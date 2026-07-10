# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for Admin API v2 warehouse endpoints.

Covers: auth (401/403/200), list, retrieve, filters, bulk PATCH, error cases.
"""

import pytest

from django_qms.models import WarehouseStock

BASE_URL = "/api/qms/v2/admin/warehouses/"


@pytest.mark.django_db
class TestWarehouseListAuth:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(BASE_URL)
        assert response.status_code == 401

    def test_regular_user_returns_403(self, regular_client):
        response = regular_client.get(BASE_URL)
        assert response.status_code == 403

    def test_admin_returns_200(self, admin_client, manual_warehouse):
        response = admin_client.get(BASE_URL)
        assert response.status_code == 200


@pytest.mark.django_db
class TestWarehouseList:
    def test_returns_all_warehouses(self, admin_client, manual_warehouse, integration_warehouse):
        response = admin_client.get(BASE_URL)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_filter_is_active_true(self, admin_client, manual_warehouse, inactive_warehouse):
        response = admin_client.get(BASE_URL, {"is_active": "true"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "wh-manual"

    def test_filter_is_active_false(self, admin_client, manual_warehouse, inactive_warehouse):
        response = admin_client.get(BASE_URL, {"is_active": "false"})
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "wh-inactive"

    def test_search_by_code(self, admin_client, manual_warehouse, integration_warehouse):
        response = admin_client.get(BASE_URL, {"search": "manual"})
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "wh-manual"

    def test_search_by_name(self, admin_client, manual_warehouse, integration_warehouse):
        response = admin_client.get(BASE_URL, {"search": "Integration"})
        data = response.json()
        assert len(data) == 1

    def test_response_includes_channel_idxs(self, admin_client, manual_warehouse):
        response = admin_client.get(BASE_URL)
        data = response.json()
        assert "channel_idxs" in data[0]
        assert "test-channel" in data[0]["channel_idxs"]


@pytest.mark.django_db
class TestWarehouseRetrieve:
    def test_retrieve_existing(self, admin_client, manual_warehouse):
        response = admin_client.get(f"{BASE_URL}wh-manual/")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "wh-manual"
        assert data["source_type"] == "manual"
        assert data["is_active"] is True

    def test_retrieve_not_found(self, admin_client):
        response = admin_client.get(f"{BASE_URL}nonexistent/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestStockList:
    def test_stock_list_paginated(self, admin_client, manual_warehouse, stock_items):
        response = admin_client.get(f"{BASE_URL}wh-manual/stock/")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "results" in data
        assert data["count"] == 3

    def test_stock_list_search_by_sku(self, admin_client, manual_warehouse, stock_items):
        response = admin_client.get(f"{BASE_URL}wh-manual/stock/", {"search": "001"})
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["sku"] == "SKU-001"

    def test_stock_list_warehouse_not_found(self, admin_client):
        response = admin_client.get(f"{BASE_URL}nonexistent/stock/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestStockBulkEdit:
    def test_bulk_edit_creates_stock(self, admin_client, manual_warehouse):
        payload = {"items": [{"sku": "NEW-SKU", "quantity": 42}]}
        response = admin_client.patch(f"{BASE_URL}wh-manual/stock/edit/", payload, format="json")
        assert response.status_code == 200
        assert WarehouseStock.objects.get(warehouse=manual_warehouse, sku="NEW-SKU").quantity == 42

    def test_bulk_edit_updates_existing(self, admin_client, manual_warehouse, stock_items):
        payload = {"items": [{"sku": "SKU-001", "quantity": 999}]}
        response = admin_client.patch(f"{BASE_URL}wh-manual/stock/edit/", payload, format="json")
        assert response.status_code == 200
        assert WarehouseStock.objects.get(warehouse=manual_warehouse, sku="SKU-001").quantity == 999

    def test_bulk_edit_multiple_items(self, admin_client, manual_warehouse):
        payload = {
            "items": [
                {"sku": "BULK-001", "quantity": 10},
                {"sku": "BULK-002", "quantity": 20},
                {"sku": "BULK-003", "quantity": 30},
            ]
        }
        response = admin_client.patch(f"{BASE_URL}wh-manual/stock/edit/", payload, format="json")
        assert response.status_code == 200
        assert WarehouseStock.objects.filter(warehouse=manual_warehouse).count() == 3

    def test_bulk_edit_negative_quantity_rejected(self, admin_client, manual_warehouse):
        payload = {"items": [{"sku": "NEG", "quantity": -1}]}
        response = admin_client.patch(f"{BASE_URL}wh-manual/stock/edit/", payload, format="json")
        assert response.status_code == 400

    def test_bulk_edit_integration_warehouse_rejected(self, admin_client, integration_warehouse):
        payload = {"items": [{"sku": "X", "quantity": 1}]}
        response = admin_client.patch(f"{BASE_URL}wh-integration/stock/edit/", payload, format="json")
        assert response.status_code == 400
        assert "integration" in response.json()["detail"].lower()

    def test_bulk_edit_inactive_warehouse_rejected(self, admin_client, inactive_warehouse):
        payload = {"items": [{"sku": "X", "quantity": 1}]}
        response = admin_client.patch(f"{BASE_URL}wh-inactive/stock/edit/", payload, format="json")
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()

    def test_bulk_edit_warehouse_not_found(self, admin_client):
        payload = {"items": [{"sku": "X", "quantity": 1}]}
        response = admin_client.patch(f"{BASE_URL}nonexistent/stock/edit/", payload, format="json")
        assert response.status_code == 404

    def test_bulk_edit_auth_required(self, api_client, manual_warehouse):
        payload = {"items": [{"sku": "X", "quantity": 1}]}
        response = api_client.patch(f"{BASE_URL}wh-manual/stock/edit/", payload, format="json")
        assert response.status_code == 401

    def test_bulk_edit_regular_user_returns_403(self, regular_client, manual_warehouse):
        payload = {"items": [{"sku": "X", "quantity": 1}]}
        response = regular_client.patch(f"{BASE_URL}wh-manual/stock/edit/", payload, format="json")
        assert response.status_code == 403


@pytest.mark.django_db
class TestStockImportCSVApi:
    def test_import_csv_auth_required(self, api_client, manual_warehouse):
        response = api_client.post(f"{BASE_URL}wh-manual/stock/import-csv/")
        assert response.status_code == 401

    def test_import_csv_regular_user_returns_403(self, regular_client, manual_warehouse):
        response = regular_client.post(f"{BASE_URL}wh-manual/stock/import-csv/")
        assert response.status_code == 403

    def test_import_csv_no_file_returns_400(self, admin_client, manual_warehouse):
        response = admin_client.post(f"{BASE_URL}wh-manual/stock/import-csv/")
        assert response.status_code == 400
        assert "No file" in response.json()["detail"]

    def test_import_csv_warehouse_not_found(self, admin_client):
        response = admin_client.post(f"{BASE_URL}nonexistent/stock/import-csv/")
        assert response.status_code == 404

    def test_import_csv_success(self, admin_client, manual_warehouse):
        csv_content = b"sku,quantity\nCSV-001,10\nCSV-002,20\n"
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv_file = SimpleUploadedFile("stock.csv", csv_content, content_type="text/csv")
        response = admin_client.post(f"{BASE_URL}wh-manual/stock/import-csv/", {"file": csv_file}, format="multipart")
        assert response.status_code == 200
        data = response.json()
        assert data["rows_imported"] == 2
        assert WarehouseStock.objects.filter(warehouse=manual_warehouse).count() == 2

    def test_import_csv_integration_warehouse_rejected(self, admin_client, integration_warehouse):
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv_file = SimpleUploadedFile("stock.csv", b"sku,quantity\nX,1\n", content_type="text/csv")
        response = admin_client.post(
            f"{BASE_URL}wh-integration/stock/import-csv/", {"file": csv_file}, format="multipart"
        )
        assert response.status_code == 400


STOCK_BY_SKU_URL = "/api/qms/v2/admin/stock-by-sku/"


@pytest.mark.django_db
class TestStockBySkuList:
    def test_returns_stock_across_warehouses(self, admin_client, manual_warehouse, stock_items):
        response = admin_client.get(f"{STOCK_BY_SKU_URL}SKU-001/")
        assert response.status_code == 200
        data = response.json()
        assert any(d["warehouse_code"] == "wh-manual" and d["quantity"] == 100 for d in data)

    def test_auth_required(self, api_client):
        response = api_client.get(f"{STOCK_BY_SKU_URL}SKU-001/")
        assert response.status_code == 401

    def test_regular_user_403(self, regular_client):
        response = regular_client.get(f"{STOCK_BY_SKU_URL}SKU-001/")
        assert response.status_code == 403

    def test_unknown_sku_returns_empty_quantities(self, admin_client, manual_warehouse):
        response = admin_client.get(f"{STOCK_BY_SKU_URL}NONEXISTENT/")
        assert response.status_code == 200
        data = response.json()
        assert all(d["quantity"] == 0 for d in data)


@pytest.mark.django_db
class TestStockBySkuEdit:
    def test_updates_stock_for_sku(self, admin_client, manual_warehouse, stock_items):
        payload = {"items": [{"warehouse_code": "wh-manual", "quantity": 77}]}
        response = admin_client.patch(f"{STOCK_BY_SKU_URL}SKU-001/edit/", payload, format="json")
        assert response.status_code == 200
        assert WarehouseStock.objects.get(warehouse=manual_warehouse, sku="SKU-001").quantity == 77

    def test_rejects_integration_warehouse(self, admin_client, integration_warehouse, stock_items):
        payload = {"items": [{"warehouse_code": "wh-integration", "quantity": 5}]}
        response = admin_client.patch(f"{STOCK_BY_SKU_URL}SKU-001/edit/", payload, format="json")
        assert response.status_code == 400

    def test_rejects_invalid_payload(self, admin_client, manual_warehouse):
        payload = {"items": [{"warehouse_code": "wh-manual", "quantity": -1}]}
        response = admin_client.patch(f"{STOCK_BY_SKU_URL}SKU-001/edit/", payload, format="json")
        assert response.status_code == 400

    def test_rejects_empty_items(self, admin_client, manual_warehouse):
        response = admin_client.patch(f"{STOCK_BY_SKU_URL}SKU-001/edit/", {"items": []}, format="json")
        assert response.status_code == 400

    def test_auth_required(self, api_client, manual_warehouse):
        payload = {"items": [{"warehouse_code": "wh-manual", "quantity": 1}]}
        response = api_client.patch(f"{STOCK_BY_SKU_URL}SKU-001/edit/", payload, format="json")
        assert response.status_code == 401


@pytest.mark.django_db
class TestProductsList:
    def test_returns_products_with_has_stock(self, admin_client, manual_warehouse, stock_items):
        response = admin_client.get(f"{BASE_URL}wh-manual/products/")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_filter_has_stock_true(self, admin_client, manual_warehouse, stock_items):
        response = admin_client.get(f"{BASE_URL}wh-manual/products/", {"has_stock": "true"})
        assert response.status_code == 200
        data = response.json()
        for item in data["results"]:
            assert item["has_stock"] is True

    def test_filter_has_stock_false(self, admin_client, manual_warehouse, stock_items):
        response = admin_client.get(f"{BASE_URL}wh-manual/products/", {"has_stock": "false"})
        assert response.status_code == 200

    def test_warehouse_not_found(self, admin_client):
        response = admin_client.get(f"{BASE_URL}nonexistent/products/")
        assert response.status_code == 404
