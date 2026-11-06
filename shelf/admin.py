from django.contrib import admin

from .models import Item, ShelfEntry


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
