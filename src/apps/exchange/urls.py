from django.urls import path

from apps.exchange.api.views.price_views import GetBuySellPriceApiView

urlpatterns = [
    path('buy-sell-price/', GetBuySellPriceApiView.as_view(), name='buy-sell-price'),
]
