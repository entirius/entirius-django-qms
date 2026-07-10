# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from idx_normalizator import normalize_sku, validate_sku

from django_qms.utils import format_package_name

if TYPE_CHECKING:
    from django_qms.models import ZuluPitQuantity


class ZuluProductRepresentation(models.Model):
    PR_SETUP_EQUAL = "equal"
    PR_SETUP_SPLIT = "split"
    PR_SETUP_ALGOS = [(PR_SETUP_EQUAL, _("Equal")), (PR_SETUP_SPLIT, _("Split"))]
    sku = models.CharField(max_length=128, blank=False, null=False)
    product_algo = models.CharField(max_length=10, choices=PR_SETUP_ALGOS, default=PR_SETUP_SPLIT)
    objects = models.Manager()

    def __str__(self):
        return self.sku

    class Meta:
        ordering = ["sku"]
        db_table = "%s_%s" % (format_package_name(__package__), "productrepresentation")
        verbose_name = "[Zulu] product representation"
        verbose_name_plural = "[Zulu] products representations"
        constraints = [UniqueConstraint(Lower("sku"), name="unique_qms_zulu_product_sku")]

    def save(self, *args, **kwargs):
        validate_sku(self.sku)
        super().save(*args, **kwargs)

    def split_by_algo(self, number: int):
        from django_qms.models import Channel

        channels = Channel.objects.all().exclude(stock_weight=0).order_by("-stock_weight")
        split_prods = {}
        if len(channels) == 1:
            split_prods[channels[0].idx] = number
            return split_prods
        if len(channels) > 0:
            if self.product_algo == self.PR_SETUP_EQUAL:
                divider = len(channels)
                main_num = int(number / divider)
                rest = number - (main_num * divider)
                for channel in channels:
                    split_prods[channel.idx] = main_num
                split_prods[channels[0].idx] += rest
            elif self.product_algo == self.PR_SETUP_SPLIT:
                weights = sum([channel.stock_weight for channel in channels])
                weights = 1 if weights == 0 else weights
                main_num = int(number / weights)
                rest = number - (main_num * weights)
                for channel in channels:
                    split_prods[channel.idx] = main_num * channel.stock_weight
                split_prods[channels[0].idx] += rest
            else:
                raise ValueError("Invalid algorithm")
        return split_prods

    def get_stocks(self, date_before=None):
        """
        Deprecated
        """

        if date_before is None:
            date_before = datetime.datetime.now()

        from django_qms.models import ZuluPointInTime

        stock = {}
        pit = ZuluPointInTime.objects.filter(pit__lte=date_before).latest()
        for channel in pit.zulupitquantitybychannel_set.all():
            stock[channel.channel.idx] = channel.quantity_available
        total_pit: ZuluPitQuantity = pit.zulupitquantity_set.get(product=self)
        stock["total"] = total_pit.quantity_available
        return stock

    @staticmethod
    def normalize_sku(sku):
        """Deprecated"""
        return normalize_sku(sku)
