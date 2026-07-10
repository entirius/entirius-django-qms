# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from process_logger import ProcessLogger

from django_qms.models import XrayPointInTime, XrayQuantityByStorage, XrayStorage, XrayStorageLink
from django_qms.settings import QMS_XRAY_CHUNK_SIZE

logger = ProcessLogger(process_name="QMS_XRAY")


@shared_task(queue="quantities")
def xray_linked_storages(channel_idx: int, pit_id: int) -> bool:
    logger.add_log_param("channel_idx", channel_idx)
    try:
        pit: XrayPointInTime = XrayPointInTime.objects.get(pk=pit_id, channel__idx=channel_idx)
    except ObjectDoesNotExist:
        logger.error(f"PointInTime with id={pit_id} for channel={channel_idx} does not exist")
        return False

    logger.add_log_param("pit", pit.pit)
    if not pit.is_processing():
        logger.error(f"PointInTime with id={pit_id} for channel={channel_idx} is not processing")
        raise Exception(f"Halting work on not processing pit={pit.pit}")

    channel = pit.channel

    try:
        # Pull quantities from saved input storages
        input_storages = XrayStorage.objects.filter(
            channel=channel, data_direction=XrayStorage.DataDirection.STORAGE_INPUT
        ).all()

        for input_storage in input_storages:
            output_storages = XrayStorageLink.objects.filter(storage_input=input_storage)
            if output_storages.count() == 0:
                logger.warning(f"No output storages for input storage={input_storage}")
                continue

            if output_storages.count() > 1:
                logger.warning(
                    f"Multiple output storages for input storage={input_storage}. Multiple option not implemented yet."
                )
                continue

            output_storage = output_storages.first().storage_output

            quantities = XrayQuantityByStorage.objects.filter(storage=input_storage, pit=pit).all()

            # Save quantities
            quantities_to_create = []
            for quantity in quantities:
                quantity: XrayQuantityByStorage
                quantities_to_create.append(
                    XrayQuantityByStorage(
                        storage=output_storage, pit=pit, product=quantity.product, quantity_int=quantity.quantity_int
                    )
                )
            XrayQuantityByStorage.objects.bulk_create(quantities_to_create, batch_size=QMS_XRAY_CHUNK_SIZE)

            logger.info(f"Saved {len(quantities_to_create)} quantities for channel={channel_idx}, pit={pit.pit}")

    except BaseException as e:
        logger.exception(e)
        pit.set_as_error()
        raise e
    else:
        pit.set_as_done()

    return True
