# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from celery import shared_task
from process_logger import ProcessLogger

from django_qms.enums import QMSType
from django_qms.models import XrayPointInTime

DOMAIN_NAME = QMSType.ZULU

logger = ProcessLogger(process_name="QMS_XRAY")


@shared_task(queue="quantities")
def xray_remove_old_pits(channel_idx: str) -> bool:
    logger.add_log_param("channel_idx", channel_idx)
    ids_to_delete = []
    pits_done = 0
    pits_error = 0
    pits_canceled = 0
    for pit in XrayPointInTime.objects.filter(channel__idx=channel_idx).order_by("-pit"):
        if pit.proces_status == XrayPointInTime.ProcessStatus.DONE:
            pits_done += 1
            if pits_done > 3:
                ids_to_delete.append(pit.id)
        if pit.proces_status == XrayPointInTime.ProcessStatus.CANCELED:
            pits_canceled += 1
            if pits_canceled > 1:
                ids_to_delete.append(pit.id)
        if pit.proces_status == XrayPointInTime.ProcessStatus.ERROR:
            pits_error += 1
            if pits_error > 1:
                ids_to_delete.append(pit.id)
    if len(ids_to_delete) > 0:
        logger.info(f"QMS is removing old {len(ids_to_delete)} PITs for channel={channel_idx}")
        XrayPointInTime.objects.filter(id__in=ids_to_delete).delete()
    return True
