from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DashboardAPIView,
    DashboardPageView,
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
        "dashboard/",
        DashboardAPIView.as_view(),
        name="dashboard",
    ),
    path(
        "app/",
        DashboardPageView.as_view(),
        name="dashboard-page",
    ),
]

urlpatterns += router.urls