import re

with open('habits/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace ONBOARDING_QUESTIONS and ONBOARDING_HABITS
questions_habits_new = """ONBOARDING_QUESTIONS = [
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
]"""

answers_rec_new = """def _onboarding_answers(post_data) -> dict:
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
    return [_with_display_unit(habit) for _score, habit in scored[:3]]"""

content = re.sub(r'ONBOARDING_QUESTIONS = \[.*?\]\s*ONBOARDING_HABITS = \[.*?\]', questions_habits_new, content, flags=re.DOTALL)
content = re.sub(r'def _onboarding_answers\(post_data\) -> dict:.*?def _with_display_unit', answers_rec_new + '\n\n\ndef _with_display_unit', content, flags=re.DOTALL)

with open('habits/views.py', 'w', encoding='utf-8') as f:
    f.write(content)