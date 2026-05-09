from rest_framework import viewsets

from .models import Habit, HabitLog
from .serializers import HabitLogSerializer, HabitSerializer


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