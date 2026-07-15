# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import logging
import os
from dataclasses import asdict, dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class StorageItem:
    sku: str
    quantity: int
    shipping_date: str

    def __init__(self, sku: str, quantity: int, shipping_date: str = ""):
        self.sku = sku
        self.quantity = quantity
        self.shipping_date = shipping_date

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)


@dataclass
class StorageDataSet:
    items: list[StorageItem]


class StorageManager:
    qms_type: str | None = None

    def __init__(self, connection_data):
        self.connection_data = connection_data
        self.channel_idx = None

    def push_data(self, data_set: StorageDataSet):
        raise NotImplementedError("Called function from abstract class")

    def get_data(self) -> StorageDataSet:
        raise NotImplementedError("Called function from abstract class")


class CheckoutStorageManager(StorageManager):
    def push_data(self, data: StorageDataSet):
        try:
            from django_checkout.models import Stock
        except ImportError:
            raise Exception("CheckoutStorageManager.push_data() can not import django_checkout module.")
        channel_idx = self.connection_data.get("channel_idx", None)
        if channel_idx is None:
            channel_idx = self.channel_idx
            if channel_idx is None:
                raise Exception(
                    'Can not run CheckoutStorageManager.push_data(), "channel_idx" is missing in "connection_data"'
                )
        supplier_code = self.connection_data.get("supplier_code", None)

        logger.info(
            f"QMS {self.qms_type} Push Quantity to Checkout on channel={channel_idx} "
            f"and supplier={supplier_code} is starting"
        )
        # uwaga! channel_idx musi byc taki jak channgel_idx w django_checkout
        # supplier_code jesli jest None to zostanie ustawiony supplier global z tego samego channela
        Stock.objects.update_from_qms_dataset(asdict(data), channel_idx, supplier_code)
        logger.info(f"QMS {self.qms_type} Push Quantity to Checkout is done")

    def get_data(self) -> StorageDataSet:
        raise NotImplementedError("CheckoutStorageManager.get_data() is not yet implemented")


class CsvStorageManager(StorageManager):
    def get_data(self) -> StorageDataSet:
        from django_qms.integrations.csv import get_quantities_as_dataset

        csv_path = self.connection_data.get("csv_path", None)
        if csv_path is None:
            raise FileExistsError(f"There is no CSV file for given path: {csv_path}")
        # Substitute only placeholders actually present — the host may not define the
        # other dirs; settings may be pathlib.Path (str.replace needs str args).
        csv_path = str(csv_path)
        for placeholder, setting_name in (
            ("%DATA_DIR%", "DATA_DIR"),
            ("%IMPORT_DIR%", "IMPORT_DIR"),
            ("%EXPORT_DIR%", "EXPORT_DIR"),
            ("%TMP_DIR%", "TMP_DIR"),
        ):
            if placeholder in csv_path:
                csv_path = csv_path.replace(placeholder, str(getattr(settings, setting_name)))
        csv_path = os.path.abspath(csv_path)
        data = get_quantities_as_dataset(csv_path)
        items = []
        for item in data:
            items.append(StorageItem(**item))
        return StorageDataSet(items=items)

    def push_data(self, data_set: StorageDataSet):
        from django_qms.integrations.csv import push_quantities_to_csv

        csv_path = self.connection_data.get("csv_path", None)
        push_quantities_to_csv(csv_path, data_set)


class StorageManagerFake(StorageManager):
    def __init__(self, connection_data: dict):
        super().__init__(connection_data)
        self.storage_dataset = {}

    def get_data(self):
        return self.storage_dataset

    def push_data(self, data_set: StorageDataSet):
        self.storage_dataset = data_set
