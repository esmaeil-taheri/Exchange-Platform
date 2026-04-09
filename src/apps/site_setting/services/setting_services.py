import time
from apps.site_setting.models.setting import Setting

class SettingService:

    @staticmethod
    def update_settings(**data):

        setting = Setting.load()

        for key, value in data.items():
            setattr(setting, key, value)

        setting.modified_timestamp = int(time.time())

        setting.save()

        return setting
