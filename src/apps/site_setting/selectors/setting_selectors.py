from django.core.cache import cache
from apps.site_setting.models import SiteSetting

CACHE_KEY = "site_settings"


def get_site_settings():
    settings = cache.get(CACHE_KEY)

    if settings is None:
        settings = SiteSetting.load()
        cache.set(CACHE_KEY, settings, 60 * 5)

    return settings