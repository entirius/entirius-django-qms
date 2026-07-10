# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from django_qms.storage_managers import StorageDataSet, StorageItem
from django_qms.utils import format_package_name

if TYPE_CHECKING:
    from django_qms.models import PitSetupQuantity


class ZuluPointInTime(models.Model):
    pit = models.DateTimeField()

    class ProcessStatus(models.TextChoices):
        WAITING = "waiting", _("Waiting")
        PROCESSING = "processing", _("Processing")
        DONE = "done", _("Done")
        CANCELED = "canceled", _("Canceled")
        ERROR = "error", _("Error")

    proces_status = models.CharField(max_length=12, choices=ProcessStatus.choices, default=ProcessStatus.WAITING)
    objects = models.Manager()

    def set_as_error(self):
        self.proces_status = ZuluPointInTime.ProcessStatus.ERROR
        self.save()

    def set_as_processing(self):
        if self.proces_status == ZuluPointInTime.ProcessStatus.ERROR:
            raise Exception("Can not change ZuluPointInTime status to PROCESSING if it is already set to ERROR")
        self.proces_status = ZuluPointInTime.ProcessStatus.PROCESSING
        self.save()

    def set_as_done(self):
        if self.proces_status == ZuluPointInTime.ProcessStatus.ERROR:
            raise Exception("Can not change ZuluPointInTime status to DONE if it is already set to ERROR")
        self.proces_status = ZuluPointInTime.ProcessStatus.DONE
        self.save()

    def set_as_canceled(self):
        if self.proces_status == ZuluPointInTime.ProcessStatus.ERROR:
            raise Exception("Can not change ZuluPointInTime status to CANCELED if it is already set to ERROR")
        self.proces_status = ZuluPointInTime.ProcessStatus.CANCELED
        self.save()

    class Meta:
        get_latest_by = "pit"
        ordering = ["-pit"]
        db_table = "%s_%s" % (format_package_name(__package__), "pit")
        verbose_name = "[Zulu] Point In Time"
        verbose_name_plural = "[Zulu] Points In Time"

    def __str__(self):
        return str(self.pit)

    def send_results(self):
        from django_qms.models import Storage

        for storage in Storage.objects.all():
            items_to_send = []
            setup_item: PitSetupQuantity
            for setup_item in self.zulupitsetupquantity_set.filter(storage=storage):
                item = StorageItem(setup_item.product.sku, setup_item.quantity_available)
                items_to_send.append(item)
            if len(items_to_send) > 0:
                result = StorageDataSet(items_to_send)
                storage.push_quantity(result)
