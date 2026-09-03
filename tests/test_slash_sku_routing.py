# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Slash-containing SKU routing (e.g. "ENT-1001/N") for stock-by-sku endpoints.

<path:sku> matches slashes; the /edit/ route MUST resolve before the bare list route.
"""

import pytest
from django.urls import resolve

from django_qms.models import WarehouseStock

STOCK_BY_SKU_URL = "/api/qms/v2/admin/stock-by-sku/"
SLASH_SKU = "ENT-1001/N"
SKUS = [SLASH_SKU, "ENT-2004/NR", "ENT-PLAIN-001"]


class TestStockBySkuRouting:
    @pytest.mark.parametrize("sku", SKUS)
    def test_list_route_resolves(self, sku):
        match = resolve(f"{STOCK_BY_SKU_URL}{sku}/")

        assert match.url_name == "qms-stock-by-sku-list"
        assert match.kwargs["sku"] == sku

    @pytest.mark.parametrize("sku", SKUS)
    def test_edit_route_resolves(self, sku):
        match = resolve(f"{STOCK_BY_SKU_URL}{sku}/edit/")

        assert match.url_name == "qms-stock-by-sku-edit"
        assert match.kwargs["sku"] == sku


@pytest.mark.django_db
class TestStockBySkuSlashEndpoints:
    def test_list_returns_quantity_for_slash_sku(self, admin_client, manual_warehouse):
        WarehouseStock.objects.create(warehouse=manual_warehouse, sku=SLASH_SKU, quantity=64)

        response = admin_client.get(f"{STOCK_BY_SKU_URL}{SLASH_SKU}/")

        assert response.status_code == 200
        entry = next(row for row in response.json() if row["warehouse_code"] == "wh-manual")
        assert entry["quantity"] == 64

    def test_edit_updates_quantity_for_slash_sku(self, admin_client, manual_warehouse):
        payload = {"items": [{"warehouse_code": "wh-manual", "quantity": 12}]}

        response = admin_client.patch(f"{STOCK_BY_SKU_URL}{SLASH_SKU}/edit/", payload, format="json")

        assert response.status_code == 200
        assert WarehouseStock.objects.get(warehouse=manual_warehouse, sku=SLASH_SKU).quantity == 12
