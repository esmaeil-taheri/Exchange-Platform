from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Prometheus
    path("", include("django_prometheus.urls")),

    # Spectacular
    path('api/schema', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Accounts
    path('api/v1/authentication/', include('apps.accounts.urls')),

    # Notifications
    path('api/v1/notifications/', include('apps.notifications.urls')),

    # Customers
    path('api/v1/customers/', include('apps.customers.urls')),

    # Exchange
    path('api/v1/exchange/', include('apps.exchange.urls')),

    # Payments
    path('api/v1/payments/', include('apps.payments.urls')),

    # Settlements
    path('api/v1/settlements/', include('apps.settlements.urls')),
]
