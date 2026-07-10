# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from collections import defaultdict

from celery import shared_task
from idx_normalizator import normalize_sku

from django_qms.bi import QM_GatherQuantityDataEvent
from django_qms.enums import QMSType
from django_qms.models import Channel, ZuluPitQuantityByChannel, ZuluPointInTime, ZuluProductRepresentation
from django_qms.settings import QMS_PIT_QUANTITY_BY_CHANNEL_CHUNK_SIZE

DOMAIN_NAME = QMSType.ZULU

logger = logging.getLogger(__name__)


@shared_task(queue="quantities", hard_time_limit=1200, time_limit=1200)
def zulu_create_pit_quantity_by_channel(channel_id: int, pit_id: int) -> dict:
    """Pull quantities data for given Channel then save it to PitQuantityByChannel"""

    def save_chunk():
        if not records_to_create:
            return
        logger.info(f"QMS {DOMAIN_NAME}: Gather Quantity channel={channel.idx} progress {cnt} / {dataset_total}")
        ZuluPitQuantityByChannel.objects.bulk_create(records_to_create, batch_size=50000)
        report["pit_quantities_created"] += len(records_to_create)

    pit = ZuluPointInTime.objects.get(pk=pit_id)
    if pit.proces_status != ZuluPointInTime.ProcessStatus.PROCESSING:
        raise Exception(f"Halting work on not processing pit={pit.pit}")
    channel = Channel.objects.get(pk=channel_id)
    bev = QM_GatherQuantityDataEvent(channel_idx=channel.idx, pit=pit.pit, is_ongoing_event=True)
    report = {"pit_quantities_created": 0}
    chunk_size = QMS_PIT_QUANTITY_BY_CHANNEL_CHUNK_SIZE
    products_sku_to_id = {}
    try:
        logger.info(f"QMS {DOMAIN_NAME}: is pulling data from channel: {channel.idx}")
        dataset = defaultdict(lambda: 0)
        for storage in channel.zulu_storages.all():
            data = storage.pull_quantity()
            for item in data.items:
                dataset[item.sku] += int(float(item.quantity))
        dataset_total = len(dataset)
        report["dataset_total"] = dataset_total
        logger.info(f"QMS {DOMAIN_NAME} preloading products to cache")
        for product_id, product_sku in ZuluProductRepresentation.objects.all().values_list("id", "sku"):
            products_sku_to_id[product_sku] = product_id
        report["product_representations_existed"] = len(products_sku_to_id)
        logger.info(f"QMS {DOMAIN_NAME} loaded {len(products_sku_to_id)} ProductRepresentations to cache")
        logger.info(f"QMS {DOMAIN_NAME} is collecting missing ProductRepresentations for channel={channel.idx}")
        records_to_create = []
        cnt = 0
        for sku in dataset.keys():
            cnt += 1
            normalized_sku = normalize_sku(sku)
            if normalized_sku in products_sku_to_id:
                continue
            records_to_create.append(ZuluProductRepresentation(sku=normalized_sku))
        if records_to_create:
            logger.info(f"QMS {DOMAIN_NAME} is saving bulk ProductRepresentation {len(records_to_create)} data to db")
            products = ZuluProductRepresentation.objects.bulk_create(records_to_create, batch_size=chunk_size)
            for product in products:
                products_sku_to_id[product.sku] = product.id
            report["product_representations_created"] = len(records_to_create)
        else:
            report["product_representations_created"] = 0
        report["product_representations_total"] = len(products_sku_to_id)

        logger.info(f"QMS {DOMAIN_NAME} Gather Quantity channel={channel.idx} pulled {dataset_total} skus")
        records_to_create = []
        report["pit_quantities_created"] = 0
        cnt = 0
        for sku, quantity in dataset.items():
            cnt += 1
            normalized_sku = normalize_sku(sku)
            pit_qty = ZuluPitQuantityByChannel(
                pit=pit,
                channel=channel,
                product_id=products_sku_to_id[normalized_sku],
                quantity_available=quantity,
                quantity_locked=0,
            )
            records_to_create.append(pit_qty)
            if len(records_to_create) % chunk_size == 0:  # save to disc in bulks
                save_chunk()
                records_to_create = []
        save_chunk()
        logger.info(f"QMS {DOMAIN_NAME} Gather Quantity channel={channel.idx} is done")
        bev.finish_with_success(finish_tag="ok", details=report)
        return {"status": "ok"}
    except BaseException as e:
        bev.finish_with_exception(e, details=report)
        pit.set_as_error()
        raise e
