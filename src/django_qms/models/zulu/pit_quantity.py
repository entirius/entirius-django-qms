# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from django_qms.utils import format_package_name


class ZuluPitQuantity(models.Model):
    pit = models.ForeignKey("ZuluPointInTime", on_delete=models.CASCADE)
    product = models.ForeignKey("ZuluProductRepresentation", on_delete=models.CASCADE)
    quantity_available = models.IntegerField(default=0)
    quantity_locked = models.IntegerField(default=0)
    objects = models.Manager()

    class Meta:
        db_table = "%s_%s" % (format_package_name(__package__), "pitquantity")
        verbose_name = "[Zulu] PIT quantity"
        verbose_name_plural = "[Zulu] PIT quantities"
        unique_together = ("pit", "product")
