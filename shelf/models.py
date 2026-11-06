from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone

MIN_YEAR = 1000


def max_year():
    return timezone.localdate().year + 1


class Item(models.Model):
    """A film or a book in the shared catalog (entered by hand)."""

    class Kind(models.TextChoices):
        FILM = "film", "Film"
        BOOK = "book", "Kitap"

    kind = models.CharField("tür", max_length=10, choices=Kind.choices)
    title = models.CharField("başlık", max_length=200)
    creator = models.CharField("yazar / yönetmen", max_length=100)
    year = models.PositiveSmallIntegerField(
        "yıl", validators=[MinValueValidator(MIN_YEAR), MaxValueValidator(max_year)]
    )
    genre = models.CharField("tür (ör. bilim kurgu)", max_length=50, blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_items",
        verbose_name="ekleyen",
    )
    created_at = models.DateTimeField("eklenme", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "film / kitap"
        verbose_name_plural = "filmler / kitaplar"
        constraints = [
            # Prevents the same film/book from being entered twice (case-insensitive title).
            models.UniqueConstraint(Lower("title"), "year", "kind", name="unique_item_title_year_kind"),
        ]

    def __str__(self):
        return f"{self.title} ({self.year})"

    def get_absolute_url(self):
        return reverse("shelf:item_detail", args=[self.pk])

    @classmethod
    def find_duplicate(cls, kind, title, year):
        return cls.objects.filter(kind=kind, title__iexact=title.strip(), year=year).first()


class ShelfEntry(models.Model):
    """One item on one user's shelf, with its status and (when finished) rating/review."""

    class Status(models.TextChoices):
        WANT = "want", "İzleyeceğim / Okuyacağım"
        CURRENT = "current", "Şu an"
        DONE = "done", "Bitti"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shelf", verbose_name="kullanıcı"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="entries", verbose_name="öğe")
    status = models.CharField("durum", max_length=10, choices=Status.choices, default=Status.WANT)
    rating = models.PositiveSmallIntegerField(
        "puan", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review = models.CharField("yorum", max_length=280, blank=True)
    finished_at = models.DateField("bitirme tarihi", null=True, blank=True)
    created_at = models.DateTimeField("eklenme", auto_now_add=True)
    updated_at = models.DateTimeField("güncellenme", auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "raf kaydı"
        verbose_name_plural = "raf kayıtları"
        constraints = [
            models.UniqueConstraint(fields=["user", "item"], name="unique_shelf_entry"),
            models.CheckConstraint(
                condition=models.Q(rating__isnull=True) | models.Q(rating__gte=1, rating__lte=5),
                name="shelf_entry_rating_1_5",
            ),
        ]

    def __str__(self):
        return f"{self.user} · {self.item}"

    def save(self, *args, **kwargs):
        # Rating, review and finish date only make sense for finished items.
        if self.status == self.Status.DONE:
            self.finished_at = self.finished_at or timezone.localdate()
        else:
            self.rating = None
            self.review = ""
            self.finished_at = None
        super().save(*args, **kwargs)

    @property
    def status_label(self):
        return status_label(self.status, self.item.kind)


def status_label(status, kind):
    """Status label worded for the item's kind, e.g. "Okuyacağım" for a book."""
    is_book = kind == Item.Kind.BOOK
    if status == ShelfEntry.Status.WANT:
        return "Okuyacağım" if is_book else "İzleyeceğim"
    return ShelfEntry.Status(status).label
