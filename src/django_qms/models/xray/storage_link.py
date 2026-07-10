# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_qms.utils import format_package_name

if TYPE_CHECKING:
    from django_qms.models import XrayStorage


class XrayStorageLink(models.Model):
    class DataDirection(models.TextChoices):
        STORAGE_INPUT = "input", _("Input")
        STORAGE_OUTPUT = "output", _("Output")

    storage_input: "XrayStorage" = models.ForeignKey(
        "XrayStorage", on_delete=models.CASCADE, related_name="xray_storage_links_input"
    )
    storage_output: "XrayStorage" = models.ForeignKey(
        "XrayStorage", on_delete=models.CASCADE, related_name="xray_storage_links_output"
    )
    objects = models.Manager()

    class Meta:
        db_table = "%s_%s" % (format_package_name(__package__), "storagelink")
        verbose_name = "[XRay] Storage Link"
        verbose_name_plural = "[XRay] Storage Links"

    def validate(self):
        if self.storage_input == self.storage_output:
            raise ValidationError("Storage input and storage output cannot be the same")
        if self.storage_input.data_direction != XrayStorageLink.DataDirection.STORAGE_INPUT:
            raise ValidationError("Storage input must be of input type")
        if self.storage_output.data_direction != XrayStorageLink.DataDirection.STORAGE_OUTPUT:
            raise ValidationError("Storage output must be of output type")
        if self.storage_input.channel != self.storage_output.channel:
            raise ValidationError("Storage input and storage output must be of the same channel")

    def clean(self):
        self.validate()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.storage_input} > {self.storage_output}"
