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

from .forms import ItemForm, ShelfEntryForm, ThemeListForm
from .models import Item, ShelfEntry, ThemeList, ThemeListItem
from .quiz import make_question

PAGE_SIZE = 20
SEARCH_MIN_LENGTH = 3
SEARCH_LIMIT = 8
TOP_SIZE = 10


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


def top(request):
    """Top 10 books and films by average star rating (ties: more ratings first)."""
    rated = (
        Item.objects.annotate(
            avg_rating=Avg("entries__rating"),
            rating_count=Count("entries", filter=Q(entries__rating__isnull=False)),
        )
        .filter(rating_count__gt=0)
        .order_by("-avg_rating", "-rating_count", "title")
    )
    lists = [
        ("Kitap", "book", rated.filter(kind=Item.Kind.BOOK)[:TOP_SIZE]),
        ("Film", "film", rated.filter(kind=Item.Kind.FILM)[:TOP_SIZE]),
    ]
    return render(request, "shelf/top.html", {"lists": lists})


def quiz(request):
    """One random quiz question as JSON (the answer is included; it is just for fun)."""
    return JsonResponse({"question": make_question()})


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
    my_lists = []
    if request.user.is_authenticated:
        my_lists = list(request.user.theme_lists.exclude(items__item=item).order_by("title"))
    containing_lists = (
        # Filter through a subquery: filtering on the same relation before Count would only count this item.
        ThemeList.objects.filter(pk__in=ThemeListItem.objects.filter(item=item).values("theme_list"))
        .select_related("owner")
        .annotate(item_count=Count("items"))
        .order_by("-created_at", "-pk")
    )
    reviews = (
        item.entries.filter(status=ShelfEntry.Status.DONE)
        .filter(Q(rating__isnull=False) | ~Q(review=""))
        .select_related("user")
        .order_by("-finished_at", "-updated_at")
    )
    return render(
        request,
        "shelf/item_detail.html",
        {
            "item": item,
            "my_entry": my_entry,
            "reviews": reviews,
            "my_lists": my_lists,
            "containing_lists": containing_lists,
        },
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
            "theme_lists": owner.theme_lists.annotate(item_count=Count("items")).order_by("-created_at", "-pk"),
        },
    )


# --- Themed lists -------------------------------------------------------------


def list_index(request):
    """All themed lists, newest first, with their item counts."""
    theme_lists = (
        ThemeList.objects.select_related("owner").annotate(item_count=Count("items")).order_by("-created_at", "-pk")
    )
    page = Paginator(theme_lists, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "shelf/list_index.html", {"page": page})


@login_required
def list_create(request):
    form = ThemeListForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        theme_list = form.save(commit=False)
        theme_list.owner = request.user
        theme_list.save()
        messages.success(request, f"“{theme_list.title}” listesi oluşturuldu.")
        return redirect(_safe_next(request, theme_list.get_absolute_url()))
    return render(request, "shelf/list_form.html", {"form": form, "next": _safe_next(request, "")})


def list_detail(request, pk):
    theme_list = get_object_or_404(ThemeList.objects.select_related("owner"), pk=pk)
    list_items = theme_list.items.select_related("item")
    my_item_ids = set()
    if request.user.is_authenticated:
        my_item_ids = set(
            request.user.shelf.filter(item__list_entries__theme_list=theme_list).values_list("item_id", flat=True)
        )
    return render(
        request,
        "shelf/list_detail.html",
        {
            "theme_list": theme_list,
            "list_items": list_items,
            "is_owner": request.user == theme_list.owner,
            "my_item_ids": my_item_ids,
        },
    )


@login_required
def list_edit(request, pk):
    theme_list = get_object_or_404(ThemeList, pk=pk, owner=request.user)
    form = ThemeListForm(request.POST or None, instance=theme_list)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Liste güncellendi.")
        return redirect(theme_list)
    return render(request, "shelf/list_form.html", {"form": form, "theme_list": theme_list})


@login_required
def list_delete(request, pk):
    theme_list = get_object_or_404(ThemeList, pk=pk, owner=request.user)
    if request.method == "POST":
        theme_list.delete()
        messages.success(request, f"“{theme_list.title}” listesi silindi.")
        return redirect("shelf:user_shelf", username=request.user.username)
    return render(request, "shelf/list_delete.html", {"theme_list": theme_list})


@login_required
@require_POST
def list_item_add(request, pk):
    """"Listeye ekle" from an item page: puts the item into one of my lists."""
    theme_list = get_object_or_404(ThemeList, pk=pk, owner=request.user)
    item_id = request.POST.get("item_id", "")
    item = get_object_or_404(Item, pk=item_id if item_id.isdigit() else 0)
    note = " ".join(request.POST.get("note", "").split())[:200]
    _, created = ThemeListItem.objects.get_or_create(theme_list=theme_list, item=item, defaults={"note": note})
    if created:
        theme_list.save(update_fields=["updated_at"])
        messages.success(request, f"“{item.title}” “{theme_list.title}” listesine eklendi.")
    else:
        messages.info(request, f"“{item.title}” zaten “{theme_list.title}” listesinde.")
    return redirect(_safe_next(request, theme_list.get_absolute_url()))


@login_required
@require_POST
def list_item_remove(request, pk, item_id):
    list_item = get_object_or_404(
        ThemeListItem.objects.select_related("item"), theme_list__pk=pk, theme_list__owner=request.user, item_id=item_id
    )
    list_item.delete()
    messages.success(request, f"“{list_item.item.title}” listeden çıkarıldı.")
    return redirect("shelf:list_detail", pk=pk)
