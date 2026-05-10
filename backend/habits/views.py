import calendar
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
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


class DashboardPageView(LoginRequiredMixin, TemplateView):
    """
    Frontend-страница главного приложения.

    Если пользователь не вошёл, Django отправит его на:
    /api/login/
    """

    template_name = "habits/dashboard.html"
    login_url = "/api/login/"


class HabitDetailPageView(LoginRequiredMixin, TemplateView):
    """
    Отдельная frontend-страница детальной информации о привычке.

    Сейчас основной detail-экран уже есть внутри /api/app/,
    но эту страницу оставляем как дополнительный прямой URL:
    /api/app/habits/<id>/
    """

    template_name = "habits/habit_detail.html"
    login_url = "/api/login/"


class HabitViewSet(viewsets.ModelViewSet):
    """
    API для привычек текущего пользователя.

    Пользователь видит и изменяет только свои привычки.
    """

    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Возвращаем только привычки текущего авторизованного пользователя.
        """

        return Habit.objects.filter(
            user=self.request.user,
        ).order_by("-created_at")

    def perform_create(self, serializer):
        """
        При создании привычки автоматически привязываем её
        к текущему авторизованному пользователю.

        Даже если frontend случайно передаст другой user_id,
        backend всё равно поставит request.user.
        """

        serializer.save(user=self.request.user)

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

        habit_log, created = HabitLog.objects.update_or_create(
            habit=habit,
            user=request.user,
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

    @action(
        detail=True,
        methods=["get"],
        url_path="stats",
    )
    def stats(self, request, pk=None):
        """
        Получить статистику по конкретной привычке текущего пользователя.
        """

        habit = self.get_object()

        logs = HabitLog.objects.filter(
            habit=habit,
            user=request.user,
        ).order_by("-log_date", "-created_at")

        total_logs = logs.count()
        completed_count = logs.filter(status="done").count()
        missed_count = logs.filter(status="missed").count()
        partial_count = logs.filter(status="partial").count()
        skipped_count = logs.filter(status="skipped").count()

        if total_logs == 0:
            completion_rate = 0
        else:
            completion_rate = round(completed_count / total_logs * 100)

        total_duration_minutes = sum(
            log.duration_minutes for log in logs
        )

        recent_logs = []

        for log in logs[:10]:
            recent_logs.append(
                {
                    "id": log.id,
                    "log_date": log.log_date,
                    "status": log.status,
                    "value": log.value,
                    "duration_minutes": log.duration_minutes,
                    "note": log.note,
                    "mood_score": log.mood_score,
                }
            )

        return Response(
            {
                "habit": {
                    "id": habit.id,
                    "title": habit.title,
                    "description": habit.description,
                    "target_type": habit.target_type,
                    "target_value": habit.target_value,
                    "target_unit": habit.target_unit,
                    "icon": habit.icon,
                    "color": habit.color,
                    "is_active": habit.is_active,
                },
                "stats": {
                    "total_logs": total_logs,
                    "completed_count": completed_count,
                    "missed_count": missed_count,
                    "partial_count": partial_count,
                    "skipped_count": skipped_count,
                    "completion_rate": completion_rate,
                    "total_duration_minutes": total_duration_minutes,
                },
                "recent_logs": recent_logs,
            }
        )


class HabitLogViewSet(viewsets.ModelViewSet):
    """
    API для логов выполнения привычек текущего пользователя.
    """

    serializer_class = HabitLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HabitLog.objects.filter(
            user=self.request.user,
        ).order_by("-log_date", "-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HabitScheduleViewSet(viewsets.ModelViewSet):
    """
    API для расписаний привычек текущего пользователя.
    """

    serializer_class = HabitScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HabitSchedule.objects.filter(
            habit__user=self.request.user,
        )


class TagCategoryViewSet(viewsets.ModelViewSet):
    """
    API для категорий тегов.

    Пока категории тегов общие для всех пользователей.
    """

    queryset = TagCategory.objects.all().order_by("name")
    serializer_class = TagCategorySerializer
    permission_classes = [IsAuthenticated]


class TagViewSet(viewsets.ModelViewSet):
    """
    API для тегов.

    Пока теги общие для всех пользователей.
    """

    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


class DashboardAPIView(APIView):
    """
    API для главного дашборда текущего пользователя.

    Возвращает:
    - профиль текущего пользователя
    - статистику по его привычкам
    - список его активных привычек на сегодня
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

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
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
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


