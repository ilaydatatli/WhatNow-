from django.contrib import admin

from .models import Item, ShelfEntry, ThemeList, ThemeListItem


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "creator", "year", "genre", "added_by", "created_at")
    list_filter = ("kind",)
    search_fields = ("title", "creator")


@admin.register(ShelfEntry)
class ShelfEntryAdmin(admin.ModelAdmin):
    list_display = ("item", "user", "status", "rating", "finished_at", "updated_at")
    list_filter = ("status", "item__kind")
    search_fields = ("item__title", "user__username")
    list_select_related = ("item", "user")


class ThemeListItemInline(admin.TabularInline):
    model = ThemeListItem
    extra = 0
    autocomplete_fields = ("item",)


@admin.register(ThemeList)
class ThemeListAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "created_at", "updated_at")
    search_fields = ("title", "owner__username")
    list_select_related = ("owner",)
    inlines = [ThemeListItemInline]
