# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_qms.models import XrayQuantityByStorage


@admin.register(XrayQuantityByStorage)
class XrayQuantityByStorageAdmin(admin.ModelAdmin):
    list_display = ("storage", "product", "pit", "quantity")
    list_filter = ("storage__channel", "storage", "storage__data_direction", "pit", "pit__proces_status")
    search_fields = ("product__sku",)
