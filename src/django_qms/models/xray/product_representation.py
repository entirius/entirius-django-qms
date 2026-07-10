# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
from idx_normalizator import validate_sku

from django_qms.utils import format_package_name


class XrayProductRepresentation(models.Model):
    sku = models.CharField(max_length=128, blank=False, null=False)
    objects = models.Manager()

    def __str__(self):
        return self.sku

    class Meta:
        ordering = ["sku"]
        db_table = "%s_%s" % (format_package_name(__package__), "productrepresentation")
        verbose_name = "[XRay] Product representation"
        verbose_name_plural = "[XRay] Products representations"
        constraints = [UniqueConstraint(Lower("sku"), name="unique_qms_xray_product_sku")]

    def save(self, *args, **kwargs):
        validate_sku(self.sku)
        super().save(*args, **kwargs)
