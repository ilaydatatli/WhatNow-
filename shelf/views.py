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


def home(request):
    # Temporary home page (Phase 5): newest items. Becomes the activity feed in Phase 6.
    items = (
        Item.objects.annotate(shelf_count=Count("entries"))
        .select_related("added_by")
        .order_by("-created_at", "-pk")
    )
    page = Paginator(items, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "shelf/home.html", {"page": page})


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
    return render(request, "shelf/item_detail.html", {"item": item, "my_entry": my_entry})


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
        return redirect("accounts:profile")
    return render(request, "shelf/entry_remove.html", {"entry": entry})
