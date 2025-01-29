from django.urls import path
from .views import (
    CustomLoginView, RegisterView,
    profile_view, password_reset_request,
    password_reset_confirm, logout_view
)

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('signup/', RegisterView.as_view(), name='signup'),
    path('profile/', profile_view, name='profile'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/', password_reset_request, name='password_reset'),
    path('password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
] 