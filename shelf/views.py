from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import User

from .forms import ItemForm, ShelfEntryForm
from .models import Item, ShelfEntry

PAGE_SIZE = 20
SEARCH_MIN_LENGTH = 3
SEARCH_LIMIT = 8


def _safe_next(request, fallback):
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return fallback


def _add_to_shelf(user, item, status=ShelfEntry.Status.WANT):
    """Puts the item on the user's shelf; an existing entry is left untouched."""
    entry, created = ShelfEntry.objects.get_or_create(user=user, item=item, defaults={"status": status})
    return entry, created


def feed(request):
    """Home page: the community's latest shelf activity, newest first."""
    entries = ShelfEntry.objects.select_related("user", "item").order_by("-updated_at", "-pk")
    kind = request.GET.get("kind")
    if kind in Item.Kind.values:
        entries = entries.filter(item__kind=kind)
    else:
        kind = ""
    page = Paginator(entries, PAGE_SIZE).get_page(request.GET.get("page"))

    # Items on this page that are already on the viewer's shelf (no "Ben de ekleyeyim" for those).
    my_item_ids = set()
    if request.user.is_authenticated:
        my_item_ids = set(
            request.user.shelf.filter(item__in=[entry.item_id for entry in page]).values_list("item_id", flat=True)
        )
    return render(
        request,
        "shelf/feed.html",
        {"page": page, "kind": kind, "kinds": Item.Kind.choices, "my_item_ids": my_item_ids},
    )


@login_required
def item_create(request):
    form = ItemForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    item = form.save(commit=False)
                    item.added_by = request.user
                    item.save()
                    _add_to_shelf(request.user, item, form.cleaned_data["status"])
            except IntegrityError:
                # Someone added the same item at the same moment.
                form.duplicate = Item.find_duplicate(item.kind, item.title, item.year)
            else:
                messages.success(request, f"“{item.title}” rafına eklendi.")
                return redirect(item)

        if form.duplicate:
            _, created = _add_to_shelf(request.user, form.duplicate, form.cleaned_data["status"])
            if created:
                messages.info(request, f"“{form.duplicate.title}” zaten kayıtlıydı, yeni kayıt açmadık — senin rafına ekledik.")
            else:
                messages.info(request, f"“{form.duplicate.title}” zaten kayıtlı ve zaten rafında — yeni kayıt açmadık.")
            return redirect(form.duplicate)

    return render(request, "shelf/item_form.html", {"form": form})


def item_search(request):
    """Title suggestions for the add form, so people pick an existing item instead of retyping it."""
    query = " ".join(request.GET.get("q", "").split())
    if len(query) < SEARCH_MIN_LENGTH:
        return JsonResponse({"results": []})
    items = Item.objects.filter(title__icontains=query).order_by("title", "year")[:SEARCH_LIMIT]
    return JsonResponse(
        {
            "results": [
                {
                    "title": item.title,
                    "creator": item.creator,
                    "year": item.year,
                    "kind": item.get_kind_display(),
                    "url": item.get_absolute_url(),
                    "add_url": reverse("shelf:item_add", args=[item.pk]),
                }
                for item in items
            ]
        }
    )


def item_detail(request, pk):
    item = get_object_or_404(
        Item.objects.select_related("added_by").annotate(
            shelf_count=Count("entries"),
            avg_rating=Avg("entries__rating"),
            rating_count=Count("entries", filter=Q(entries__rating__isnull=False)),
        ),
        pk=pk,
    )
    my_entry = None
    if request.user.is_authenticated:
        my_entry = item.entries.filter(user=request.user).first()
    reviews = (
        item.entries.filter(status=ShelfEntry.Status.DONE)
        .filter(Q(rating__isnull=False) | ~Q(review=""))
        .select_related("user")
        .order_by("-finished_at", "-updated_at")
    )
    return render(
        request, "shelf/item_detail.html", {"item": item, "my_entry": my_entry, "reviews": reviews}
    )


@login_required
@require_POST
def item_add(request, pk):
    """"Ben de ekleyeyim": put someone else's item on my shelf in one click."""
    item = get_object_or_404(Item, pk=pk)
    status = request.POST.get("status")
    if status not in ShelfEntry.Status.values:
        status = ShelfEntry.Status.WANT
    _, created = _add_to_shelf(request.user, item, status)
    if created:
        messages.success(request, f"“{item.title}” rafına eklendi.")
    else:
        messages.info(request, f"“{item.title}” zaten rafında.")
    return redirect(_safe_next(request, item.get_absolute_url()))


@login_required
def entry_edit(request, pk):
    entry = get_object_or_404(ShelfEntry.objects.select_related("item"), pk=pk, user=request.user)
    form = ShelfEntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Rafın güncellendi.")
        return redirect(entry.item)
    return render(request, "shelf/entry_form.html", {"form": form, "entry": entry})


@login_required
def entry_remove(request, pk):
    entry = get_object_or_404(ShelfEntry.objects.select_related("item"), pk=pk, user=request.user)
    if request.method == "POST":
        entry.delete()
        messages.success(request, f"“{entry.item.title}” rafından kaldırıldı.")
        return redirect("shelf:user_shelf", username=request.user.username)
    return render(request, "shelf/entry_remove.html", {"entry": entry})


def user_shelf(request, username):
    """Public profile: someone's shelf split into status tabs."""
    owner = get_object_or_404(User, username__iexact=username)
    entries = list(owner.shelf.select_related("item"))
    tabs = []
    for status, label in (
        (ShelfEntry.Status.CURRENT, "Şu an"),
        (ShelfEntry.Status.DONE, "Bitti"),
        (ShelfEntry.Status.WANT, "İzleyeceğim / Okuyacağım"),
    ):
        tabs.append({"status": status, "label": label, "entries": [e for e in entries if e.status == status]})

    # Default tab: the first one that has something in it.
    selected = request.GET.get("status")
    if selected not in ShelfEntry.Status.values:
        selected = next((tab["status"] for tab in tabs if tab["entries"]), ShelfEntry.Status.CURRENT)
    current_tab = next(tab for tab in tabs if tab["status"] == selected)

    return render(
        request,
        "shelf/user_shelf.html",
        {
            "owner": owner,
            "is_me": request.user == owner,
            "tabs": tabs,
            "current_tab": current_tab,
            "total": len(entries),
        },
    )
