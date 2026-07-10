from django_qms.admin.channel import ChannelAdmin

# Warehouse admin
from django_qms.admin.warehouse import WarehouseAdmin  # noqa: F401
from django_qms.admin.xray.pit import XrayPointInTimeAdmin
from django_qms.admin.xray.product_representation import XrayProductRepresentationAdmin
from django_qms.admin.xray.quantity_by_storage import XrayQuantityByStorageAdmin
from django_qms.admin.xray.storage import XrayStorageAdmin
from django_qms.admin.xray.storage_link import XrayStorageLinkAdmin
from django_qms.admin.zulu.pit import ZuluPointInTimeAdmin
from django_qms.admin.zulu.pit_quantity import ZuluPitQuantityAdmin
from django_qms.admin.zulu.pit_quantity_by_channel import ZuluPitQuantityByChannelAdmin
from django_qms.admin.zulu.pit_setup_quantity import ZuluPitSetupQuantityAdmin
from django_qms.admin.zulu.product_representation import ZuluProductRepresentationAdmin
from django_qms.admin.zulu.storage import ZuluStorageAdmin
