from django.contrib import admin
from django.db.models import Count

from .models import Option, Poll, Vote


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ("question", "author", "vote_count", "created_at")
    list_select_related = ("author",)
    search_fields = ("question", "author__username")
    inlines = [OptionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(vote_count=Count("votes"))

    @admin.display(description="oy sayısı", ordering="vote_count")
    def vote_count(self, poll):
        return poll.vote_count


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ("text", "poll", "order")
    list_select_related = ("poll",)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("poll", "option", "user", "created_at")
    list_select_related = ("poll", "option", "user")
    list_filter = ("created_at",)
