# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from django_qms.enums import QMSType

# QMS Type
QMS_TYPE = getattr(settings, "QMS_TYPE", QMSType.ZULU)

# XRay settings
QMS_XRAY_CHUNK_SIZE = int(getattr(settings, "QMS_XRAY_CHUNK_SIZE", 10000))

# Zulu settings
QMS_PIT_QUANTITY_BY_CHANNEL_CHUNK_SIZE = int(getattr(settings, "QMS_PIT_QUANTITY_BY_CHANNEL_CHUNK_SIZE", 25000))
QMS_PIT_QUANTITY_CHUNK_SIZE = int(getattr(settings, "QMS_PIT_QUANTITY_CHUNK_SIZE", 25000))
QMS_PIT_SETUP_QUANTITY_CHUNK_SIZE = int(getattr(settings, "QMS_PIT_SETUP_QUANTITY_CHUNK_SIZE", 10000))

# Warehouse settings
QMS_BULK_BATCH_SIZE: int = getattr(settings, "QMS_BULK_BATCH_SIZE", 500)
QMS_SUPPLIER_CODE_PREFIX: str = getattr(settings, "QMS_SUPPLIER_CODE_PREFIX", "wh-")
