from django.urls import path

from apps.accounts.api.views.user_views import RegisterApiView, ProfileApiView

urlpatterns = [
    path("register/", RegisterApiView.as_view(), name="user-register"),
    path('profile/me/', ProfileApiView.as_view(), name='user-profile')
]
