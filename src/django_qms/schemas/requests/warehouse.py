# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from pydantic import BaseModel, Field


class WarehouseStockItem(BaseModel):
    sku: str = Field(description="Product SKU identifier", examples=["ENT-S001"])
    quantity: int = Field(ge=0, description="Stock quantity (non-negative)", examples=[100])


class WarehouseStockBulkRequest(BaseModel):
    items: list[WarehouseStockItem] = Field(
        max_length=10000,
        description="List of SKU/quantity pairs to upsert (max 10,000)",
        examples=[[{"sku": "ENT-S001", "quantity": 100}, {"sku": "ENT-S002", "quantity": 50}]],
    )


class WarehouseStockBySkuItem(BaseModel):
    warehouse_code: str = Field(description="Warehouse code", examples=["wh-manual"])
    quantity: int = Field(ge=0, description="Stock quantity (non-negative)", examples=[100])


class WarehouseStockBySkuRequest(BaseModel):
    items: list[WarehouseStockBySkuItem] = Field(
        min_length=1,
        max_length=100,
        description="List of warehouse/quantity pairs to upsert for a single SKU",
        examples=[[{"warehouse_code": "wh-manual", "quantity": 90}]],
    )
