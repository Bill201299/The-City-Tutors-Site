"""ct URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
import debug_toolbar
from django.contrib import admin
from django.urls import include, path

from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from tutor.forms import UserPasswordResetForm, UserPasswordResetConfirmForm


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('tutor.urls')),
    path('__debug__/', include(debug_toolbar.urls)),
    path("password_reset/", PasswordResetView.as_view(template_name="tutor/password_reset.html", email_template_name='tutor/custom_password_reset_email.txt', form_class=UserPasswordResetForm), name="password_reset"),
    path("password_reset/done/", PasswordResetDoneView.as_view(template_name="tutor/password_reset_done.html"), name="password_reset_done"),
    path("password_reset/<uidb64>/<token>/", PasswordResetConfirmView.as_view(template_name="tutor/password_reset_confirm.html", form_class=UserPasswordResetConfirmForm), name="password_reset_confirm"),
    path("password_reset/complete", PasswordResetCompleteView.as_view(template_name="tutor/password_reset_complete.html"), name="password_reset_complete"),
]
