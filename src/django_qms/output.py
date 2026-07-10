# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_qms.models import Channel
from django_qms.service import xray_get_quantities, xray_get_quantity, zulu_get_quantities, zulu_get_quantity
from django_qms.settings import QMSType


def get_quantities(channel_idx: str):
    channel = Channel.objects.get(idx=channel_idx)

    match channel.qms_type:
        case QMSType.XRAY:
            return xray_get_quantities(channel)
        case QMSType.ZULU:
            return zulu_get_quantities(channel)
        case _:
            raise Exception(f"Can not get quantities from not implemented QMS type: {channel.qms_type}")


def get_product_quantity(channel_idx: str, sku: str):
    channel = Channel.objects.get(idx=channel_idx)

    match channel.qms_type:
        case QMSType.XRAY:
            return xray_get_quantity(channel, sku)
        case QMSType.ZULU:
            return zulu_get_quantity(channel, sku)
        case _:
            raise Exception(f"Can not get {sku} quantity from not implemented QMS type: {channel.qms_type}")
