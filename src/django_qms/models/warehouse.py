# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models
from django_utils.models.base_model import BaseModel


class SourceType(models.TextChoices):
    MANUAL = "manual", "Manual (CMS)"
    INTEGRATION = "integration", "Integration (CSV/API)"


class Warehouse(BaseModel):
    """Physical warehouse or virtual stock source.

    Manual warehouses are edited via CMS. Integration warehouses are fed by CSV/API
    and appear read-only in CMS.
    """

    code = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    source_type = models.CharField(max_length=16, choices=SourceType.choices, default=SourceType.MANUAL)
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    channels = models.ManyToManyField("django_qms.Channel", blank=True, related_name="warehouses")

    class Meta:
        db_table = "django_qms_warehouse"
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
