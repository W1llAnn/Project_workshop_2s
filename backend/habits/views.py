"""HTML views for HabitHamster."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from habits.forms import HabitForm, LoginForm, RegisterForm
from habits.models import Achievement, Habit, HabitLog, UserAchievement, UserInsight
from habits.services.analytics import (
    completion_rate_for_habit,
    habit_completed_count,
    habit_heatmap,
    habit_hour_distribution,
    habit_total_minutes,
    user_activity_per_day,
    user_best_days,
    user_category_breakdown,
    user_habit_correlations,
    user_period_progress,
)
from habits.services.streak import habit_best_streak, habit_current_streak
from django.utils.http import url_has_allowed_host_and_scheme


# ---------------------------------------------------------------------------
# Auth pages.
# ---------------------------------------------------------------------------


class HHLoginView(LoginView):
    template_name = 'auth/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class HHLogoutView(LogoutView):
    next_page = reverse_lazy('landing')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Добро пожаловать в HabitHamster!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'auth/register.html', {'form': form})



# ---------------------------------------------------------------------------
# Calendar.
# ---------------------------------------------------------------------------


_CALENDAR_HOUR_RANGE = list(range(6, 24))  # 06:00 — 23:00
_WEEKDAY_LABELS = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
_RUSSIAN_MONTHS = [
    'Январь',
    'Февраль',
    'Март',
    'Апрель',
    'Май',
    'Июнь',
    'Июль',
    'Август',
    'Сентябрь',
    'Октябрь',
    'Ноябрь',
    'Декабрь',
]


def _parse_anchor_date(raw: str | None, fallback: date) -> date:
    """Parse ?date=YYYY-MM-DD into a real date, falling back to today."""
    if not raw:
        return fallback
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return fallback


def _week_bounds(anchor: date) -> tuple[date, date]:
    """Return (Monday, Sunday) of the ISO week that contains ``anchor``."""
    monday = anchor - timedelta(days=anchor.isoweekday() - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _month_grid_bounds(anchor: date) -> tuple[date, date]:
    """Return the (first_visible_monday, last_visible_sunday) for a 6x7 grid."""
    first_of_month = anchor.replace(day=1)
    pad_days = first_of_month.isoweekday() - 1
    grid_start = first_of_month - timedelta(days=pad_days)
    grid_end = grid_start + timedelta(days=6 * 7 - 1)
    return grid_start, grid_end


@login_required
def calendar_view(request):
    """Calendar page — day / week / month views with habit pills in a time grid.

    Driven by query parameters:
      * ``view``  — ``week`` (default) | ``day`` | ``month``
      * ``date``  — ``YYYY-MM-DD`` anchor inside the period to render
    """
    today = timezone.localdate()
    anchor = _parse_anchor_date(request.GET.get('date'), today)
    view_mode = request.GET.get('view', 'week')
    if view_mode not in {'day', 'week', 'month'}:
        view_mode = 'week'

    habits = list(
        Habit.objects.filter(user=request.user, is_active=True).select_related('schedule').prefetch_related('tags')
    )

    # Period bounds + previous / next anchors for the toolbar.
    if view_mode == 'day':
        period_start = period_end = anchor
        prev_anchor = anchor - timedelta(days=1)
        next_anchor = anchor + timedelta(days=1)
    elif view_mode == 'month':
        period_start, period_end = _month_grid_bounds(anchor)
        first_of_month = anchor.replace(day=1)
        # Step a month back / forward by sticking close to the 1st-of-month.
        prev_anchor = (first_of_month - timedelta(days=1)).replace(day=1)
        last_of_month = first_of_month.replace(day=28) + timedelta(days=4)
        last_of_month = last_of_month - timedelta(days=last_of_month.day)
        next_anchor = last_of_month + timedelta(days=1)
    else:  # week
        period_start, period_end = _week_bounds(anchor)
        prev_anchor = period_start - timedelta(days=7)
        next_anchor = period_start + timedelta(days=7)

    # Pull all logs for the visible period in a single query.
    period_logs = HabitLog.objects.filter(
        user=request.user,
        log_date__gte=period_start,
        log_date__lte=period_end,
    )
    log_lookup: dict[tuple[int, date], HabitLog] = {(log.habit_id, log.log_date): log for log in period_logs}

    def _pill_for(habit: Habit, day: date) -> dict | None:
        schedule = getattr(habit, 'schedule', None)
        if schedule and not schedule.is_due_on(day):
            return None
        log = log_lookup.get((habit.id, day))
        slot_time = None
        if schedule:
            slot_time = schedule.window_start or schedule.reminder_time
        # Both 'done' and 'partial' count as a completed pill so the calendar
        # matches the dashboard's "сегодня X / Y" counters. A 'partial' log
        # still represents progress toward the habit and should not look like
        # an unchecked slot.
        is_done = bool(log and log.status in {'done', 'partial'})
        return {
            'habit': habit,
            'time': slot_time,
            'is_done': is_done,
            'is_planned': not is_done,
            'log': log,
        }

    # --- Day / Week shared structure: time-grid columns. -------------------
    grid_days: list[dict] = []
    if view_mode in {'day', 'week'}:
        col_count = 1 if view_mode == 'day' else 7
        for offset in range(col_count):
            day = period_start + timedelta(days=offset)
            slots: dict[int, list[dict]] = {h: [] for h in _CALENDAR_HOUR_RANGE}
            untimed: list[dict] = []
            day_done = 0
            day_total = 0
            for habit in habits:
                pill = _pill_for(habit, day)
                if pill is None:
                    continue
                day_total += 1
                if pill['is_done']:
                    day_done += 1
                if pill['time'] is None:
                    untimed.append(pill)
                else:
                    hour = pill['time'].hour
                    if hour < _CALENDAR_HOUR_RANGE[0]:
                        slots[_CALENDAR_HOUR_RANGE[0]].append(pill)
                    elif hour > _CALENDAR_HOUR_RANGE[-1]:
                        slots[_CALENDAR_HOUR_RANGE[-1]].append(pill)
                    else:
                        slots[hour].append(pill)
            grid_days.append(
                {
                    'date': day,
                    'weekday_label': _WEEKDAY_LABELS[day.isoweekday() - 1],
                    'is_today': day == today,
                    'is_weekend': day.isoweekday() >= 6,
                    'slots': [{'hour': h, 'pills': slots[h]} for h in _CALENDAR_HOUR_RANGE],
                    'untimed': untimed,
                    'day_done': day_done,
                    'day_total': day_total,
                }
            )

    # --- Month grid: 6 rows of 7 days, each cell shows up to 3 habit pills.
    month_cells: list[dict] = []
    if view_mode == 'month':
        cursor = period_start
        while cursor <= period_end:
            cell_pills: list[dict] = []
            for habit in habits:
                pill = _pill_for(habit, cursor)
                if pill is None:
                    continue
                cell_pills.append(pill)
            month_cells.append(
                {
                    'date': cursor,
                    'in_month': cursor.month == anchor.month,
                    'is_today': cursor == today,
                    'pills': cell_pills[:3],
                    'extra_count': max(len(cell_pills) - 3, 0),
                }
            )
            cursor += timedelta(days=1)

    # Weekly progress card on the banner. The denominator is the number of
    # (active habit × due day) pairs in the current ISO week — see the
    # docstring of ``user_period_progress`` for why we don't divide by the
    # raw log count.
    week_start, week_end = _week_bounds(today)
    week_progress = user_period_progress(request.user, week_start, week_end)
    weekly_completion_rate = week_progress['rate']
    wt_done = week_progress['done']
    wt_total_real = week_progress['expected']

    # Display title ("Ноябрь 2023" / a date / a week range).
    if view_mode == 'day':
        period_title = f'{anchor.day} {_RUSSIAN_MONTHS[anchor.month - 1]} {anchor.year}'
    elif view_mode == 'month':
        period_title = f'{_RUSSIAN_MONTHS[anchor.month - 1]} {anchor.year}'
    else:
        if period_start.month == period_end.month:
            period_title = (
                f'{period_start.day}–{period_end.day} ' f'{_RUSSIAN_MONTHS[period_start.month - 1]} {period_start.year}'
            )
        else:
            period_title = (
                f'{period_start.day} {_RUSSIAN_MONTHS[period_start.month - 1]} – '
                f'{period_end.day} {_RUSSIAN_MONTHS[period_end.month - 1]} {period_start.year}'
            )

    context = {
        'today': today,
        'anchor': anchor,
        'view_mode': view_mode,
        'period_title': period_title,
        'prev_anchor': prev_anchor.isoformat(),
        'next_anchor': next_anchor.isoformat(),
        'today_anchor': today.isoformat(),
        'grid_days': grid_days,
        'hours': _CALENDAR_HOUR_RANGE,
        'month_cells': month_cells,
        'weekday_labels': _WEEKDAY_LABELS,
        'weekly_completion_rate': weekly_completion_rate,
        'wt_done': wt_done,
        'wt_total_real': wt_total_real,
        'add_form': HabitForm(),
    }
    return render(request, 'calendar.html', context)