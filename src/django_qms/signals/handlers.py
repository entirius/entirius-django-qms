# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Signal handlers for warehouse stock changes.

Connected in DjangoQmsConfig.ready(). Thin receivers — all logic delegated to services.
"""

import logging

from django.dispatch import receiver

from django_qms.signals.warehouse_signals import warehouse_stock_changed

logger = logging.getLogger("django_qms.signals")


@receiver(warehouse_stock_changed, dispatch_uid="qms.checkout_sync")
def on_warehouse_stock_changed_checkout(sender, warehouse, skus, **kwargs):
    """Propagate warehouse stock changes to Checkout Stock records (bulk).

    Resolves QMS Channel idx → Checkout Channel objects for propagation.
    Checkout never imports from django_qms — all data passed via kwargs.
    """
    if not warehouse.is_active:
        logger.debug("Skipping inactive warehouse %s", warehouse.code)
        return

    try:
        from django_checkout.models import Channel as CheckoutChannel
        from django_checkout.services.stock_sync_service import sync_warehouse_to_checkout
    except ImportError:
        logger.debug("django_checkout not installed, skipping stock sync")
        return

    from django_qms.models import WarehouseStock
    from django_qms.settings import QMS_SUPPLIER_CODE_PREFIX

    qty_by_sku = dict(WarehouseStock.objects.filter(warehouse=warehouse, sku__in=skus).values_list("sku", "quantity"))

    # Resolve QMS Channel idx → Checkout Channel (uses prefetch cache via .all())
    qms_channel_idxs = [ch.idx for ch in warehouse.channels.all()]
    checkout_channels = list(CheckoutChannel.objects.filter(idx__in=qms_channel_idxs))

    sync_warehouse_to_checkout(
        channels=checkout_channels,
        supplier_code=f"{QMS_SUPPLIER_CODE_PREFIX}{warehouse.code}",
        supplier_name=warehouse.name,
        skus_with_quantities=qty_by_sku,
    )


@receiver(warehouse_stock_changed, dispatch_uid="qms.matrix_enqueue")
def on_warehouse_stock_changed_matrix(sender, warehouse, skus, **kwargs):
    """Enqueue Matrix read model rebuild for affected SKUs (batched Redis pipeline)."""
    if not warehouse.is_active:
        return

    try:
        from django_pim.signals.dispatch import enqueue_product_sync
    except ImportError:
        logger.debug("django_pim not installed, skipping matrix enqueue")
        return

    channel_idxs = [ch.idx for ch in warehouse.channels.all()]
    for channel_idx in channel_idxs:
        for sku in skus:
            enqueue_product_sync(sku, channel_idx)
