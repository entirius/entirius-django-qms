# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin API v2 ViewSet for Warehouse management.

All stock mutations go through warehouse_service — no ORM in views.
"""

from __future__ import annotations

import logging
import uuid

from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_qms.api.v2.pagination import AdminPageNumberPagination
from django_qms.api.v2.permissions import IsAdminUser
from django_qms.schemas.requests.warehouse import WarehouseStockBulkRequest, WarehouseStockBySkuRequest
from django_qms.schemas.responses.warehouse import WarehouseResponse, WarehouseStockListResponse, WarehouseStockResponse
from django_qms.services import warehouse_service
from django_qms.services.csv_import_service import import_csv_to_warehouse

logger = logging.getLogger("django_qms.api")

MAX_CSV_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _internal_error(exc: Exception) -> Response:
    error_id = uuid.uuid4().hex[:8]
    logger.error("Internal error [%s]: %s", error_id, exc, exc_info=True)
    return Response({"detail": f"Internal server error [{error_id}]"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _raise_pydantic_as_drf(exc: ValidationError) -> None:
    """Convert Pydantic ValidationError to DRF ValidationError with field-level details."""
    from rest_framework.exceptions import ValidationError as DRFValidationError

    errors = {}
    for error in exc.errors():
        loc = ".".join(str(part) for part in error["loc"])
        errors.setdefault(loc, []).append(error["msg"])
    raise DRFValidationError(errors)


@extend_schema_view(
    list=extend_schema(tags=["Warehouses"], summary="List warehouses"),
    retrieve=extend_schema(tags=["Warehouses"], summary="Retrieve warehouse by code"),
)
class WarehouseViewSet(ViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="List warehouses",
        description="Returns list of warehouses. Filter by is_active and search by code/name.",
        parameters=[
            OpenApiParameter(name="is_active", description="Filter by active status", type=bool, required=False),
            OpenApiParameter(name="search", description="Search by code or name", type=str, required=False),
        ],
        responses={200: WarehouseResponse},
    )
    def list(self, request):
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            is_active = is_active.lower() in ("true", "1", "yes")
        search = request.query_params.get("search")

        warehouses = warehouse_service.list_warehouses(is_active=is_active, search=search)
        data = [warehouse_service.serialize_warehouse(wh) for wh in warehouses]
        return Response(data)

    @extend_schema(
        summary="Retrieve warehouse by code",
        description="Returns warehouse detail including assigned channels.",
        parameters=[OpenApiParameter(name="code", location="path", description="Warehouse code")],
        responses={200: WarehouseResponse, 404: {"description": "Not found"}},
    )
    def retrieve(self, request, code=None):
        try:
            warehouse = warehouse_service.get_warehouse(code)
        except ObjectDoesNotExist:
            return Response({"detail": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(warehouse_service.serialize_warehouse(warehouse))

    @extend_schema(
        summary="List stock for warehouse",
        description="Returns paginated stock table for a warehouse. Search by SKU.",
        parameters=[
            OpenApiParameter(name="code", location="path", description="Warehouse code"),
            OpenApiParameter(name="search", description="Search by SKU", type=str, required=False),
        ],
        responses={200: WarehouseStockListResponse, 404: {"description": "Not found"}},
    )
    @action(detail=False, methods=["get"], url_path="(?P<code>[^/.]+)/stock")
    def stock_list(self, request, code=None):
        try:
            warehouse = warehouse_service.get_warehouse(code)
        except ObjectDoesNotExist:
            return Response({"detail": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)

        search = request.query_params.get("search")
        qs = warehouse_service.list_stock(warehouse, search=search)

        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        data = [
            {"sku": s.sku, "quantity": s.quantity, "created_at": s.created_at, "modified_at": s.modified_at}
            for s in page
        ]
        return paginator.get_paginated_response(data)

    @extend_schema(
        summary="Bulk edit stock quantities",
        description="Upsert stock records for a warehouse. Sends one signal with all changed SKUs.",
        parameters=[OpenApiParameter(name="code", location="path", description="Warehouse code")],
        request=WarehouseStockBulkRequest,
        responses={
            200: WarehouseStockResponse,
            400: {"description": "Validation error or warehouse not editable"},
            404: {"description": "Warehouse not found"},
        },
    )
    @action(detail=False, methods=["patch"], url_path="(?P<code>[^/.]+)/stock")
    def stock_bulk_edit(self, request, code=None):
        try:
            warehouse = warehouse_service.get_warehouse(code)
        except ObjectDoesNotExist:
            return Response({"detail": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            body = WarehouseStockBulkRequest(**request.data)
        except ValidationError as exc:
            _raise_pydantic_as_drf(exc)

        try:
            items = [{"sku": item.sku, "quantity": item.quantity} for item in body.items]
            result = warehouse_service.bulk_upsert_stock(warehouse, items)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return _internal_error(exc)

        return Response(result)

    @extend_schema(
        summary="Import stock from CSV",
        description="Upload a CSV file (sku,quantity columns) to bulk import stock. Max 10MB.",
        parameters=[OpenApiParameter(name="code", location="path", description="Warehouse code")],
        responses={
            200: {"description": "Import report"},
            400: {"description": "Validation error"},
            404: {"description": "Warehouse not found"},
        },
    )
    @action(detail=False, methods=["post"], url_path="(?P<code>[^/.]+)/stock/import-csv")
    def stock_import_csv(self, request, code=None):
        try:
            warehouse = warehouse_service.get_warehouse(code)
        except ObjectDoesNotExist:
            return Response({"detail": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        if file_obj.size and file_obj.size > MAX_CSV_FILE_SIZE:
            return Response(
                {"detail": f"File too large ({file_obj.size} bytes). Maximum is {MAX_CSV_FILE_SIZE} bytes."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report = import_csv_to_warehouse(warehouse, file_obj)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return _internal_error(exc)

        return Response(report)

    @extend_schema(
        summary="List products with stock availability",
        description="Returns all PIM products annotated with has_stock flag and quantity for this warehouse. "
        "Filter by has_stock=false to find products without stock.",
        parameters=[
            OpenApiParameter(name="code", location="path", description="Warehouse code"),
            OpenApiParameter(name="search", description="Search by SKU", type=str, required=False),
            OpenApiParameter(
                name="has_stock", description="Filter: true=with stock, false=without", type=str, required=False
            ),
        ],
        responses={
            200: {"description": "Paginated product list with has_stock flag"},
            404: {"description": "Not found"},
        },
    )
    @action(detail=False, methods=["get"], url_path="(?P<code>[^/.]+)/products")
    def products(self, request, code=None):
        try:
            warehouse = warehouse_service.get_warehouse(code)
        except ObjectDoesNotExist:
            return Response({"detail": "Warehouse not found"}, status=status.HTTP_404_NOT_FOUND)

        search = request.query_params.get("search")
        qs = warehouse_service.list_products_for_warehouse(warehouse, search=search)

        has_stock_filter = request.query_params.get("has_stock")
        if has_stock_filter == "true":
            qs = qs.filter(has_stock=True)
        elif has_stock_filter == "false":
            qs = qs.filter(has_stock=False)

        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        data = [{"sku": p.sku, "has_stock": p.has_stock, "quantity": p.stock_quantity} for p in page]
        return paginator.get_paginated_response(data)

    @extend_schema(
        summary="Get stock for a SKU across all warehouses",
        description="Product-centric view: returns all active warehouses with stock quantity for this SKU.",
        parameters=[OpenApiParameter(name="sku", location="path", description="Product SKU")],
        responses={200: {"description": "List of warehouse stock entries"}},
    )
    @action(detail=False, methods=["get"], url_path="stock-by-sku/(?P<sku>[^/.]+)")
    def stock_by_sku_list(self, request, sku=None):
        data = warehouse_service.get_stock_by_sku(sku)
        return Response(data)

    @extend_schema(
        summary="Update stock for a SKU across warehouses",
        description="Upsert stock quantity per warehouse for a single SKU. Only manual+active warehouses.",
        parameters=[OpenApiParameter(name="sku", location="path", description="Product SKU")],
        request=WarehouseStockBySkuRequest,
        responses={200: {"description": "Updated items"}, 400: {"description": "Validation error"}},
    )
    @action(detail=False, methods=["patch"], url_path="stock-by-sku/(?P<sku>[^/.]+)")
    def stock_by_sku_edit(self, request, sku=None):
        try:
            body = WarehouseStockBySkuRequest(**request.data)
        except ValidationError as exc:
            _raise_pydantic_as_drf(exc)

        try:
            items = [{"warehouse_code": item.warehouse_code, "quantity": item.quantity} for item in body.items]
            result = warehouse_service.upsert_stock_by_sku(sku, items)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return _internal_error(exc)
        return Response(result)
