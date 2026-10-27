from django.conf import settings
from django.db import models
from django.db.models import Q

MIN_OPTIONS = 2
MAX_OPTIONS = 5


class Poll(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="polls", verbose_name="yazar"
    )
    question = models.CharField("soru", max_length=200)
    created_at = models.DateTimeField("olusturulma_tarihi", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "anket"
        verbose_name_plural = "anketler"

    def __str__(self):
        return self.question


class Option(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField("seçenek", max_length=100)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "seçenek"
        verbose_name_plural = "seçenekler"

    def __str__(self):
        return self.text


class Vote(models.Model):
    # One vote per poll: registered users are tracked by `user`, guests by the
    # `voter_token` cookie. Prototype-level only: clearing cookies lets a guest vote again.
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    voter_token = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "oy"
        verbose_name_plural = "oylar"
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "user"],
                condition=Q(user__isnull=False),
                name="unique_vote_per_user",
            ),
            models.UniqueConstraint(fields=["poll", "voter_token"], name="unique_vote_per_token"),
        ]

    def __str__(self):
        return f"{self.poll_id} → {self.option}"
