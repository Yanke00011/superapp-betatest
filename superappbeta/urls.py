"""
URL configuration for superappbeta project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import (
    CustomLoginView, SignUpView, profile_view, 
    password_reset_request, home_view,
    password_reset_confirm, logout_view,
    WelcomeView, bad_request, permission_denied, page_not_found, server_error
)
from django.contrib.auth.decorators import login_required
from django.conf.urls import handler400, handler403, handler404, handler500

urlpatterns = [
    path('', WelcomeView.as_view(), name='welcome'),
    path('home/', login_required(home_view), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/login/', CustomLoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('accounts/logout/', logout_view, name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),
    path('accounts/profile/', profile_view, name='profile'),
    path('accounts/password-reset-request/', password_reset_request, name='password_reset_request'),
    path('accounts/password-reset-confirm/', password_reset_confirm, name='password_reset_confirm'),
    path('files/', include('files.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = 'accounts.views.bad_request'
handler403 = 'accounts.views.permission_denied'
handler404 = 'accounts.views.page_not_found'
handler500 = 'accounts.views.server_error'
