
from django.urls import path

from apps.settlements.api.views import (
    WithdrawalListApiView,
    WithdrawalDetailApiView,
)

urlpatterns = [
    path('withdrawals/', WithdrawalListApiView.as_view(), name='withdrawal-list'),
    path('withdrawals/<int:withdrawal_id>/',
         WithdrawalDetailApiView.as_view(), name='withdrawal-detail'),
]
