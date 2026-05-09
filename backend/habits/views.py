from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Habit, HabitLog, HabitSchedule, Tag, TagCategory, UserProfile
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
    - POST /api/habits/{id}/complete/ — отметить привычку выполненной
    """

    queryset = Habit.objects.all().order_by("-created_at")
    serializer_class = HabitSerializer

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(self, request, pk=None):
        """
        Отметить привычку выполненной за сегодня.

        Если лог за сегодня уже есть — обновляем его.
        Если лога за сегодня нет — создаём новый.
        """

        habit = self.get_object()
        today = timezone.localdate()

        user = request.user

        if not user.is_authenticated:
            user = habit.user

        habit_log, created = HabitLog.objects.update_or_create(
            habit=habit,
            user=user,
            log_date=today,
            defaults={
                "status": "done",
                "value": habit.target_value,
                "duration_minutes": (
                    habit.target_value
                    if habit.target_type == "minutes"
                    else 0
                ),
            },
        )

        response_status = (
            status.HTTP_201_CREATED
            if created
            else status.HTTP_200_OK
        )

        return Response(
            {
                "message": "Habit marked as completed",
                "habit_id": habit.id,
                "habit_title": habit.title,
                "log_id": habit_log.id,
                "log_date": habit_log.log_date,
                "status": habit_log.status,
                "created": created,
            },
            status=response_status,
        )


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


class DashboardAPIView(APIView):
    """
    API для главного дашборда.

    Возвращает:
    - профиль пользователя
    - статистику по привычкам
    - список активных привычек на сегодня
    """

    def get(self, request):
        user = request.user

        if not user.is_authenticated:
            user = None

        if user is None:
            first_habit = Habit.objects.select_related("user").first()

            if first_habit is None:
                return Response(
                    {
                        "profile": None,
                        "stats": {
                            "active_habits_count": 0,
                            "completed_today_count": 0,
                            "daily_progress": 0,
                        },
                        "today_habits": [],
                    }
                )

            user = first_habit.user

        profile, _ = UserProfile.objects.get_or_create(user=user)

        today = timezone.localdate()

        active_habits = Habit.objects.filter(
            user=user,
            is_active=True,
        ).order_by("created_at")

        completed_today_habit_ids = set(
            HabitLog.objects.filter(
                user=user,
                log_date=today,
                status="done",
            ).values_list("habit_id", flat=True)
        )

        active_habits_count = active_habits.count()
        completed_today_count = len(completed_today_habit_ids)

        if active_habits_count == 0:
            daily_progress = 0
        else:
            daily_progress = round(
                completed_today_count / active_habits_count * 100
            )

        today_habits = []

        for habit in active_habits:
            today_habits.append(
                {
                    "id": habit.id,
                    "title": habit.title,
                    "description": habit.description,
                    "icon": habit.icon,
                    "color": habit.color,
                    "target_type": habit.target_type,
                    "target_value": habit.target_value,
                    "target_unit": habit.target_unit,
                    "is_completed_today": habit.id in completed_today_habit_ids,
                }
            )

        return Response(
            {
                "profile": {
                    "username": user.username,
                    "level": profile.level,
                    "xp": profile.xp,
                    "current_streak": profile.current_streak,
                    "best_streak": profile.best_streak,
                    "mascot_name": profile.mascot_name,
                    "mascot_mood": profile.mascot_mood,
                },
                "stats": {
                    "active_habits_count": active_habits_count,
                    "completed_today_count": completed_today_count,
                    "daily_progress": daily_progress,
                },
                "today_habits": today_habits,
            }
        )