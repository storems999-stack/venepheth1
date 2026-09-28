"""
URL routing for the accounts app.
Core auth (login/signup/MFA/password reset) is handled by allauth at /accounts/.
This file adds custom endpoints on top.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # ── Account Overview ──────────────────────────────────────────────────────
    path("overview/", views.account_overview, name="overview"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("security/", views.security_overview, name="security"),
    path("password/change/done/", views.password_change_done, name="password_change_done"),
    # ── Logout (POST only) ────────────────────────────────────────────────────
    path("logout/", views.logout_view, name="logout"),
    # ── Post-login redirect ───────────────────────────────────────────────────
    path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
    # ── User Management (admin) ───────────────────────────────────────────────
    path("users/", views.user_list, name="user_list"),
    path("users/<uuid:pk>/", views.user_detail, name="user_detail"),
    path("users/<uuid:pk>/toggle/", views.toggle_user_active, name="toggle_user_active"),
]
