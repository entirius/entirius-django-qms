# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


import celery
from django.utils import timezone
from process_logger import ProcessLogger

from django_qms.enums import QMSType
from django_qms.models import Channel, XrayPointInTime

# Submodule imports (not the package) — the package __init__ imports this module
# before those names exist, so package-level imports here are a circular import.
from django_qms.tasks.xray.linked_storages import xray_linked_storages
from django_qms.tasks.xray.pull_data import xray_pull_data
from django_qms.tasks.xray.push_data import xray_push_data
from django_qms.tasks.xray.remove_old_pits import xray_remove_old_pits

logger = ProcessLogger(process_name="QMS_XRAY")


def xray_manage_quantities(channel_idx: str | None = None) -> bool:
    channels = Channel.objects.filter(qms_type=QMSType.XRAY)
    if channel_idx:
        channels = channels.filter(idx=channel_idx)

    for channel in channels:
        logger.add_log_param("channel_idx", channel.idx)
        already_running_pits = XrayPointInTime.objects.already_running(channel=channel)
        if len(already_running_pits) > 0:
            for already_running_pit in already_running_pits:
                logger.add_log_param("pit", already_running_pit.pit)
                logger.warning(
                    f"Can not start new Manage Quantities process for channel={channel.idx}, "
                    f"pit='{already_running_pit.pit}' is already processing"
                )
            continue

        waiting_pits = XrayPointInTime.objects.waiting(channel=channel)
        if len(waiting_pits) > 0:
            for waiting_pit in waiting_pits:
                logger.add_log_param("pit", waiting_pit.pit)
                logger.warning(
                    f"Can not start new Manage Quantities process for channel={channel.idx},  "
                    f"pit='{waiting_pit.pit}' is already waiting"
                )
            continue

        pit: XrayPointInTime = XrayPointInTime.objects.create(pit=timezone.now(), channel=channel)
        try:
            process_chain = celery.chain(
                xray_pull_data.si(channel_idx=channel.idx, pit_id=pit.pk),
                xray_linked_storages.si(channel_idx=channel.idx, pit_id=pit.pk),
                xray_push_data.si(channel_idx=channel.idx, pit_id=pit.pk),
                xray_remove_old_pits.si(channel_idx=channel.idx),
            )
            process_chain.delay()
        except Exception as e:
            logger.exception(e)
            pit.set_as_error()

    return True
