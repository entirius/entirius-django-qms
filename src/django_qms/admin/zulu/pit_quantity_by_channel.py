# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_qms.models import ZuluPitQuantityByChannel


@admin.register(ZuluPitQuantityByChannel)
class ZuluPitQuantityByChannelAdmin(admin.ModelAdmin):
    list_display = ("id", "pit", "channel", "product", "quantity_available", "quantity_locked")
    list_filter = ("pit",)
    search_fields = ("product__sku",)
