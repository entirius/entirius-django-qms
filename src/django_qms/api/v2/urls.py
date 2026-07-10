# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from django_qms.api.v2.views import WarehouseViewSet

warehouse_list = WarehouseViewSet.as_view({"get": "list"})
warehouse_detail = WarehouseViewSet.as_view({"get": "retrieve"})
stock_list = WarehouseViewSet.as_view({"get": "stock_list"})
stock_bulk_edit = WarehouseViewSet.as_view({"patch": "stock_bulk_edit"})
stock_import_csv = WarehouseViewSet.as_view({"post": "stock_import_csv"})
products_list = WarehouseViewSet.as_view({"get": "products"})
stock_by_sku_list = WarehouseViewSet.as_view({"get": "stock_by_sku_list"})
stock_by_sku_edit = WarehouseViewSet.as_view({"patch": "stock_by_sku_edit"})

urlpatterns = [
    path("warehouses/", warehouse_list, name="qms-warehouse-list"),
    path("warehouses/<str:code>/", warehouse_detail, name="qms-warehouse-detail"),
    path("warehouses/<str:code>/stock/", stock_list, name="qms-stock-list"),
    path("warehouses/<str:code>/stock/edit/", stock_bulk_edit, name="qms-stock-bulk-edit"),
    path("warehouses/<str:code>/stock/import-csv/", stock_import_csv, name="qms-stock-import-csv"),
    path("warehouses/<str:code>/products/", products_list, name="qms-products-list"),
    path("stock-by-sku/<str:sku>/", stock_by_sku_list, name="qms-stock-by-sku-list"),
    path("stock-by-sku/<str:sku>/edit/", stock_by_sku_edit, name="qms-stock-by-sku-edit"),
]
