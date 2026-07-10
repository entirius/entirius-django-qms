# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError
from django.db import models
from idx_normalizator import normalize_idx, validate_idx

from django_qms.enums import QMSType


class Channel(models.Model):
    idx = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    stock_weight = models.IntegerField(default=0)
    qms_type = models.CharField(
        max_length=8, choices=QMSType.choices, db_index=True, blank=False, null=False, default=QMSType.ZULU
    )
    objects = models.Manager()

    class Meta:
        ordering = ["idx"]
        verbose_name_plural = "channels"
        unique_together = (["idx"], ["name"])

    def __str__(self):
        return self.idx

    def validate_qms_type(self):
        if not QMSType.is_implemented(self.qms_type):
            raise ValidationError(f"QMS type {self.qms_type} is not yet implemented.")

    def save(self, *args, **kwargs):
        if self.idx is None:
            self.idx = normalize_idx(str(self.name))
        validate_idx(self.idx)
        super().save(*args, **kwargs)

    def clean(self):
        self.validate_qms_type()
