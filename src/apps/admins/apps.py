from django.apps import AppConfig

class SiteAdminsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    
    name = 'apps.admins' 
    
    label = 'admins'

    def ready(self):
        pass