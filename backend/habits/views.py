from rest_framework import viewsets

from .models import Habit, HabitLog, HabitSchedule, Tag, TagCategory
from .serializers import (
    HabitLogSerializer,
    HabitScheduleSerializer,
    HabitSerializer,
    TagCategorySerializer,
    TagSerializer,
)


class HabitViewSet(viewsets.ModelViewSet):
    """
    API для привычек.

    Что умеет:
    - GET /api/habits/ — получить список привычек
    - POST /api/habits/ — создать привычку
    - GET /api/habits/{id}/ — получить одну привычку
    - PATCH /api/habits/{id}/ — частично обновить привычку
    - DELETE /api/habits/{id}/ — удалить привычку
    """

    queryset = Habit.objects.all().order_by("-created_at")
    serializer_class = HabitSerializer


class HabitLogViewSet(viewsets.ModelViewSet):
    """
    API для логов выполнения привычек.

    Что умеет:
    - GET /api/habit-logs/ — получить список логов
    - POST /api/habit-logs/ — создать лог выполнения
    - GET /api/habit-logs/{id}/ — получить один лог
    - PATCH /api/habit-logs/{id}/ — обновить лог
    - DELETE /api/habit-logs/{id}/ — удалить лог
    """

    queryset = HabitLog.objects.all().order_by("-log_date", "-created_at")
    serializer_class = HabitLogSerializer

class HabitScheduleViewSet(viewsets.ModelViewSet):
    """
    API для расписаний привычек.

    Например:
    - ежедневно
    - еженедельно
    - по конкретным дням недели
    """

    queryset = HabitSchedule.objects.all()
    serializer_class = HabitScheduleSerializer


class TagCategoryViewSet(viewsets.ModelViewSet):
    """
    API для категорий тегов.

    Например:
    - Здоровье
    - Осознанность
    - Продуктивность
    """

    queryset = TagCategory.objects.all().order_by("name")
    serializer_class = TagCategorySerializer


class TagViewSet(viewsets.ModelViewSet):
    """
    API для тегов привычек.

    Например:
    - Фитнес
    - Сон
    - Медитация
    """

    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer