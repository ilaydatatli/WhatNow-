from django import forms
from django.db import transaction

from .models import MAX_OPTIONS, MIN_OPTIONS, Option, Poll

OPTION_MAX_LENGTH = Option._meta.get_field("text").max_length


class PollForm(forms.Form):
    """Question plus a variable list of options submitted as repeated `options` fields."""

    question = forms.CharField(
        label="Sorun ne?",
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Bugün makarna mı yapsam pilav mı?"}),
    )

    def __init__(self, data=None):
        super().__init__(data)
        # Raw values are kept so the template can re-render what the user typed.
        self.option_values = data.getlist("options") if data is not None else [""] * MIN_OPTIONS

    def clean(self):
        cleaned_data = super().clean()
        options = [value.strip() for value in self.option_values]

        if not MIN_OPTIONS <= len(options) <= MAX_OPTIONS:
            raise forms.ValidationError(
                f"Anket en az {MIN_OPTIONS}, en fazla {MAX_OPTIONS} seçenek içermeli."
            )
        if any(not option for option in options):
            raise forms.ValidationError("Seçenekler boş bırakılamaz.")
        if any(len(option) > OPTION_MAX_LENGTH for option in options):
            raise forms.ValidationError(
                f"Her seçenek en fazla {OPTION_MAX_LENGTH} karakter olabilir."
            )
        if len({option.casefold() for option in options}) != len(options):
            raise forms.ValidationError("Aynı seçeneği iki kez ekleyemezsin.")

        cleaned_data["options"] = options
        return cleaned_data

    @transaction.atomic
    def save(self, author):
        poll = Poll.objects.create(author=author, question=self.cleaned_data["question"])
        Option.objects.bulk_create(
            Option(poll=poll, text=text, order=index)
            for index, text in enumerate(self.cleaned_data["options"])
        )
        return poll
