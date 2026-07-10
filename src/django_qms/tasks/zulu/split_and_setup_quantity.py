# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from celery import shared_task

from django_qms.bi import QM_SplitAndSetupEvent
from django_qms.enums import QMSType
from django_qms.models import Channel, ZuluPitQuantity, ZuluPitSetupQuantity, ZuluPointInTime
from django_qms.settings import QMS_PIT_SETUP_QUANTITY_CHUNK_SIZE

DOMAIN_NAME = QMSType.ZULU

logger = logging.getLogger(__name__)


@shared_task(queue="quantities")
def zulu_split_and_setup_quantity(pit_id: int) -> dict:
    def save_chunk(pit, records_to_create, cnt, total):
        if not records_to_create:
            return
        logger.info(f"QMS {DOMAIN_NAME} Split and Setup Quantity pit={pit} progress {cnt} / {total}")
        ZuluPitSetupQuantity.objects.bulk_create(records_to_create, batch_size=50000)

    chunk_size = QMS_PIT_SETUP_QUANTITY_CHUNK_SIZE
    pit: ZuluPointInTime
    pq: ZuluPitQuantity
    pit = ZuluPointInTime.objects.get(pk=pit_id)
    if pit.proces_status != ZuluPointInTime.ProcessStatus.PROCESSING:
        raise Exception(f"Halting work on not processing pit={pit.pit}")
    logger.info(f"QMS {DOMAIN_NAME} Split and Setup Quantity is starting")
    bev = QM_SplitAndSetupEvent(pit=pit.pit, is_ongoing_event=True)
    report = {"per-storage": {}}
    cnt = 0
    try:
        channels_out_cache = {}
        storages_cache = {}
        for channel in Channel.objects.all().exclude(stock_weight=0):
            channels_out_cache[channel.idx] = channel
            storages_cache[channel.idx] = {}
            for storage in channel.zulu_storages.all():
                storages_cache[channel.idx][storage.code] = storage
        pqs = pit.zulupitquantity_set.all()
        total = len(pqs)
        records_to_create = []
        for pq in pqs:
            pq: ZuluPitQuantity
            cnt += 1
            if len(channels_out_cache) == 1:
                # speedup hack if only 1 out channel
                split_values = {}
                split_values[next(iter(channels_out_cache))] = pq.quantity_available
            else:
                split_values = pq.product.split_by_algo(pq.quantity_available)
            # if cnt == 1:
            #     bi_event.debug(
            #         "Example: for quantity_available={} split_values={}".format(
            #             pq.quantity_available, split_values
            #         )
            #     )
            for channel_idx, channel_qty in split_values.items():
                # channel = Channel.objects.get(idx=channel_idx)
                channel = channels_out_cache[channel_idx]
                if len(storages_cache[channel_idx]) == 1:
                    # speedup hack if there is only 1 storage
                    storage = next(iter(storages_cache[channel_idx].values()))
                    psq = ZuluPitSetupQuantity(
                        pit=pit, channel=channel, product=pq.product, storage=storage, quantity_available=channel_qty
                    )
                    records_to_create.append(psq)
                    key = f"{channel_idx}.{storage.code}"
                    if key not in report["per-storage"]:
                        report["per-storage"][key] = 1
                    else:
                        report["per-storage"][key] += 1
                else:
                    storages = channel.zulu_storages.all().order_by("pk")
                    if not storages:
                        raise Exception(
                            f'Can not split quantities for channel="{channel.idx}" because storages are not configured'
                        )
                    ch_split_values = {}
                    # tymczasowo tylko algorytm typu "Equal"
                    divider = len(storages)
                    if divider == 1:
                        ch_split_values[storages[0].code] = channel_qty
                    else:
                        main_num = int(channel_qty / divider)
                        rest = channel_qty - (main_num * divider)
                        for storage in storages:
                            ch_split_values[storage.code] = main_num
                        ch_split_values[storages[0].code] += rest

                    for storage_code, storage_qty in ch_split_values.items():
                        storage = channel.zulu_storages.get(code=storage_code)
                        psq = ZuluPitSetupQuantity(
                            pit=pit,
                            channel=channel,
                            product=pq.product,
                            storage=storage,
                            quantity_available=storage_qty,
                        )
                        records_to_create.append(psq)
                        key = f"{channel.idx}.{storage.code}"
                        if key not in report["per-storage"]:
                            report["per-storage"][key] = 1
                        else:
                            report["per-storage"][key] += 1
            if len(records_to_create) % chunk_size == 0:  # save to disc in bulks
                save_chunk(pit.pit, records_to_create, cnt, total)
                records_to_create = []
        save_chunk(pit.pit, records_to_create, cnt, total)
        logger.info(f"QMS {DOMAIN_NAME} Split and Setup Quantity is done")
        bev.finish_with_success(finish_tag="QMS Split and Setup Quantity is done", details=report)
        return {"status": "ok"}
    except BaseException as e:
        bev.finish_with_exception(e, details=report)
        pit.set_as_error()
        raise e
