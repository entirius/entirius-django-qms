# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from django_qms.utils import format_package_name


class XrayQuantityByStorage(models.Model):
    storage = models.ForeignKey("XrayStorage", on_delete=models.CASCADE, related_name="xray_quantities_by_storage")
    pit = models.ForeignKey("XrayPointInTime", on_delete=models.CASCADE)
    product = models.ForeignKey("XrayProductRepresentation", on_delete=models.CASCADE)
    quantity_int = models.IntegerField(default=0)
    objects = models.Manager()

    class Meta:
        db_table = "%s_%s" % (format_package_name(__package__), "quantitybystorage")
        verbose_name = "[XRay] Quantity by Storage"
        verbose_name_plural = "[XRay] Quantities by Storage"
        unique_together = ("product", "pit", "storage")

    @property
    def quantity(self):
        return self.quantity_int
