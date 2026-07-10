# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv

from django_qms.storage_managers import StorageDataSet


def get_quantities_as_dataset(csv_path: str):
    result = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for item in reader:
            result.append(item)
    return result


def push_quantities_to_csv(csv_path: str, dataset: StorageDataSet):
    with open(csv_path, "w") as file:
        writer = csv.writer(file)
        writer.writerow(["sku", "quantity"])
        for item in dataset.items:
            writer.writerow([item.sku, item.quantity])
