# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Signal emitted after WarehouseStock records are created or updated.

Providing args:
    warehouse (Warehouse): the warehouse whose stock changed
    skus (list[str]): list of SKU codes that were modified
"""

from django.dispatch import Signal

warehouse_stock_changed = Signal()
