
from django.urls import path

from apps.settlements.api.views import (
    WithdrawalListApiView,
    WithdrawalDetailApiView,
    CreateWithdrawalRequest
    
)

urlpatterns = [
    path('withdrawals/', WithdrawalListApiView.as_view(), name='withdrawal-list'),
    path('withdrawals/create/', CreateWithdrawalRequest.as_view(), name='create-withdrawal'),
    path('withdrawals/<int:withdrawal_id>/',
         WithdrawalDetailApiView.as_view(), name='withdrawal-detail'),
]
