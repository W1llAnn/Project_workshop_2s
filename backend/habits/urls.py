from rest_framework.routers import DefaultRouter

from .views import (
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

urlpatterns = router.urls