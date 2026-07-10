# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from itertools import groupby
from operator import itemgetter

from celery import shared_task

from django_qms.bi import QM_CreatePitQuantityEvent
from django_qms.enums import QMSType
from django_qms.models import ZuluPitQuantity, ZuluPitQuantityByChannel, ZuluPointInTime
from django_qms.settings import QMS_PIT_QUANTITY_CHUNK_SIZE

DOMAIN_NAME = QMSType.ZULU

logger = logging.getLogger(__name__)


@shared_task(queue="quantities")
def zulu_create_pit_quantity(pit_id: int) -> dict:
    def save_chunk(pit, records_to_create, cnt, total):
        if not records_to_create:
            return
        logger.info(f"QMS {DOMAIN_NAME} create PIT quantity pit={pit} progress {cnt} / {total}")
        ZuluPitQuantity.objects.bulk_create(records_to_create, batch_size=50000)
        report["pit_quantities_created"] += len(records_to_create)

    pit = ZuluPointInTime.objects.get(pk=pit_id)
    if pit.proces_status != ZuluPointInTime.ProcessStatus.PROCESSING:
        raise Exception(f"Halting work on not processing pit={pit.pit}")
    bev = QM_CreatePitQuantityEvent(pit=pit.pit, is_ongoing_event=True)
    report = {"pit_quantities_created": 0}
    chunk_size = QMS_PIT_QUANTITY_CHUNK_SIZE
    try:
        logger.info(f"QMS {DOMAIN_NAME} create PIT quantity is loading products data")
        qty_by_channel = ZuluPitQuantityByChannel.objects.filter(pit=pit).values("product__pk", "quantity_available")
        key_func = itemgetter("product__pk")
        grouped_by_product = groupby(sorted(qty_by_channel, key=key_func), key=key_func)
        total = len(qty_by_channel)
        logger.info(f"QMS {DOMAIN_NAME} create PIT quantities is starting")
        records_to_create = []
        cnt = 0
        for product_id, group in grouped_by_product:
            cnt += 1
            product_qty = sum(elem["quantity_available"] for elem in group)
            records_to_create.append(ZuluPitQuantity(pit=pit, product_id=product_id, quantity_available=product_qty))
            if len(records_to_create) % chunk_size == 0:  # save to disc in bulks
                save_chunk(pit.pit, records_to_create, cnt, total)
                records_to_create = []
        save_chunk(pit.pit, records_to_create, cnt, total)
        bev.finish_with_success(finish_tag="ok", details=report)
        return {"status": "ok"}
    except BaseException as e:
        bev.finish_with_exception(e, details=report)
        pit.set_as_error()
        raise e
