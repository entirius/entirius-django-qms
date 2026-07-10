# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_qms.models import SourceType, Warehouse, WarehouseStock


class WarehouseStockInline(admin.TabularInline):
    model = WarehouseStock
    extra = 0
    fields = ("sku", "quantity", "created_at", "modified_at")
    readonly_fields = ("created_at", "modified_at")

    def has_change_permission(self, request, obj=None):
        if obj and obj.source_type == SourceType.INTEGRATION:
            return False
        return super().has_change_permission(request, obj)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "source_type", "is_active", "last_synced_at")
    list_filter = ("source_type", "is_active")
    search_fields = ("code", "name")
    filter_horizontal = ("channels",)
    readonly_fields = ("last_synced_at", "created_at", "modified_at")
    inlines = [WarehouseStockInline]
    fieldsets = (
        (None, {"fields": ("code", "name", "description", "source_type", "is_active")}),
        ("Channels", {"fields": ("channels",)}),
        ("Timestamps", {"fields": ("last_synced_at", "created_at", "modified_at"), "classes": ("collapse",)}),
    )
