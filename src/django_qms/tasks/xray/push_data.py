# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from process_logger import ProcessLogger

from django_qms.models import XrayPointInTime, XrayQuantityByStorage, XrayStorage
from django_qms.storage_managers import StorageDataSet, StorageItem

logger = ProcessLogger(process_name="QMS_XRAY")


@shared_task(queue="quantities")
def xray_push_data(channel_idx: int, pit_id: int) -> bool:
    logger.add_log_param("channel_idx", channel_idx)
    try:
        pit: XrayPointInTime = XrayPointInTime.objects.get(pk=pit_id, channel__idx=channel_idx)
    except ObjectDoesNotExist:
        logger.error(f"PointInTime with id={pit_id} for channel={channel_idx} does not exist")
        return False

    logger.add_log_param("pit", pit.pit)
    if not pit.is_done():
        logger.error(f"PointInTime with id={pit_id} for channel={channel_idx} is not done")
        raise Exception(f"Halting work on not done pit={pit.pit}")

    channel = pit.channel

    try:
        storages = XrayStorage.objects.filter(
            channel=channel, data_direction=XrayStorage.DataDirection.STORAGE_OUTPUT
        ).all()

        if len(storages) == 0:
            logger.error(f"No output storages for channel={channel_idx}")
            raise Exception(f"No output storages for channel={channel_idx}")

        storage: XrayStorage
        for storage in storages:
            quantities = XrayQuantityByStorage.objects.filter(storage=storage, pit=pit).all()
            items = []
            for quantitiy in quantities:
                items.append(StorageItem(sku=quantitiy.product.sku, quantity=quantitiy.quantity_int))
            logger.info(f"Loaded {len(items)} items to cache")

            logger.add_log_param("storage", storage.code)
            storage.push_quantity(data=StorageDataSet(items=items))
            logger.info(f"Pushed storage={storage} data to {storage.storage_manager}")
    except Exception as e:
        logger.exception(e)
        raise e

    return True
