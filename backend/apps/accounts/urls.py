from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("csrf/", views.csrf, name="auth-csrf"),
    path("login/", views.login_view, name="auth-login"),
    path("logout/", views.logout_view, name="auth-logout"),
    path("me/", views.me_view, name="auth-me"),
    path("admin-stub/", views.AdminOnlyStubView.as_view(), name="auth-admin-stub"),
]
