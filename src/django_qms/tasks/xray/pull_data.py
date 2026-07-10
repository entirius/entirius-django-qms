# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from idx_normalizator import normalize_sku
from process_logger import ProcessLogger

from django_qms.models import XrayPointInTime, XrayProductRepresentation, XrayQuantityByStorage, XrayStorage
from django_qms.settings import QMS_XRAY_CHUNK_SIZE
from django_qms.storage_managers import StorageDataSet

logger = ProcessLogger(process_name="QMS_XRAY")


@shared_task(queue="quantities")
def xray_pull_data(channel_idx: str, pit_id: int) -> bool:
    logger.add_log_param("channel_idx", channel_idx)
    try:
        pit: XrayPointInTime = XrayPointInTime.objects.get(pk=pit_id, channel__idx=channel_idx)
    except ObjectDoesNotExist:
        logger.error(f"PointInTime with id={pit_id} for channel={channel_idx} does not exist")
        return False

    logger.add_log_param("pit", pit.pit)
    channel = pit.channel
    pit.set_as_processing()

    storage: XrayStorage
    for storage in channel.xray_storages.filter(data_direction=XrayStorage.DataDirection.STORAGE_INPUT):
        try:
            data: StorageDataSet = storage.pull_quantity()
            logger.add_log_param("storage", storage.code)
            logger.info(f"Pulled data from storage={storage}")

            # Rearrange data
            quantities = {}
            duplicates = 0
            for item in data.items:
                if item.sku not in quantities:
                    quantities[item.sku] = item.quantity
                else:
                    # SAP zwraca smietnik i duzo SKU ma duplikaty z stanem 0 wiec zapisuje stan większy
                    if item.quantity > quantities[item.sku]:
                        quantities[item.sku] = item.quantity
                    duplicates += 1
                    logger.add_log_param_once("sku", item.sku)
                    logger.debug(f"Found duplicated sku={item.sku} in storage={storage.code}")

            if duplicates > 0:
                logger.warning(f"Found {duplicates}/{len(data.items)} duplicated skus in storage={storage.code}")

            # Pull all product representations
            products_sku_to_id = {
                product_sku: product_id
                for product_id, product_sku in XrayProductRepresentation.objects.all().values_list("id", "sku")
            }

            # Check if some are missing
            products_to_create = {}
            for sku in quantities.keys():
                normalized_sku = normalize_sku(sku)
                if normalized_sku not in products_sku_to_id and normalized_sku not in products_to_create:
                    products_to_create[normalized_sku] = XrayProductRepresentation(sku=normalized_sku)

            # If some are missing, create them
            if len(products_to_create) > 0:
                logger.info(f"Creating {len(products_to_create)} new ProductRepresentations")
                products = XrayProductRepresentation.objects.bulk_create(
                    products_to_create.values(), batch_size=QMS_XRAY_CHUNK_SIZE
                )
                for product in products:
                    products_sku_to_id[product.sku] = product.id

            # Save storage quantities
            quantities_to_create = []
            for sku, quantity in quantities.items():
                normalized_sku = normalize_sku(sku)
                storage_qty = XrayQuantityByStorage(
                    pit=pit, storage=storage, product_id=products_sku_to_id[normalized_sku], quantity_int=quantity
                )
                quantities_to_create.append(storage_qty)

            XrayQuantityByStorage.objects.bulk_create(quantities_to_create, batch_size=QMS_XRAY_CHUNK_SIZE)
            logger.info(f"Saved {len(quantities_to_create)} quantities for storage={storage.code}")
        except BaseException as e:
            logger.exception(e)
            pit.set_as_error()

    return True
