# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_qms.models import ZuluPointInTime


@admin.register(ZuluPointInTime)
class ZuluPointInTimeAdmin(admin.ModelAdmin):
    list_display = ("id", "pit", "proces_status")
    actions = ["push_snapshot_data"]

    def push_snapshot_data(self, request, rset):
        for item in rset:
            item.send_results()
