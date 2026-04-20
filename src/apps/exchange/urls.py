from django.urls import path

from apps.exchange.api.views.price_views import GetBuySellPriceApiView, PriceCalculatorApiView
from apps.exchange.api.views.buy_sell_views import BuyApiView

urlpatterns = [
    path('buy-sell-price/', GetBuySellPriceApiView.as_view(), name='buy-sell-price'),
    path('price-calculator/', PriceCalculatorApiView.as_view(), name='price-calculator'),
    path('buy/', BuyApiView.as_view(), name='buy-sell'),
]
