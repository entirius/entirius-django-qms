# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models import Q

from django_qms.models import (
    Channel,
    XrayPointInTime,
    XrayQuantityByStorage,
    XrayStorage,
    ZuluPitSetupQuantity,
    ZuluPointInTime,
)


def xray_get_quantities(channel: Channel):
    return (
        XrayQuantityByStorage.objects.filter(
            storage__channel__idx=channel.idx,
            storage__data_direction=XrayStorage.DataDirection.STORAGE_OUTPUT,
            pit__proces_status=XrayPointInTime.ProcessStatus.DONE,
        )
        .exclude(
            ~Q(storage__additional_data__supplier_code=None) & Q(storage__additional_data__has_key="supplier_code")
        )
        .order_by("product__id", "-pit__pit")
        .distinct("product")
        .values_list("product__sku", "quantity_int")
    )


def zulu_get_quantities(channel: Channel):
    return (
        ZuluPitSetupQuantity.objects.filter(
            channel__idx=channel.idx, pit__proces_status=ZuluPointInTime.ProcessStatus.DONE
        )
        .order_by("product__id", "-pit__pit")
        .distinct("product")
        .values_list("product__sku", "quantity_available")
    )


def xray_get_quantity(channel: Channel, sku: str):
    zulu_qty = (
        XrayQuantityByStorage.objects.filter(
            product__sku=sku,
            storage__channel__idx=channel.idx,
            storage__data_direction=XrayStorage.DataDirection.STORAGE_OUTPUT,
            pit__proces_status=XrayPointInTime.ProcessStatus.DONE,
        )
        .exclude(
            ~Q(storage__additional_data__supplier_code=None) & Q(storage__additional_data__has_key="supplier_code")
        )
        .order_by("product__id", "-pit__pit")
        .first()
    )

    return zulu_qty.quantity_int if zulu_qty else None


def zulu_get_quantity(channel: Channel, sku: str):
    zulu_qty = (
        ZuluPitSetupQuantity.objects.filter(
            product__sku=sku, channel__idx=channel.idx, pit__proces_status=ZuluPointInTime.ProcessStatus.DONE
        )
        .order_by("product__id", "-pit__pit")
        .first()
    )

    return zulu_qty.quantity_available if zulu_qty else None
