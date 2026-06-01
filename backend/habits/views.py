"""HTML views for HabitHamster."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from habits.forms import HabitForm, LoginForm, RegisterForm
from habits.models import (
    Achievement,
    Habit,
    HabitLog,
    HabitSchedule,
    Notification,
    Tag,
    UserAchievement,
    UserInsight,
    UserProfile,
)
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


ONBOARDING_QUESTIONS = [
    {
        'name': 'goal',
        'title': 'Какая ваша цель?',
        'is_multi_select': True,
        'options': [
            ('goal_health', 'Улучшить здоровье', {'health': 0.8, 'fitness': 0.6}),
            ('goal_prod', 'Повысить продуктивность', {'productivity': 1.0}),
            ('goal_sleep', 'Улучшить сон', {'sleep': 1.0}),
            ('goal_mind', 'Снизить стресс', {'mindfulness': 1.0}),
            ('goal_disc', 'Развить дисциплину', {'self_development': 1.0}),
            ('goal_learn', 'Учиться новому', {'learning': 1.0}),
        ],
    },
    {
        'name': 'sport_freq',
        'title': 'Как часто вы занимаетесь спортом?',
        'is_multi_select': False,
        'options': [
            ('sport_0', 'Никогда', {'fitness': 0.2}),
            ('sport_1_2', '1–2 раза в неделю', {'fitness': 0.4}),
            ('sport_3_5', '3–5 раз в неделю', {'fitness': 0.7}),
            ('sport_7', 'Каждый день', {'fitness': 1.0}),
        ],
    },
    {
        'name': 'hard_to_do',
        'title': 'Что вам сложнее всего делать регулярно?',
        'is_multi_select': True,
        'options': [
            ('hard_wake', 'Просыпаться вовремя', {'sleep': 0.8}),
            ('hard_focus', 'Концентрироваться', {'productivity': 0.8}),
            ('hard_train', 'Тренироваться', {'fitness': 0.8}),
            ('hard_water', 'Пить воду', {'health': 0.8}),
            ('hard_read', 'Читать', {'learning': 0.8}),
            ('hard_rest', 'Отдыхать', {'mindfulness': 0.8}),
        ],
    },
    {
        'name': 'free_time',
        'title': 'Сколько свободного времени в день вы готовы уделять привычкам?',
        'is_multi_select': False,
        'options': [
            ('time_5', '5 минут', {'time_5': 1.0}),
            ('time_15', '15 минут', {'time_15': 1.0}),
            ('time_30', '30 минут', {'time_30': 1.0}),
            ('time_60', '1 час+', {'time_60': 1.0}),
        ],
    },
    {
        'name': 'time_of_day',
        'title': 'В какое время суток вам проще выполнять задачи?',
        'is_multi_select': True,
        'options': [
            ('tod_morning', 'Утро', {'tod_morning': 1.0}),
            ('tod_day', 'День', {'tod_day': 1.0}),
            ('tod_evening', 'Вечер', {'tod_evening': 1.0}),
            ('tod_night', 'Ночью', {'tod_night': 1.0}),
        ],
    },
    {
        'name': 'interests',
        'title': 'Какие привычки вам интересны?',
        'is_multi_select': True,
        'options': [
            ('int_sport', 'Спорт', {'fitness': 1.0}),
            ('int_read', 'Чтение', {'learning': 1.0}),
            ('int_meditation', 'Медитация', {'mindfulness': 1.0}),
            ('int_sleep', 'Сон', {'sleep': 1.0}),
            ('int_food', 'Питание', {'health': 1.0}),
            ('int_lang', 'Изучение языков', {'learning': 1.0}),
            ('int_prod', 'Продуктивность', {'productivity': 1.0}),
            ('int_finance', 'Финансы', {'finance': 1.0}),
            ('int_self', 'Саморазвитие', {'self_development': 1.0}),
        ],
    },
]


ONBOARDING_HABITS = [
    {
        'key': 'stretch',
        'title': 'Растяжка',
        'description': 'Мягкая разминка для тела без сложного инвентаря.',
        'icon': 'spa',
        'color': 'green',
        'target_type': 'minutes',
        'target_value': 10,
        'target_unit': 'minutes',
        'tags': ['растяжка', 'тело'],
        'signals': {'fitness', 'health', 'time_5', 'time_15', 'tod_morning', 'tod_day'},
    },
    {
        'key': 'walk',
        'title': 'Прогулка',
        'description': 'Короткая прогулка, чтобы добавить движения и проветрить голову.',
        'icon': 'leaf',
        'color': 'green',
        'target_type': 'minutes',
        'target_value': 15,
        'target_unit': 'minutes',
        'tags': ['прогулка', 'здоровье'],
        'signals': {'fitness', 'health', 'mindfulness', 'time_15', 'time_30', 'time_60', 'tod_day', 'tod_evening'},
    },
    {
        'key': 'squats',
        'title': '10 приседаний',
        'description': 'Простой старт для силы и дисциплины.',
        'icon': 'dumbbell',
        'color': 'orange',
        'target_type': 'count',
        'target_value': 10,
        'target_unit': 'times',
        'tags': ['спорт', 'сила'],
        'signals': {'fitness', 'self_development', 'time_5', 'tod_morning', 'tod_day', 'tod_evening'},
    },
    {
        'key': 'water',
        'title': 'Вода утром',
        'description': 'Стакан воды после пробуждения как легкий первый шаг.',
        'icon': 'water',
        'color': 'blue',
        'target_type': 'count',
        'target_value': 1,
        'target_unit': 'glasses',
        'tags': ['вода', 'утро'],
        'signals': {'health', 'sleep', 'self_development', 'time_5', 'tod_morning'},
    },
    {
        'key': 'read',
        'title': 'Читать 10 минут',
        'description': 'Небольшой ежедневный слот для книги, статьи или конспекта.',
        'icon': 'book',
        'color': 'blue',
        'target_type': 'minutes',
        'target_value': 10,
        'target_unit': 'minutes',
        'tags': ['чтение', 'обучение'],
        'signals': {'learning', 'self_development', 'time_15', 'time_30', 'tod_evening'},
    },
    {
        'key': 'review',
        'title': 'Повторить материал',
        'description': 'Вернуться к заметкам и закрепить одну тему.',
        'icon': 'brain',
        'color': 'purple',
        'target_type': 'minutes',
        'target_value': 15,
        'target_unit': 'minutes',
        'tags': ['повторение', 'обучение'],
        'signals': {'learning', 'productivity', 'time_15', 'time_30', 'time_60', 'tod_day', 'tod_evening'},
    },
    {
        'key': 'one_thought',
        'title': 'Записать 1 мысль',
        'description': 'Короткая заметка о том, что понял, почувствовал или решил.',
        'icon': 'brain',
        'color': 'purple',
        'target_type': 'count',
        'target_value': 1,
        'target_unit': 'times',
        'tags': ['заметки', 'рефлексия'],
        'signals': {'mindfulness', 'learning', 'self_development', 'time_5', 'tod_evening', 'tod_night'},
    },
    {
        'key': 'meditation',
        'title': 'Медитация',
        'description': 'Несколько спокойных минут, чтобы снизить шум и вернуться к себе.',
        'icon': 'spa',
        'color': 'green',
        'target_type': 'minutes',
        'target_value': 5,
        'target_unit': 'minutes',
        'tags': ['медитация', 'спокойствие'],
        'signals': {'mindfulness', 'sleep', 'health', 'time_5', 'time_15', 'tod_morning', 'tod_evening', 'tod_night'},
    },
    {
        'key': 'breathing',
        'title': 'Дыхательная практика',
        'description': 'Один короткий цикл дыхания для паузы в течение дня.',
        'icon': 'heart',
        'color': 'pink',
        'target_type': 'minutes',
        'target_value': 5,
        'target_unit': 'minutes',
        'tags': ['дыхание', 'спокойствие'],
        'signals': {'mindfulness', 'health', 'time_5', 'tod_morning', 'tod_day', 'tod_evening'},
    },
    {
        'key': 'gratitude',
        'title': 'Дневник благодарности',
        'description': 'Записать одну вещь, за которую сегодня можно сказать спасибо.',
        'icon': 'heart',
        'color': 'pink',
        'target_type': 'count',
        'target_value': 1,
        'target_unit': 'times',
        'tags': ['дневник', 'благодарность'],
        'signals': {'mindfulness', 'self_development', 'time_5', 'time_15', 'tod_evening', 'tod_night'},
    },
    {
        'key': 'day_plan',
        'title': 'План дня',
        'description': 'Наметить несколько дел до того, как день начнет шуметь.',
        'icon': 'code',
        'color': 'blue',
        'target_type': 'minutes',
        'target_value': 10,
        'target_unit': 'minutes',
        'tags': ['планирование', 'продуктивность'],
        'signals': {'productivity', 'self_development', 'time_15', 'tod_morning', 'tod_night'},
    },
    {
        'key': 'main_task',
        'title': '1 главная задача',
        'description': 'Выбрать один результат дня и держать его в фокусе.',
        'icon': 'code',
        'color': 'orange',
        'target_type': 'count',
        'target_value': 1,
        'target_unit': 'times',
        'tags': ['фокус', 'продуктивность'],
        'signals': {'productivity', 'self_development', 'time_5', 'time_15', 'tod_morning'},
    },
    {
        'key': 'desk_reset',
        'title': 'Убрать рабочее место',
        'description': 'Две минуты порядка вокруг себя, чтобы проще начать.',
        'icon': 'leaf',
        'color': 'green',
        'target_type': 'minutes',
        'target_value': 5,
        'target_unit': 'minutes',
        'tags': ['порядок', 'организация'],
        'signals': {'productivity', 'mindfulness', 'time_5', 'tod_morning', 'tod_evening'},
    },
    {
        'key': 'phone_away',
        'title': 'Убрать телефон перед сном',
        'description': 'Освободить последний отрезок вечера от бесконечной ленты.',
        'icon': 'moon',
        'color': 'purple',
        'target_type': 'check',
        'target_value': 1,
        'target_unit': 'times',
        'tags': ['сон', 'режим'],
        'signals': {'sleep', 'mindfulness', 'health', 'time_5', 'tod_night'},
    },
    {
        'key': 'evening_ritual',
        'title': 'Вечерний ритуал',
        'description': 'Один повторяемый вечерний шаг: душ, книга, тишина или подготовка одежды.',
        'icon': 'moon',
        'color': 'blue',
        'target_type': 'minutes',
        'target_value': 15,
        'target_unit': 'minutes',
        'tags': ['сон', 'вечер'],
        'signals': {'sleep', 'mindfulness', 'time_15', 'time_30', 'tod_evening', 'tod_night'},
    },
    {
        'key': 'creative_note',
        'title': 'Творческая заметка',
        'description': 'Набросать идею, фразу, рисунок или маленький фрагмент проекта.',
        'icon': 'palette',
        'color': 'pink',
        'target_type': 'minutes',
        'target_value': 10,
        'target_unit': 'minutes',
        'tags': ['творчество', 'идея'],
        'signals': {'learning', 'mindfulness', 'time_15', 'tod_day', 'tod_evening'},
    },
    {
        'key': 'message_friend',
        'title': 'Написать близкому',
        'description': 'Короткое сообщение человеку, с которым хочется сохранить связь.',
        'icon': 'heart',
        'color': 'pink',
        'target_type': 'count',
        'target_value': 1,
        'target_unit': 'times',
        'tags': ['общение', 'баланс'],
        'signals': {'mindfulness', 'health', 'time_5', 'tod_day', 'tod_evening'},
    },
    {
        'key': 'expense_tracking',
        'title': 'Учет финансов',
        'description': 'Записать свои траты за день.',
        'icon': 'wallet',
        'color': 'orange',
        'target_type': 'minutes',
        'target_value': 5,
        'target_unit': 'minutes',
        'tags': ['финансы', 'деньги'],
        'signals': {'finance', 'self_development', 'time_5', 'tod_evening'},
    },
    {
        'key': 'budget_review',
        'title': 'Анализ бюджета',
        'description': 'Распределить деньги на неделю и проверить остатки.',
        'icon': 'chart-pie',
        'color': 'blue',
        'target_type': 'minutes',
        'target_value': 15,
        'target_unit': 'minutes',
        'tags': ['финансы', 'планирование'],
        'signals': {'finance', 'productivity', 'time_15', 'time_30', 'tod_morning', 'tod_day'},
    },
]


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
            return redirect('onboarding')
    else:
        form = RegisterForm()
    return render(request, 'auth/register.html', {'form': form})


@login_required
def onboarding(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.onboarding_completed and request.method == 'GET':
        return redirect('dashboard')

    if request.method == 'POST' and request.POST.get('action') == 'skip':
        _complete_onboarding(profile)
        messages.info(request, 'Onboarding пропущен. Ты всегда можешь добавить привычки вручную.')
        return redirect('dashboard')

    if request.method == 'POST' and request.POST.get('action') == 'add':
        selected = request.POST.getlist('habits')
        created_count = _create_onboarding_habits(request.user, selected)
        _complete_onboarding(profile)
        if created_count:
            messages.success(request, f'Добавлено привычек: {created_count}. Можно начинать.')
        else:
            messages.info(request, 'Onboarding завершен. Рекомендации можно добавить вручную позже.')
        return redirect('dashboard')

    answers = _onboarding_answers(request.POST) if request.method == 'POST' else {}
    if request.method == 'POST':
        missing = [q['title'] for q in ONBOARDING_QUESTIONS if not answers.get(q['name'])]
        if missing:
            messages.error(request, 'Ответь на все вопросы, чтобы получить рекомендации.')
        else:
            recommendations = _onboarding_recommendations(answers)
            return render(
                request,
                'onboarding.html',
                {
                    'questions': ONBOARDING_QUESTIONS,
                    'answers': answers,
                    'recommendations': recommendations,
                    'show_recommendations': True,
                },
            )

    return render(
        request,
        'onboarding.html',
        {
            'questions': ONBOARDING_QUESTIONS,
            'answers': answers,
            'recommendations': [],
            'show_recommendations': False,
        },
    )


def _onboarding_answers(post_data) -> dict:
    valid_values = {}
    for question in ONBOARDING_QUESTIONS:
        allowed = {option[0] for option in question['options']}
        valid_values[question['name']] = allowed

    answers = {}
    for name, allowed in valid_values.items():
        values = [value for value in post_data.getlist(name) if value in allowed]
        if values:
            answers[name] = values
    return answers


def _onboarding_recommendations(answers: dict) -> list[dict]:
    # Calculate weighted user signals based on selected options
    user_signals = {}
    for question in ONBOARDING_QUESTIONS:
        q_name = question['name']
        selected_vals = answers.get(q_name, [])
        for option_val, label, weights in question['options']:
            if option_val in selected_vals:
                for sig_name, sig_weight in weights.items():
                    user_signals[sig_name] = user_signals.get(sig_name, 0.0) + sig_weight

    scored = []
    for habit in ONBOARDING_HABITS:
        score = sum(user_signals.get(sig, 0.0) for sig in habit['signals'])
        if score > 0:
            scored.append((score, habit))

    if len(scored) < 3:
        seen = {habit['key'] for _score, habit in scored}
        for habit in ONBOARDING_HABITS:
            if habit['key'] not in seen:
                scored.append((0, habit))
                seen.add(habit['key'])
            if len(scored) >= 3:
                break

    scored.sort(key=lambda item: (-item[0], item[1]['title']))
    return [_with_display_unit(habit) for _score, habit in scored[:3]]


def _with_display_unit(habit: dict) -> dict:
    return {
        **habit,
        'target_label': _target_label(habit['target_value'], habit['target_unit']),
    }


def _target_label(value: int, unit: str) -> str:
    if unit == 'minutes':
        return f'{value} {_plural_ru(value, "минута", "минуты", "минут")}'
    if unit == 'times':
        return f'{value} {_plural_ru(value, "раз", "раза", "раз")}'
    if unit == 'glasses':
        return f'{value} {_plural_ru(value, "стакан", "стакана", "стаканов")}'
    if unit == 'pages':
        return f'{value} {_plural_ru(value, "страница", "страницы", "страниц")}'
    return str(value)


def _plural_ru(value: int, one: str, few: str, many: str) -> str:
    value = abs(value)
    if 11 <= value % 100 <= 14:
        return many
    if value % 10 == 1:
        return one
    if 2 <= value % 10 <= 4:
        return few
    return many


def _create_onboarding_habits(user, selected_keys: list[str]) -> int:
    catalog = {habit['key']: habit for habit in ONBOARDING_HABITS}
    created_count = 0
    for key in selected_keys:
        habit_data = catalog.get(key)
        if not habit_data:
            continue
        habit, created = Habit.objects.get_or_create(
            user=user,
            title=habit_data['title'],
            defaults={
                'description': habit_data['description'],
                'icon': habit_data['icon'],
                'color': habit_data['color'],
                'target_type': habit_data['target_type'],
                'target_value': habit_data['target_value'],
                'target_unit': habit_data['target_unit'],
            },
        )
        if not created and not habit.is_active:
            habit.is_active = True
            habit.save(update_fields=['is_active', 'updated_at'])
        HabitSchedule.objects.get_or_create(habit=habit)
        _attach_onboarding_tags(habit, habit_data['tags'])
        if created:
            created_count += 1
    return created_count


def _attach_onboarding_tags(habit: Habit, tag_names: list[str]) -> None:
    for tag_name in tag_names:
        tag, _ = Tag.objects.get_or_create(
            name=tag_name,
            defaults={'slug': _unique_tag_slug(tag_name)},
        )
        habit.tags.add(tag)


def _unique_tag_slug(name: str) -> str:
    from django.utils.text import slugify

    base = slugify(name, allow_unicode=True) or 'tag'
    candidate = base
    suffix = 1
    while Tag.objects.filter(slug=candidate).exists():
        suffix += 1
        candidate = f'{base}-{suffix}'
    return candidate


def _complete_onboarding(profile: UserProfile) -> None:
    profile.onboarding_completed = True
    profile.save(update_fields=['onboarding_completed', 'updated_at'])


# ---------------------------------------------------------------------------
# Pages.
# ---------------------------------------------------------------------------


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.onboarding_completed:
        return redirect('onboarding')

    today: date = timezone.localdate()
    now = timezone.localtime()
    selected_date = _parse_anchor_date(request.GET.get('date'), today)
    habits = list(
        Habit.objects.filter(user=request.user, is_active=True).select_related('schedule').prefetch_related('tags')
    )
    selected_items = _day_habit_items(request.user, habits, selected_date, now)
    timed_items = [item for item in selected_items if item['sort_time'] is not None]
    untimed_items = [item for item in selected_items if item['sort_time'] is None]
    logs_today = {log.habit_id: log for log in HabitLog.objects.filter(user=request.user, log_date=today)}
    due_today = 0
    done_today = 0
    for habit in habits:
        schedule = getattr(habit, 'schedule', None)
        is_due = True if schedule is None else schedule.is_due_on(today)
        log = logs_today.get(habit.id)
        is_done = bool(log and log.status in {'done', 'partial'})
        if is_due:
            due_today += 1
        if is_done:
            done_today += 1

    # Mini month calendar with intensity.
    cal_start = selected_date.replace(day=1)
    next_month = cal_start.replace(day=28) + timedelta(days=4)
    cal_end = next_month - timedelta(days=next_month.day)
    cal_logs = HabitLog.objects.filter(
        user=request.user,
        log_date__gte=cal_start,
        log_date__lte=cal_end,
        status__in=['done', 'partial'],
    ).values_list('log_date', flat=True)
    cal_active = set(cal_logs)
    # Build an array of {date, in_month, has_activity, is_today}.
    calendar_cells: list[dict] = []
    # Pad to start on Monday.
    start_offset = cal_start.isoweekday() - 1  # Mon=0
    pad_start = cal_start - timedelta(days=start_offset)
    cursor = pad_start
    while cursor <= cal_end or cursor.isoweekday() != 1:
        calendar_cells.append(
            {
                'date': cursor,
                'in_month': cursor.month == selected_date.month,
                'has_activity': cursor in cal_active,
                'is_today': cursor == today,
                'is_selected': cursor == selected_date,
                'dashboard_url': f'{reverse("dashboard")}?date={cursor.isoformat()}',
                'calendar_url': f'{reverse("calendar")}?view=day&date={cursor.isoformat()}',
            }
        )
        cursor += timedelta(days=1)
        if len(calendar_cells) >= 42:
            break

    # Weekly progress card. Use the current ISO week (Mon–Sun) for parity
    # with the calendar page, and the expected-vs-done denominator from
    # services.analytics so the rate isn't inflated to ~100% just because
    # the user only ever logs successful completions.
    week_start, week_end = _week_bounds(today)
    week_progress = user_period_progress(request.user, week_start, week_end)

    insights = UserInsight.objects.filter(user=request.user).order_by('-created_at')[:3]

    add_form = HabitForm()

    context = {
        'today': today,
        'habits': selected_items,
        'timed_habits': timed_items,
        'untimed_habits': untimed_items,
        'selected_date': selected_date,
        'selected_day_heading': _date_heading(selected_date, today),
        'selected_is_today': selected_date == today,
        'due_today': due_today,
        'done_today': done_today,
        'weekly_completion_rate': week_progress['rate'],
        'wt_done': week_progress['done'],
        'wt_total': max(week_progress['expected'], 1),
        'wt_total_real': week_progress['expected'],
        'calendar_cells': calendar_cells,
        'calendar_month': selected_date,
        'calendar_prev_month': (cal_start - timedelta(days=1)).replace(day=1),
        'calendar_next_month': cal_end + timedelta(days=1),
        'calendar_link': f'{reverse("calendar")}?view=month&date={selected_date.isoformat()}',
        'insights': insights,
        'add_form': add_form,
        'habit_form_anchor': selected_date,
    }
    return render(request, 'dashboard.html', context)


# ---------------------------------------------------------------------------
# Calendar.
# ---------------------------------------------------------------------------


_CALENDAR_HOUR_RANGE = list(range(0, 24))  # 00:00 — 23:00
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


def _day_habit_items(user, habits: list[Habit], target_day: date, now=None) -> list[dict]:
    logs = {log.habit_id: log for log in HabitLog.objects.filter(user=user, log_date=target_day)}
    items = []
    check_time = now if target_day == timezone.localdate() else None
    for habit in habits:
        schedule = getattr(habit, 'schedule', None)
        is_due = True if schedule is None else schedule.is_due_on(target_day)
        if not is_due:
            continue
        is_active_now = True if schedule is None else bool(check_time and schedule.is_active_at(check_time))
        log = logs.get(habit.id)
        is_done = bool(log and log.status in {'done', 'partial'})
        sort_time = schedule.window_start if schedule and schedule.window_start else None
        items.append(
            {
                'habit': habit,
                'is_due': is_due,
                'is_active_now': is_active_now,
                'is_done': is_done,
                'today_status': log.status if log else None,
                'log': log,
                'sort_time': sort_time,
                'time_label': (
                    f'{schedule.window_start.strftime("%H:%M")}–{schedule.window_end.strftime("%H:%M")}'
                    if schedule and schedule.has_window
                    else 'Без времени'
                ),
            }
        )
    items.sort(key=lambda item: (item['sort_time'] is None, item['sort_time'] or time.max, item['habit'].title.lower()))
    return items


def _date_heading(target_day: date, today: date) -> str:
    if target_day == today:
        return 'Привычки на сегодня'
    return f'Привычки на {target_day.day} {_RUSSIAN_MONTHS[target_day.month - 1].lower()}'


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
                print(habit, pill)
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


@login_required
@require_POST
def habit_schedule_move(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        target_date = datetime.strptime(payload.get('date', ''), '%Y-%m-%d').date()
        source_raw = payload.get('source_date')
        source_date = datetime.strptime(source_raw, '%Y-%m-%d').date() if source_raw else target_date
        hour_raw = payload.get('hour')
        hour = int(hour_raw) if hour_raw not in (None, '') else None
        clear_time = bool(payload.get('clear_time'))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'detail': 'Некорректная дата или время.'}, status=400)
    if hour is not None and (hour < _CALENDAR_HOUR_RANGE[0] or hour > _CALENDAR_HOUR_RANGE[-1]):
        return JsonResponse({'detail': 'Время вне диапазона календаря.'}, status=400)

    schedule, _ = HabitSchedule.objects.get_or_create(habit=habit)
    if clear_time:
        schedule.window_start = None
        schedule.window_end = None
        schedule.reminder_time = None
    elif hour is not None:
        target_time = time(hour=hour)
        end_hour = min(hour + 1, 23)
        schedule.window_start = target_time
        schedule.window_end = time(hour=end_hour)
        schedule.reminder_time = target_time
    if clear_time and schedule.frequency_type == 'custom':
        schedule.days_of_week = str(target_date.isoweekday())
        schedule.start_date = target_date
        schedule.end_date = target_date
    elif clear_time and schedule.frequency_type == 'weekly':
        schedule.days_of_week = str(target_date.isoweekday())
        schedule.start_date, schedule.end_date = _week_bounds(target_date)
    elif clear_time and (schedule.frequency_type != 'daily' or source_date.isoweekday() != target_date.isoweekday()):
        schedule.frequency_type = 'weekly'
        schedule.days_of_week = str(target_date.isoweekday())
        schedule.start_date, schedule.end_date = _week_bounds(target_date)
    elif clear_time:
        schedule.start_date, schedule.end_date = _week_bounds(target_date)
    elif hour is None and schedule.frequency_type == 'weekly':
        schedule.days_of_week = str(target_date.isoweekday())
        schedule.start_date, schedule.end_date = _week_bounds(target_date)
    elif hour is None or schedule.frequency_type == 'custom':
        schedule.frequency_type = 'custom'
        schedule.days_of_week = str(target_date.isoweekday())
        schedule.start_date = target_date
        schedule.end_date = target_date
    elif schedule.frequency_type != 'daily' or source_date.isoweekday() != target_date.isoweekday():
        schedule.frequency_type = 'weekly'
        schedule.days_of_week = str(target_date.isoweekday())
        schedule.start_date, schedule.end_date = _week_bounds(target_date)
    else:
        schedule.start_date, schedule.end_date = _week_bounds(target_date)
    schedule.save(update_fields=[
        'frequency_type',
        'days_of_week',
        'start_date',
        'end_date',
        'window_start',
        'window_end',
        'reminder_time',
    ])
    return JsonResponse({
        'detail': 'ok',
        'habit_id': habit.id,
        'date': target_date.isoformat(),
        'hour': hour,
        'time_label': f'{hour:02d}:00' if hour is not None else '',
        'frequency_type': schedule.frequency_type,
        'days_of_week': schedule.days_of_week,
    })


@login_required
@require_POST
def habit_create(request):
    form = HabitForm(request.POST)
    if form.is_valid():
        form.save(user=request.user)
        messages.success(request, 'Привычка создана. Вперёд к серии!')
    else:
        errors = '; '.join(msg for msgs in form.errors.values() for msg in msgs)
        messages.error(request, f'Не удалось создать привычку: {errors}')
    return redirect(_safe_next(request))


@login_required
def habit_edit(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    if request.method == 'POST':
        form = HabitForm(request.POST, instance=habit)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, f'Привычка "{habit.title}" обновлена.')
            return redirect('habit_detail', habit_id=habit.id)
        errors = '; '.join(msg for msgs in form.errors.values() for msg in msgs)
        messages.error(request, f'Не удалось обновить привычку: {errors}')
    else:
        form = HabitForm(instance=habit)
    return render(request, 'habit_form.html', {'form': form, 'habit': habit, 'mode': 'edit'})


_STATUS_LABELS = {
    'done': 'выполнено',
    'partial': 'частично',
    'skipped': 'пропущено',
}


def _undo_extra_tags(url: str, label: str = 'Отменить') -> str:
    """Encode an undo action for a flash toast (parsed by base.html JS)."""
    return json.dumps({'undo': url, 'label': label}, ensure_ascii=False)


def _safe_next(request, fallback: str = 'dashboard') -> str:
    """Return a same-origin ``next`` URL or fall back to a named route.

    ``next`` is propagated through hidden form inputs in many templates; an
    attacker could craft a link with ``?next=https://evil.example`` and a
    successful POST would redirect there. ``url_has_allowed_host_and_scheme``
    guards against that classic open-redirect pattern.
    """
    raw = request.POST.get('next') or request.GET.get('next')
    if raw and url_has_allowed_host_and_scheme(
        raw, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return raw
    return fallback


@login_required
@require_POST
def habit_log_today(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    target_day = _parse_anchor_date(request.POST.get('log_date'), timezone.localdate())
    status = request.POST.get('status', 'done')
    if status not in {'done', 'partial', 'skipped'}:
        status = 'done'
    try:
        duration = max(int(request.POST.get('duration_minutes') or 0), 0)
    except (TypeError, ValueError):
        duration = 0
    note = request.POST.get('note', '')
    HabitLog.objects.update_or_create(
        habit=habit,
        log_date=target_day,
        defaults={
            'user': request.user,
            'status': status,
            'value': duration if habit.target_type == 'minutes' else habit.target_value,
            'duration_minutes': duration,
            'note': note,
        },
    )
    label = _STATUS_LABELS.get(status, status)
    messages.success(
        request,
        f'Отметка для "{habit.title}" — {label}.',
        extra_tags=_undo_extra_tags(reverse('habit_log_undo', args=[habit.id]), 'Отменить'),
    )
    return redirect(_safe_next(request))


@login_required
@require_POST
def habit_log_undo(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    target_day = _parse_anchor_date(request.POST.get('log_date'), timezone.localdate())
    deleted, _ = HabitLog.objects.filter(habit=habit, user=request.user, log_date=target_day).delete()
    if deleted:
        # The post_delete signal recomputes current_streak / best_streak for us
        # so the dashboard pill stays accurate.
        messages.success(request, f'Отметка для "{habit.title}" снята.')
    else:
        messages.info(request, f'У "{habit.title}" сегодня и так не было отметки.')
    return redirect(_safe_next(request))


@login_required
@require_POST
def habit_delete(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    habit.is_active = False
    habit.save(update_fields=['is_active', 'updated_at'])
    messages.success(
        request,
        f'Привычка "{habit.title}" архивирована.',
        extra_tags=_undo_extra_tags(reverse('habit_restore', args=[habit.id]), 'Вернуть'),
    )
    return redirect(_safe_next(request))


@login_required
@require_POST
def habit_restore(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    habit.is_active = True
    habit.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f'Привычка "{habit.title}" возвращена в активные.')
    return redirect(_safe_next(request))


@login_required
@require_POST
def habit_destroy(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    title = habit.title
    habit.delete()
    messages.success(request, f'Привычка "{title}" удалена безвозвратно.')
    return redirect(_safe_next(request))


@login_required
def habit_archive_list(request):
    archived = (
        Habit.objects.filter(user=request.user, is_active=False)
        .select_related('schedule')
        .prefetch_related('tags')
        .order_by('-updated_at')
    )
    items: list[dict] = []
    for habit in archived:
        items.append(
            {
                'habit': habit,
                'completed_count': habit_completed_count(habit),
                'total_minutes': habit_total_minutes(habit),
            }
        )
    return render(request, 'habits_archive.html', {'items': items})


@login_required
def habit_detail(request, habit_id: int):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.localdate()
    today_log = habit.logs.filter(log_date=today).first()

    # Heatmap covering last 90 days, organised into 13 weekly columns of 7 cells.
    heatmap = habit_heatmap(habit, days=91)
    # Group into rows by weekday.
    by_weekday: list[list[dict]] = [[], [], [], [], [], [], []]
    for cell in heatmap:
        by_weekday[cell['date'].isoweekday() - 1].append(cell)

    # Last 7 days intensity (Mon..Sun bar chart on the detail page).
    last7_logs = habit.logs.filter(log_date__gte=today - timedelta(days=6))
    weekday_minutes = [0] * 7
    for log in last7_logs:
        if log.status in {'done', 'partial'}:
            idx = log.log_date.isoweekday() - 1
            weekday_minutes[idx] += log.duration_minutes or habit.target_value or 1
    max_min = max(weekday_minutes) or 1
    intensity_bars = [
        {
            'label': label,
            'minutes': mins,
            'pct': max(int(100 * mins / max_min), 8 if mins else 4),
        }
        for label, mins in zip(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'], weekday_minutes)
    ]

    history = habit.logs.order_by('-log_date')[:8]

    # Hour-of-day distribution — "когда я обычно это делаю" over last 90 days.
    hour_dist = habit_hour_distribution(habit, days=90)
    max_hour_count = max(hour_dist['hours']) or 1
    peak_hour = hour_dist['peak_hour']
    best_window = hour_dist['best_window']
    hour_bars = [
        {
            'hour': h,
            'count': cnt,
            # Reserve a tiny min height for non-empty hours so single logs
            # are still visible on the chart.
            'pct': max(int(100 * cnt / max_hour_count), 6 if cnt else 0),
            'is_peak': (peak_hour is not None and h == peak_hour),
            'in_window': (
                best_window is not None
                and (
                    (best_window['start'] <= best_window['end_exclusive'] and best_window['start'] <= h < best_window['end_exclusive'])
                    or (best_window['start'] > best_window['end_exclusive'] and (h >= best_window['start'] or h < best_window['end_exclusive']))
                )
            ),
            'bg': hour_dist['hour_bg'][h],
            'label': f'{h:02d}:00',
        }
        for h, cnt in enumerate(hour_dist['hours'])
    ]
    peak_hour_label = f'{peak_hour:02d}:00' if peak_hour is not None else None

    context = {
        'habit': habit,
        'today_log': today_log,
        'today': today,
        'completion_pct_30': completion_rate_for_habit(habit, days=30),
        'completion_pct_90': completion_rate_for_habit(habit, days=90),
        'total_minutes': habit_total_minutes(habit),
        'completed_count': habit_completed_count(habit),
        'current_streak': habit_current_streak(habit),
        'best_streak': habit_best_streak(habit),
        'heatmap_rows': by_weekday,
        'intensity_bars': intensity_bars,
        'history': history,
        'hour_bars': hour_bars,
        'hour_buckets': hour_dist['buckets'],
        'peak_hour_label': peak_hour_label,
        'peak_bucket': hour_dist['peak_bucket'],
        'hour_total': hour_dist['total'],
        'best_window': best_window,
    }
    return render(request, 'habit_detail.html', context)


@login_required
def analytics(request):
    period = request.GET.get('period', 'month')
    days = {'week': 7, 'month': 30, 'year': 365}.get(period, 30)
    activity = user_activity_per_day(request.user, days=days)
    best_days = user_best_days(request.user, days=days)
    breakdown = user_category_breakdown(request.user, days=days)
    insights = UserInsight.objects.filter(user=request.user).order_by('-created_at')[:5]
    achievements = Achievement.objects.all()
    unlocked_ids = set(UserAchievement.objects.filter(user=request.user).values_list('achievement_id', flat=True))
    completion_total = HabitLog.objects.filter(user=request.user, status__in=['done', 'partial']).count()
    total_minutes = HabitLog.objects.filter(user=request.user, status__in=['done', 'partial']).aggregate(
        total=Sum('duration_minutes')
    )['total'] or 0
    profile = request.user.profile
    # Map condition_type → Tailwind colour pair. The template can't compute
    # this dynamically because Tailwind's JIT only emits classes it sees as
    # literal strings — interpolating "bg-{{type}}-100" produced invalid
    # classes like `bg-streak-100` that silently fall back to no colour.
    _BADGE_PALETTE = {
        'streak': ('bg-orange-100', 'text-orange-600'),
        'completion_count': ('bg-green-100', 'text-green-600'),
        'total_time': ('bg-blue-100', 'text-blue-600'),
        'xp': ('bg-purple-100', 'text-purple-600'),
        'custom': ('bg-amber-100', 'text-amber-600'),
    }
    achievements_data = []
    for a in achievements:
        bg, fg = _BADGE_PALETTE.get(a.condition_type, ('bg-green-100', 'text-green-600'))
        if a.condition_type == 'streak':
            current_value = profile.best_streak
            condition_label = f'Серия {a.condition_value} дн.'
        elif a.condition_type == 'completion_count':
            current_value = completion_total
            condition_label = f'{a.condition_value} выполнений'
        elif a.condition_type == 'total_time':
            current_value = total_minutes
            condition_label = f'{a.condition_value} минут'
        elif a.condition_type == 'xp':
            current_value = profile.level
            condition_label = f'Уровень {a.condition_value}'
        else:
            current_value = 1 if a.id in unlocked_ids else 0
            condition_label = a.get_condition_type_display()
        progress_pct = min(int(100 * current_value / a.condition_value), 100) if a.condition_value else 0
        unlocked = a.id in unlocked_ids
        achievements_data.append(
            {
                'achievement': a,
                'unlocked': unlocked,
                'is_close': (not unlocked and progress_pct >= 70),
                'current_value': current_value,
                'condition_label': condition_label,
                'progress_pct': progress_pct,
                'status_label': 'Получено' if unlocked else ('Близко' if progress_pct >= 70 else 'Не получено'),
                'badge_bg': bg,
                'badge_fg': fg,
            }
        )
    unlocked_achievements = [entry for entry in achievements_data if entry['unlocked']]
    close_achievements = [entry for entry in achievements_data if entry['is_close']]
    locked_achievements = [entry for entry in achievements_data if not entry['unlocked'] and not entry['is_close']]
    # Average completion rate. Naively averaging each weekday's percentage
    # double-counts days where the user has no due habits at all (rate=0
    # because expected=0) and silently drags the headline number down. Weight
    # the average by the actual number of expected slots instead.
    total_expected = sum(b['expected'] for b in best_days)
    total_done = sum(b['done'] for b in best_days)
    avg = min(int(100 * total_done / total_expected), 100) if total_expected else 0

    # Donut chart needs cumulative offsets.
    chart_categories = []
    cumulative = 0
    palette = ['#4CAF50', '#FFB74D', '#64B5F6', '#BA68C8', '#FF8A65', '#F06292']
    for idx, row in enumerate(breakdown):
        chart_categories.append(
            {
                **row,
                'color': palette[idx % len(palette)],
                'offset': cumulative,
            }
        )
        cumulative += row['pct']

    # Find best/weak day for the highlight card.
    best_day = best_days[0] if best_days else None
    active_days = sum(1 for row in activity if row['count'] > 0)
    # "Morning %" — share of successful logs created before local-noon. We have
    # to compute the hour in the user's timezone in Python because Django's
    # ``__hour`` ORM lookup extracts in the database's connection timezone
    # (UTC), which on a Europe/Moscow site shifts "morning" by +3h.
    recent_done_logs = HabitLog.objects.filter(
        user=request.user,
        status__in=['done', 'partial'],
        log_date__gte=timezone.localdate() - timedelta(days=days - 1),
    ).only('created_at')
    total_done = 0
    morning_done = 0
    for log in recent_done_logs:
        total_done += 1
        if timezone.localtime(log.created_at).hour < 12:
            morning_done += 1
    morning_pct = int(100 * morning_done / total_done) if total_done else 0

    # Build chart bars (downsample if too many).
    max_count = max((row['count'] for row in activity), default=0) or 1
    chart_bars = [
        {
            'date': row['date'],
            'count': row['count'],
            'height_pct': max(int(100 * row['count'] / max_count), 3 if row['count'] else 0),
        }
        for row in activity
    ]

    # Habit pair correlations — only meaningful on the month/year periods
    # where the user has enough history. Skip on the 7-day view.
    correlations = []
    if days >= 14:
        correlations = user_habit_correlations(request.user, days=days)

    context = {
        'period': period,
        'days': days,
        'activity': activity,
        'chart_bars': chart_bars,
        'best_days': best_days,
        'breakdown': breakdown,
        'chart_categories': chart_categories,
        'achievements_data': achievements_data,
        'unlocked_achievements': unlocked_achievements,
        'close_achievements': close_achievements,
        'locked_achievements': locked_achievements,
        'insights': insights,
        'best_day': best_day,
        'avg_completion': avg,
        'active_days': active_days,
        'total_done': total_done,
        'total_expected': total_expected,
        'morning_pct': morning_pct,
        'correlations': correlations,
    }
    return render(request, 'analytics.html', context)


# ---------------------------------------------------------------------------
# Notification AJAX endpoints.
# ---------------------------------------------------------------------------


@login_required
def notifications_list(request):
    """Return JSON list of the user's notifications (last 50) + unread count."""
    notifs = Notification.objects.filter(user=request.user)[:50]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    items = []
    for n in notifs:
        items.append({
            'id': n.id,
            'type': n.notif_type,
            'title': n.title,
            'message': n.message,
            'icon': n.icon,
            'is_read': n.is_read,
            'achievement_id': n.achievement_id,
            'extra_data': n.extra_data or {},
            'created_at': n.created_at.isoformat(),
        })
    return JsonResponse({'notifications': items, 'unread_count': unread_count})


