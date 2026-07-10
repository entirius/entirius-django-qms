# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.domains.domain import Domain

from django_qms.models import Channel, XrayStorage


class DomainQms(Domain):
    class Scope:
        GLOBAL = "global"

    channel: Channel

    def set_channel(self, channel: Channel) -> None:
        self.channel = channel

    def get_csv_path(self, scope: str = Scope.GLOBAL):
        storage = XrayStorage.objects.get(
            channel=self.channel,
            storage_manager=XrayStorage.StorageManagerEnum.CSV,
            data_direction=XrayStorage.DataDirection.STORAGE_INPUT,
            additional_data__scope=scope,
        )
        return storage.additional_data.get("csv_path")
