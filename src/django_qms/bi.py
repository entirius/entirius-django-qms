# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from bievents import BiCeleryTaskEventAbstract
from django.conf import settings

BI_SOURCE = "django-qms"
BI_ENVIRONMENT = settings.BI_ENVIRONMENT
BI_BUSINESS_UNIT = settings.BI_BUSINESS_UNIT


class EventAbstract(BiCeleryTaskEventAbstract):
    details_type = "Event Abstract"
    version = 3

    def __init__(self, **kwargs):
        kwargs["source"] = BI_SOURCE
        kwargs["environment"] = BI_ENVIRONMENT
        kwargs["business_unit"] = BI_BUSINESS_UNIT
        super().__init__(**kwargs)


class QM_ProcessChainIsStartingEvent(EventAbstract):
    details_type = "QMS Process Chain Is Starting"
    version = 1

    def __init__(self, pit, **kwargs):
        self.details = {"pit": pit}
        super().__init__(**kwargs)


class QM_ProcessChainIsDoneEvent(EventAbstract):
    details_type = "QMS Process Chain Is Done"
    version = 1

    def __init__(self, pit, **kwargs):
        self.details = {"pit": pit}
        super().__init__(**kwargs)


class QM_ManageQuantitiesStartEvent(EventAbstract):
    details_type = "QMS Manage Quantities"
    version = 1

    def __init__(self, pit, **kwargs):
        self.details = {"pit": pit}
        super().__init__(**kwargs)


class QM_GatherQuantityDataEvent(EventAbstract):
    details_type = "QMS Gather Quantity from Channel"
    version = 1

    def __init__(self, pit, channel_idx, **kwargs):
        self.details = {"pit": pit, "channel_idx": channel_idx}
        super().__init__(**kwargs)


class QM_CreatePitQuantityEvent(EventAbstract):
    details_type = "QMS Create PIT Quantity"
    version = 1

    def __init__(self, pit, **kwargs):
        self.details = {"pit": pit}
        super().__init__(**kwargs)


class QM_SplitAndSetupEvent(EventAbstract):
    details_type = "QMS Split and Setup"
    version = 1

    def __init__(self, pit, **kwargs):
        self.details = {"pit": pit}
        super().__init__(**kwargs)


class QM_PushDataEvent(EventAbstract):
    details_type = "QMS Push to Storage"
    version = 1

    def __init__(self, pit, channel_idx, **kwargs):
        self.details = {"pit": pit, "channel_idx": channel_idx}
        super().__init__(**kwargs)
