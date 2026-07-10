# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from django_qms.utils import format_package_name


class ZuluPitSetupQuantity(models.Model):
    pit = models.ForeignKey("ZuluPointInTime", on_delete=models.CASCADE)
    channel = models.ForeignKey("Channel", null=True, blank=True, on_delete=models.SET_NULL)
    product = models.ForeignKey("ZuluProductRepresentation", on_delete=models.CASCADE)
    storage = models.ForeignKey("ZuluStorage", on_delete=models.CASCADE)
    quantity_available = models.IntegerField(default=0)
    objects = models.Manager()

    class Meta:
        db_table = "%s_%s" % (format_package_name(__package__), "pitsetupquantity")
        verbose_name = "[Zulu] PIT setup quantity"
        verbose_name_plural = "[Zulu] PIT setup quantities"
        unique_together = ("pit", "storage", "product")
