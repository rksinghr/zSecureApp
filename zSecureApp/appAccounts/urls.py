# appAccounts/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-register/', views.verify_registration, name='verify-register'),
    path('login/', views.login_request, name='login'),
    path('verify-login/', views.verify_login, name='verify-login'),
    path('logout/', views.logout_view, name='logout'),
]
