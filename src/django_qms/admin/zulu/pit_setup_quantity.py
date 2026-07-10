# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_qms.models import ZuluPitSetupQuantity


@admin.register(ZuluPitSetupQuantity)
class ZuluPitSetupQuantityAdmin(admin.ModelAdmin):
    list_display = ("id", "pit", "channel", "storage", "product", "quantity_available")
    list_filter = ("pit", "channel")
    search_fields = ("product__sku",)
