# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Warehouse primary key", examples=[1])
    code: str = Field(description="Unique warehouse code", examples=["wh-manual"])
    name: str = Field(description="Display name", examples=["Main Warehouse"])
    description: str = Field(description="Optional description", examples=["Primary warehouse"])
    source_type: Literal["manual", "integration"] = Field(
        description="manual = CMS edits, integration = CSV/API (CMS read-only)", examples=["manual"]
    )
    is_active: bool = Field(description="Inactive warehouses do not propagate to Checkout", examples=[True])
    last_synced_at: datetime | None = Field(
        description="Last integration sync timestamp (null for manual warehouses)", examples=[None]
    )
    channel_idxs: list[str] = Field(
        default_factory=list, description="Assigned channel idx codes", examples=[["default-europe", "b2b-pro"]]
    )


class WarehouseStockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str = Field(description="Product SKU", examples=["ENT-S001"])
    quantity: int = Field(ge=0, description="Stock quantity", examples=[100])
    created_at: datetime = Field(description="Record creation timestamp")
    modified_at: datetime = Field(description="Last modification timestamp")


class WarehouseStockListResponse(BaseModel):
    count: int = Field(description="Total number of stock records")
    next: str | None = Field(description="URL of the next page")
    previous: str | None = Field(description="URL of the previous page")
    results: list[WarehouseStockResponse] = Field(description="Page of stock records")
