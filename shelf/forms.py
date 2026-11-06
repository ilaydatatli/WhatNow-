from django import forms
from django.utils import timezone

from .models import Item, ShelfEntry, status_label

RATING_CHOICES = [("", "Puan yok")] + [(n, "★" * n) for n in range(1, 6)]


class ItemForm(forms.ModelForm):
    """New film/book plus the status it gets on the author's own shelf."""

    status = forms.ChoiceField(label="Rafındaki durumu", choices=ShelfEntry.Status.choices)

    class Meta:
        model = Item
        fields = ["kind", "title", "creator", "year", "genre"]
        widgets = {
            "kind": forms.RadioSelect,
            "title": forms.TextInput(attrs={"placeholder": "Dune"}),
            "creator": forms.TextInput(attrs={"placeholder": "Frank Herbert"}),
            "year": forms.NumberInput(attrs={"placeholder": "1965", "inputmode": "numeric"}),
            "genre": forms.TextInput(attrs={"placeholder": "bilim kurgu"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].choices = Item.Kind.choices  # drop the empty "---------" choice
        self.duplicate = None

    def clean_title(self):
        return " ".join(self.cleaned_data["title"].split())

    def clean_creator(self):
        return " ".join(self.cleaned_data["creator"].split())

    def clean(self):
        cleaned_data = super().clean()
        kind, title, year = (cleaned_data.get(k) for k in ("kind", "title", "year"))
        if kind and title and year:
            # The view redirects to the existing item instead of showing this error.
            self.duplicate = Item.find_duplicate(kind, title, year)
            if self.duplicate:
                raise forms.ValidationError("Bu öğe zaten var.")
        return cleaned_data


class ShelfEntryForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        label="Puan",
        choices=RATING_CHOICES,
        coerce=int,
        empty_value=None,
        required=False,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = ShelfEntry
        fields = ["status", "finished_at", "rating", "review"]
        widgets = {
            "status": forms.RadioSelect,
            "finished_at": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "review": forms.Textarea(attrs={"rows": 3, "placeholder": "Kısaca ne düşündün?"}),
        }
        help_texts = {
            "finished_at": "Boş bırakırsan bugün sayılır.",
            "review": "En fazla 280 karakter. Puan ve yorum yalnızca “Bitti” durumunda kaydedilir.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        kind = self.instance.item.kind
        self.fields["status"].choices = [
            (value, status_label(value, kind)) for value, _ in ShelfEntry.Status.choices
        ]

    def clean_finished_at(self):
        finished_at = self.cleaned_data.get("finished_at")
        if finished_at and finished_at > timezone.localdate():
            raise forms.ValidationError("Bitirme tarihi gelecekte olamaz.")
        return finished_at
