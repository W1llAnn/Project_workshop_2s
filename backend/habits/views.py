import calendar
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date
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


def get_month_name(month):
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


def get_weekday_name(weekday_number):
    names = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }

    return names.get(weekday_number, "")


def update_profile_after_completion(user, log_date):
    profile, _ = UserProfile.objects.get_or_create(user=user)

    profile.xp += 10

    active_habits_count = Habit.objects.filter(
        user=user,
        is_active=True,
    ).count()

    completed_count = HabitLog.objects.filter(
        user=user,
        log_date=log_date,
        status="done",
        habit__is_active=True,
    ).values("habit_id").distinct().count()

    is_perfect_day = (
        active_habits_count > 0
        and completed_count == active_habits_count
    )

    if is_perfect_day:
        profile.xp += 30

        if log_date == timezone.localdate():
            profile.current_streak += 1
            profile.best_streak = max(
                profile.best_streak,
                profile.current_streak,
            )

    profile.level = max(1, profile.xp // 100 + 1)

    if is_perfect_day:
        profile.mascot_mood = "happy"
    elif completed_count > 0:
        profile.mascot_mood = "neutral"
    else:
        profile.mascot_mood = "sad"

    profile.save()

    return profile


class DashboardPageView(LoginRequiredMixin, TemplateView):
    template_name = "habits/dashboard.html"
    login_url = "/api/login/"


class HabitDetailPageView(LoginRequiredMixin, TemplateView):
    template_name = "habits/habit_detail.html"
    login_url = "/api/login/"


class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Habit.objects.filter(
            user=self.request.user,
        ).order_by("-created_at")

        is_active = self.request.query_params.get("is_active")

        if is_active in ["true", "1"]:
            queryset = queryset.filter(is_active=True)

        if is_active in ["false", "0"]:
            queryset = queryset.filter(is_active=False)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(self, request, pk=None):
        habit = self.get_object()

        date_value = (
            request.query_params.get("date")
            or request.data.get("date")
        )

        if date_value:
            log_date = parse_date(date_value)

            if log_date is None:
                return Response(
                    {
                        "detail": "Некорректная дата. Используй формат YYYY-MM-DD."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            log_date = timezone.localdate()

        if log_date > timezone.localdate():
            return Response(
                {
                    "detail": "Нельзя отметить привычку за будущую дату."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_log = HabitLog.objects.filter(
            habit=habit,
            user=request.user,
            log_date=log_date,
        ).first()

        was_done = existing_log is not None and existing_log.status == "done"

        habit_log, created = HabitLog.objects.update_or_create(
            habit=habit,
            user=request.user,
            log_date=log_date,
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

        profile = None

        if not was_done:
            profile = update_profile_after_completion(
                user=request.user,
                log_date=log_date,
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
                "xp": profile.xp if profile else None,
                "level": profile.level if profile else None,
            },
            status=response_status,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        habit = self.get_object()
        habit.is_active = True
        habit.save(update_fields=["is_active", "updated_at"])

        return Response(
            {
                "message": "Habit restored",
                "habit_id": habit.id,
                "is_active": habit.is_active,
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="stats",
    )
    def stats(self, request, pk=None):
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
    serializer_class = HabitLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HabitLog.objects.filter(
            user=self.request.user,
        ).order_by("-log_date", "-created_at")

    def perform_create(self, serializer):
        habit = serializer.validated_data.get("habit")

        if habit.user != self.request.user:
            raise PermissionError("Нельзя создать лог для чужой привычки.")

        serializer.save(user=self.request.user)


class HabitScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = HabitScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HabitSchedule.objects.filter(
            habit__user=self.request.user,
        )


class TagCategoryViewSet(viewsets.ModelViewSet):
    queryset = TagCategory.objects.all().order_by("name")
    serializer_class = TagCategorySerializer
    permission_classes = [IsAuthenticated]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


class DashboardAPIView(APIView):
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

        archived_habits_count = Habit.objects.filter(
            user=user,
            is_active=False,
        ).count()

        return Response(
            {
                "profile": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "date_joined": user.date_joined.date(),
                    "level": profile.level,
                    "xp": profile.xp,
                    "current_streak": profile.current_streak,
                    "best_streak": profile.best_streak,
                    "mascot_name": profile.mascot_name,
                    "mascot_mood": profile.mascot_mood,
                },
                "stats": {
                    "active_habits_count": active_habits_count,
                    "archived_habits_count": archived_habits_count,
                    "completed_today_count": completed_today_count,
                    "daily_progress": daily_progress,
                },
                "today_habits": today_habits,
            }
        )


class CalendarAPIView(APIView):
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
                    "detail": "Некорректный год или месяц."
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
                "month_name": get_month_name(month),
                "days_in_month": days_in_month,
                "active_habits_count": active_habits_count,
                "days": days,
            }
        )


class AnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()

        active_habits = Habit.objects.filter(
            user=user,
            is_active=True,
        )

        total_habits = active_habits.count()

        completed_today = HabitLog.objects.filter(
            user=user,
            log_date=today,
            status="done",
            habit__is_active=True,
        ).values("habit_id").distinct().count()

        if total_habits == 0:
            today_progress = 0
        else:
            today_progress = round(completed_today / total_habits * 100)

        week_start = today - timedelta(days=6)
        month_start = today.replace(day=1)

        week_days = []
        perfect_days = 0
        total_week_progress = 0

        for offset in range(7):
            current_date = week_start + timedelta(days=offset)

            completed_count = HabitLog.objects.filter(
                user=user,
                log_date=current_date,
                status="done",
                habit__is_active=True,
            ).values("habit_id").distinct().count()

            if total_habits == 0:
                progress = 0
            else:
                progress = round(completed_count / total_habits * 100)

            if progress == 100 and total_habits > 0:
                perfect_days += 1

            total_week_progress += progress

            week_days.append(
                {
                    "date": current_date.isoformat(),
                    "weekday": get_weekday_name(current_date.weekday()),
                    "completed_count": completed_count,
                    "progress": progress,
                }
            )

        week_progress = round(total_week_progress / 7)

        month_logs = HabitLog.objects.filter(
            user=user,
            log_date__gte=month_start,
            log_date__lte=today,
            status="done",
            habit__is_active=True,
        )

        days_passed = today.day

        if total_habits == 0:
            month_progress = 0
        else:
            month_progress = round(
                month_logs.values("habit_id", "log_date").distinct().count()
                / (total_habits * days_passed)
                * 100
            )

        habit_counts = (
            HabitLog.objects.filter(
                user=user,
                status="done",
                habit__is_active=True,
            )
            .values("habit_id", "habit__title")
            .annotate(done_count=Count("id"))
            .order_by("-done_count")
        )

        best_habit = habit_counts.first()
        weakest_habit = habit_counts.last()

        weekday_counts = {}

        for log in month_logs:
            weekday = log.log_date.weekday()
            weekday_counts[weekday] = weekday_counts.get(weekday, 0) + 1

        if weekday_counts:
            best_weekday_number = max(
                weekday_counts,
                key=weekday_counts.get,
            )
            best_weekday = get_weekday_name(best_weekday_number)
        else:
            best_weekday = None

        profile, _ = UserProfile.objects.get_or_create(user=user)

        return Response(
            {
                "total_habits": total_habits,
                "completed_today": completed_today,
                "today_progress": today_progress,
                "week_progress": week_progress,
                "month_progress": month_progress,
                "perfect_days_last_7": perfect_days,
                "best_habit": {
                    "id": best_habit["habit_id"],
                    "title": best_habit["habit__title"],
                    "done_count": best_habit["done_count"],
                } if best_habit else None,
                "weakest_habit": {
                    "id": weakest_habit["habit_id"],
                    "title": weakest_habit["habit__title"],
                    "done_count": weakest_habit["done_count"],
                } if weakest_habit else None,
                "best_weekday": best_weekday,
                "week_days": week_days,
                "profile": {
                    "level": profile.level,
                    "xp": profile.xp,
                    "current_streak": profile.current_streak,
                    "best_streak": profile.best_streak,
                    "mascot_mood": profile.mascot_mood,
                },
            }
        )