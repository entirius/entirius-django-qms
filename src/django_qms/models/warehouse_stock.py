# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models
from django_utils.models.base_model import BaseModel

from .warehouse import Warehouse


class WarehouseStock(BaseModel):
    """Stock quantity for a single SKU in a single warehouse.

    Quantity is always non-negative (enforced by PositiveIntegerField + DB CHECK constraint).
    The (warehouse, sku) pair is unique — one row per product per warehouse.
    """

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stocks")
    sku = models.CharField(max_length=128, db_index=True)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "django_qms_warehousestock"
        constraints = [
            models.UniqueConstraint(fields=["warehouse", "sku"], name="warehousestock_warehouse_sku_unique"),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="warehousestock_quantity_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.warehouse.code}:{self.sku} = {self.quantity}"