class CalendarAPIView(APIView):
    """
    API календаря привычек текущего пользователя.

    Endpoint:
    GET /api/calendar/

    Дополнительно можно передать:
    /api/calendar/?year=2026&month=5

    Возвращает:
    - год
    - месяц
    - название месяца
    - дни месяца
    - прогресс по каждому дню
    - привычки и их статус за каждый день
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()

        year = request.query_params.get("year")
        month = request.query_params.get("month")

        try:
            year = int(year) if year else today.year
            month = int(month) if month else today.month

            if month < 1 or month > 12:
                raise ValueError
        except ValueError:
            return Response(
                {
                    "detail": "Некорректный год или месяц.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, days_in_month = calendar.monthrange(year, month)

        active_habits = Habit.objects.filter(
            user=user,
            is_active=True,
        ).order_by("created_at")

        active_habits_count = active_habits.count()

        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)

        logs = HabitLog.objects.filter(
            user=user,
            log_date__gte=month_start,
            log_date__lte=month_end,
        ).select_related("habit")

        logs_by_date = {}

        for log in logs:
            logs_by_date.setdefault(log.log_date, []).append(log)

        days = []

        for day_number in range(1, days_in_month + 1):
            current_date = date(year, month, day_number)
            day_logs = logs_by_date.get(current_date, [])

            completed_habit_ids = {
                log.habit_id
                for log in day_logs
                if log.status == "done"
            }

            completed_count = len(completed_habit_ids)

            if active_habits_count == 0:
                progress = 0
            else:
                progress = round(
                    completed_count / active_habits_count * 100
                )

            habits_for_day = []

            for habit in active_habits:
                habit_log = None

                for log in day_logs:
                    if log.habit_id == habit.id:
                        habit_log = log
                        break

                if habit_log is None:
                    habit_status = "not_done"
                    log_id = None
                    value = 0
                    duration_minutes = 0
                else:
                    habit_status = habit_log.status
                    log_id = habit_log.id
                    value = habit_log.value
                    duration_minutes = habit_log.duration_minutes

                habits_for_day.append(
                    {
                        "id": habit.id,
                        "title": habit.title,
                        "icon": habit.icon,
                        "color": habit.color,
                        "status": habit_status,
                        "log_id": log_id,
                        "value": value,
                        "duration_minutes": duration_minutes,
                    }
                )

            if progress == 100 and active_habits_count > 0:
                day_state = "perfect"
            elif progress > 0:
                day_state = "partial"
            elif current_date > today:
                day_state = "future"
            else:
                day_state = "empty"

            days.append(
                {
                    "date": current_date.isoformat(),
                    "day": day_number,
                    "is_today": current_date == today,
                    "is_future": current_date > today,
                    "completed_count": completed_count,
                    "total_count": active_habits_count,
                    "progress": progress,
                    "state": day_state,
                    "habits": habits_for_day,
                }
            )

        return Response(
            {
                "year": year,
                "month": month,
                "month_name": self.get_month_name(month),
                "days_in_month": days_in_month,
                "active_habits_count": active_habits_count,
                "days": days,
            }
        )

    def get_month_name(self, month):
        month_names = {
            1: "Январь",
            2: "Февраль",
            3: "Март",
            4: "Апрель",
            5: "Май",
            6: "Июнь",
            7: "Июль",
            8: "Август",
            9: "Сентябрь",
            10: "Октябрь",
            11: "Ноябрь",
            12: "Декабрь",
        }

        return month_names.get(month, "")