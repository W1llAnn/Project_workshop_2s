from django.urls import path
from rest_framework.routers import DefaultRouter

from .auth_views import login_page, logout_page, register_page
from .views import (
    DashboardAPIView,
    DashboardPageView,
    HabitDetailPageView,
    HabitLogViewSet,
    HabitScheduleViewSet,
    HabitViewSet,
    TagCategoryViewSet,
    TagViewSet,
)

router = DefaultRouter()

router.register(
    r"habits",
    HabitViewSet,
    basename="habit",
)

router.register(
    r"habit-logs",
    HabitLogViewSet,
    basename="habit-log",
)

router.register(
    r"habit-schedules",
    HabitScheduleViewSet,
    basename="habit-schedule",
)

router.register(
    r"tag-categories",
    TagCategoryViewSet,
    basename="tag-category",
)

router.register(
    r"tags",
    TagViewSet,
    basename="tag",
)

urlpatterns = [
    path(
        "register/",
        register_page,
        name="register-page",
    ),
    path(
        "login/",
        login_page,
        name="login-page",
    ),
    path(
        "logout/",
        logout_page,
        name="logout-page",
    ),
    path(
        "dashboard/",
        DashboardAPIView.as_view(),
        name="dashboard",
    ),
    path(
        "app/",
        DashboardPageView.as_view(),
        name="dashboard-page",
    ),
    path(
        "app/habits/<int:pk>/",
        HabitDetailPageView.as_view(),
        name="habit-detail-page",
    ),
]

urlpatterns += router.urls