# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from celery import shared_task
from celery_once import QueueOnce

from django_qms.bi import QM_PushDataEvent
from django_qms.enums import QMSType
from django_qms.models import Channel, ZuluPitSetupQuantity, ZuluPointInTime
from django_qms.storage_managers import StorageDataSet, StorageItem

DOMAIN_NAME = QMSType.ZULU

logger = logging.getLogger(__name__)


@shared_task(base=QueueOnce, queue="quantities")
def zulu_push_data(channel_id: int, pit_id: int) -> dict:
    """Push data from PitSetupQuantity to Channel"""
    pit = ZuluPointInTime.objects.get(pk=pit_id)
    if pit.proces_status != ZuluPointInTime.ProcessStatus.PROCESSING:
        raise Exception(f"Halting work on not processing pit={pit.pit}")
    channel = Channel.objects.get(pk=channel_id)
    bev = QM_PushDataEvent(pit=pit.pit, channel_idx=channel.idx, is_ongoing_event=True)
    raport_storages = {}
    try:
        logger.info(f"QMS {DOMAIN_NAME} Push Quantity channel={channel.idx} is starting")
        # Kloczi: niech stany bede ustawiane per produkt a nie per storage
        for storage in channel.zulu_storages.all().order_by("id"):
            # dataset for storage
            values_list = ZuluPitSetupQuantity.objects.filter(storage=storage, pit=pit).values_list(
                "product__sku", "quantity_available"
            )
            items = []
            for values in values_list:
                items.append(StorageItem(sku=values[0], quantity=values[1]))
            key = f"{channel.idx}.{storage.code}"
            raport_storages[key] = len(items)
            dataset = StorageDataSet(items=items)
            logger.info(f"QMS {DOMAIN_NAME} Push Quantity channel={channel.idx} is pushing to storage={storage.code}")
            storage.push_quantity(dataset)
        logger.info(f"QMS {DOMAIN_NAME} Push Quantity channel={channel.idx} is done")
        bev.set_detail("products_per_storage", raport_storages)
        bev.finish_with_success(finish_tag="QMS Push Quantity is done")
        return {"status": "ok"}
    except BaseException as e:
        bev.set_detail("products_per_storage", raport_storages)
        bev.finish_with_exception(e)
        pit.set_as_error()
        raise e