@login_required
@require_POST
def notifications_mark_read(request):
    """Mark specific notifications as read. Expects JSON body: {"ids": [1,2,3]}."""
    import json as _json
    try:
        body = _json.loads(request.body)
        ids = body.get('ids', [])
    except (ValueError, AttributeError):
        ids = []
    if ids:
        updated = Notification.objects.filter(
            user=request.user, id__in=ids, is_read=False
        ).update(is_read=True)
    else:
        updated = 0
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'updated': updated, 'unread_count': unread_count})


@login_required
@require_POST
def add_recommended_habits(request):
    """Create habits from recommendation data (JSON).

    Used by both the onboarding recommendation modal and the notification
    bell 'Add' button.  Expects::

        { "habits": [
            { "title": "...", "icon": "spa", "color": "green",
              "target_type": "check", "target_value": 1,
              "target_unit": "times", "tags": ["..."],
              "description": "..." },
            ...
        ] }
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'detail': 'Некорректный JSON.'}, status=400)

    habits_data = body.get('habits')
    if not habits_data or not isinstance(habits_data, list):
        return JsonResponse({'detail': 'Ожидается массив habits.'}, status=400)

    created_ids = []
    for item in habits_data[:10]:  # hard cap
        title = (item.get('title') or '').strip()
        if not title:
            continue
        habit, created = Habit.objects.get_or_create(
            user=request.user,
            title=title,
            defaults={
                'description': item.get('description', ''),
                'icon': item.get('icon', 'spa'),
                'color': item.get('color', 'green'),
                'target_type': item.get('target_type', 'check'),
                'target_value': item.get('target_value', 1),
                'target_unit': item.get('target_unit', 'times'),
            },
        )
        if not created and not habit.is_active:
            habit.is_active = True
            habit.save(update_fields=['is_active', 'updated_at'])
        HabitSchedule.objects.get_or_create(habit=habit)
        tag_names = item.get('tags', [])
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            tag, _ = Tag.objects.get_or_create(
                name=tag_name,
                defaults={'slug': _unique_tag_slug(tag_name)},
            )
            habit.tags.add(tag)
        if created:
            created_ids.append(habit.id)

    return JsonResponse({
        'created_count': len(created_ids),
        'habit_ids': created_ids,
    })


@login_required
def notification_detail(request, notif_id: int):
    """Return JSON with full notification details + linked achievement data."""
    notif = get_object_or_404(Notification, id=notif_id, user=request.user)
    data = {
        'id': notif.id,
        'type': notif.notif_type,
        'type_display': notif.get_notif_type_display(),
        'title': notif.title,
        'message': notif.message,
        'icon': notif.icon,
        'is_read': notif.is_read,
        'created_at': notif.created_at.isoformat(),
        'achievement': None,
    }
    if notif.achievement:
        a = notif.achievement
        data['achievement'] = {
            'id': a.id,
            'code': a.code,
            'title': a.title,
            'description': a.description,
            'condition_type': a.condition_type,
            'condition_display': a.get_condition_type_display(),
            'condition_value': a.condition_value,
            'xp_reward': a.xp_reward,
            'icon': a.icon,
        }
    return JsonResponse(data)
