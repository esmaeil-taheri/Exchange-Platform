from django.apps import AppConfig

class SiteSettingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    
    name = 'apps.site_setting' 
    
    label = 'site_setting'

    def ready(self):
        pass