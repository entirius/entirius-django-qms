# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from django_qms.storage_managers import CheckoutStorageManager, CsvStorageManager, StorageDataSet, StorageManager
from django_qms.utils import format_package_name

if TYPE_CHECKING:
    from django_qms.models import Channel


class ZuluStorage(models.Model):
    STORAGE_MANAGER_CHECKOUT = "checkout"
    STORAGE_MANAGER_CSV = "csv"
    STORAGE_MANAGERS = [(STORAGE_MANAGER_CHECKOUT, _("Checkout")), (STORAGE_MANAGER_CSV, _("CSV"))]
    code = models.CharField(max_length=100)
    channel: "Channel" = models.ForeignKey(
        "Channel",
        null=True,
        blank=True,
        related_name="zulu_storages",
        verbose_name="channel",
        on_delete=models.SET_NULL,
    )
    storage_manager = models.CharField(max_length=20, choices=STORAGE_MANAGERS)
    additional_data = models.JSONField(blank=True, default=dict)
    backup_data = models.JSONField(default=dict, null=True, blank=True)
    objects = models.Manager()

    class Meta:
        ordering = ["code"]
        db_table = "%s_%s" % (format_package_name(__package__), "storage")
        verbose_name = "[Zulu] storage"
        verbose_name_plural = "[Zulu] storages"
        unique_together = ("channel", "code")

    def __str__(self):
        return self.code

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
        # print("PULLING quantity is started for {}".format(self))
        self.storage_manager_inst: StorageManager = self._get_storage_manager()
        data = self.storage_manager_inst.get_data()
        # print("PULLING quantity is done for {}".format(self))
        return data

    def _get_storage_manager(self):
        if self.storage_manager == self.STORAGE_MANAGER_CHECKOUT:
            self.storage_manager_inst = CheckoutStorageManager(self.additional_data)
            self.storage_manager_inst.channel_idx = self.channel.idx
            self.storage_manager_inst.qms_type = str(self.channel.qms_type)
        elif self.storage_manager == self.STORAGE_MANAGER_CSV:
            self.storage_manager_inst = CsvStorageManager(self.additional_data)
            self.storage_manager_inst.qms_type = str(self.channel.qms_type)
        else:
            raise ValueError("Unknown Storage Manager")
        return self.storage_manager_inst
