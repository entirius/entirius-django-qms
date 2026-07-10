# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from django_qms.utils import format_package_name

if TYPE_CHECKING:
    from django_qms.models import Channel


class XrayPointInTimeManager(models.Manager):
    def already_running(self, channel: "Channel"):
        return self.filter(proces_status=XrayPointInTime.ProcessStatus.PROCESSING, channel=channel)

    def waiting(self, channel: "Channel"):
        return self.filter(proces_status=XrayPointInTime.ProcessStatus.WAITING, channel=channel)


class XrayPointInTime(models.Model):
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE, related_name="xray_pits")
    pit = models.DateTimeField()

    class ProcessStatus(models.TextChoices):
        WAITING = "waiting", _("Waiting")
        PROCESSING = "processing", _("Processing")
        DONE = "done", _("Done")
        CANCELED = "canceled", _("Canceled")
        ERROR = "error", _("Error")

    proces_status = models.CharField(max_length=12, choices=ProcessStatus.choices, default=ProcessStatus.WAITING)
    objects = XrayPointInTimeManager()

    def set_as_error(self):
        self.proces_status = XrayPointInTime.ProcessStatus.ERROR
        self.save()

    def set_as_processing(self):
        if self.proces_status == XrayPointInTime.ProcessStatus.ERROR:
            raise Exception("Can not change ZuluPointInTime status to PROCESSING if it is already set to ERROR")
        self.proces_status = XrayPointInTime.ProcessStatus.PROCESSING
        self.save()

    def set_as_done(self):
        if self.proces_status == XrayPointInTime.ProcessStatus.ERROR:
            raise Exception("Can not change ZuluPointInTime status to DONE if it is already set to ERROR")
        self.proces_status = XrayPointInTime.ProcessStatus.DONE
        self.save()

    def set_as_canceled(self):
        if self.proces_status == XrayPointInTime.ProcessStatus.ERROR:
            raise Exception("Can not change ZuluPointInTime status to CANCELED if it is already set to ERROR")
        self.proces_status = XrayPointInTime.ProcessStatus.CANCELED
        self.save()

    def is_processing(self) -> bool:
        return self.proces_status == XrayPointInTime.ProcessStatus.PROCESSING

    def is_done(self) -> bool:
        return self.proces_status == XrayPointInTime.ProcessStatus.DONE

    class Meta:
        get_latest_by = "pit"
        ordering = ["-pit"]
        db_table = "%s_%s" % (format_package_name(__package__), "pit")
        verbose_name = "[XRay] Point In Time"
        verbose_name_plural = "[XRay] Points In Time"

    def __str__(self):
        return f"{str(self.channel)} | {str(self.pit)}"
