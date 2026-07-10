# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from django_qms.storage_managers import (
    CheckoutStorageManager,
    CsvStorageManager,
    StorageDataSet,
    StorageManager,
)
from django_qms.utils import format_package_name

if TYPE_CHECKING:
    from django_qms.models import Channel


class XrayStorage(models.Model):
    class StorageManagerEnum(models.TextChoices):
        CHECKOUT = "checkout", _("Checkout")
        CSV = "csv", _("CSV")

    class DataDirection(models.TextChoices):
        STORAGE_INPUT = "input", _("Input")
        STORAGE_OUTPUT = "output", _("Output")

    code = models.CharField(max_length=100)
    channel: "Channel" = models.ForeignKey(
        "Channel",
        null=True,
        blank=True,
        related_name="xray_storages",
        verbose_name="channel",
        on_delete=models.SET_NULL,
    )
    storage_manager = models.CharField(max_length=20, choices=StorageManagerEnum.choices)
    data_direction = models.CharField(max_length=20, choices=DataDirection.choices)
    additional_data = models.JSONField(blank=True, default=dict)
    objects = models.Manager()

    class Meta:
        ordering = ["code"]
        db_table = "%s_%s" % (format_package_name(__package__), "storage")
        verbose_name = "[XRay] Storage"
        verbose_name_plural = "[XRay] Storages"
        unique_together = ("channel", "code")

    def __str__(self):
        return f"[{self.channel.idx}] <{self.data_direction}> {self.code}"

    def push_quantity(self, data: StorageDataSet):
        """
        Function needs to push data to proper StorageManager
        """
        self.storage_manager_inst: StorageManager = self._get_storage_manager()
        self.storage_manager_inst.push_data(data)

    def pull_quantity(self):
        """
        Function pulls data from storage
        :return:
        """
        self.storage_manager_inst: StorageManager = self._get_storage_manager()
        return self.storage_manager_inst.get_data()

    def _get_storage_manager(self):
        if self.storage_manager == self.StorageManagerEnum.CHECKOUT:
            self.storage_manager_inst = CheckoutStorageManager(self.additional_data)
            self.storage_manager_inst.channel_idx = self.channel.idx
            self.storage_manager_inst.qms_type = str(self.channel.qms_type)
        elif self.storage_manager == self.StorageManagerEnum.CSV:
            self.storage_manager_inst = CsvStorageManager(self.additional_data)
            self.storage_manager_inst.qms_type = str(self.channel.qms_type)
        else:
            raise ValueError("Unknown Storage Manager")
        return self.storage_manager_inst
