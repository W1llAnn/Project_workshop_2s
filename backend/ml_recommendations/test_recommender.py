#!/usr/bin/env python3
"""
🐹 HabitHamster: Генерация рекомендаций для конкретного пользователя
Запуск: python generate_user_recs.py --user=2
"""

import sys
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import argparse
import warnings
warnings.filterwarnings('ignore')

# ==================== КОНФИГ БД ====================

DB_CONFIG = {
    'host': '0.0.0.0',
    'port': '5432',
    'name': 'habithamster',
    'user': 'habithamster',
    'password': 'OcP-------'
}

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['name']}"
)


# ==================== ЗАГРУЗКА ДАННЫХ ====================

def load_data():
    """Загрузка данных из БД"""
    engine = create_engine(DATABASE_URL)
    
    logs_query = """
    SELECT 
        hl.user_id, hl.habit_id, hl.status, hl.duration_minutes,
        hl.value, hl.log_date,
        h.title as habit_title, h.description as habit_description,
        h.target_type, h.target_value, h.target_unit,
        up.level as user_level, up.xp as user_xp, up.current_streak, up.best_streak
    FROM habits_habitlog hl
    JOIN habits_habit h ON hl.habit_id = h.id
    JOIN habits_userprofile up ON hl.user_id = up.user_id
    WHERE h.is_active = true
    ORDER BY hl.log_date DESC
    """
    logs = pd.read_sql(logs_query, engine)
    
    tags_query = """
    SELECT 
        ht.habit_id, t.name as tag_name, t.slug as tag_slug, 
        at.name as activity_type
    FROM habits_habittag ht
    JOIN habits_tag t ON ht.tag_id = t.id
    LEFT JOIN habits_activitytype at ON t.activity_type_id = at.id
    """
    tags = pd.read_sql(tags_query, engine)
    
    return logs, tags


# ==================== СКОРИНГ ====================

def calc_interaction_score(status):
    """Кодирование статуса"""
    return {'done': 1.0, 'partial': 0.6, 'skipped': 0.1, 'missed': 0.0}.get(status, 0.0)


def generate_recommendations(user_id, top_k=5, logs=None, tags=None):
    """
    Генерация персональных рекомендаций
    
    Алгоритм:
    1. Берём привычки, которых нет у пользователя
    2. Считаем средний success rate у других пользователей
    3. Добавляем matching по тегам
    4. Добавляем шум для дифференциации
    """
    if logs is None or tags is None:
        logs, tags = load_data()
    
    # Score для каждого лога
    logs['score'] = logs['status'].apply(calc_interaction_score)
    
    # Привычки пользователя
    user_habits = set(logs[logs['user_id'] == user_id]['habit_id'])
    print(f"📊 У пользователя {user_id} привычек: {len(user_habits)}")
    
    # Признаки пользователя
    ulogs = logs[logs['user_id'] == user_id]
    user_level = ulogs['user_level'].mean() if len(ulogs) > 0 else 1
    user_tags = set(tags[tags['habit_id'].isin(user_habits)]['tag_slug'].dropna())
    user_activity_types = set(tags[tags['habit_id'].isin(user_habits)]['activity_type'].dropna())
    
    print(f"📊 Уровень пользователя: {user_level:.1f}")
    print(f"📊 Теги пользователя: {user_tags}")
    print()
    
    # Кандидаты: привычки других пользователей
    candidates = logs[~logs['habit_id'].isin(user_habits)]['habit_id'].unique()
    print(f"📊 Кандидатов на рекомендацию: {len(candidates)}")
    
    recs = []
    np.random.seed(user_id * 42)  # Фиксированный seed для воспроизводимости
    
    for hid in candidates:
        hlogs = logs[logs['habit_id'] == hid]
        if len(hlogs) == 0:
            continue
        
        # 1. Success rate у других пользователей
        avg_score = hlogs['score'].mean()
        completions = len(hlogs[hlogs['status'] == 'done'])
        total = len(hlogs)
        
        # 2. Matching по тегам
        habit_tags = set(tags[tags['habit_id'] == hid]['tag_slug'].dropna())
        habit_activity = set(tags[tags['habit_id'] == hid]['activity_type'].dropna())
        
        tag_match = len(habit_tags & user_tags) / max(len(habit_tags | user_tags), 1) if (habit_tags | user_tags) else 0.5
        activity_match = len(habit_activity & user_activity_types) / max(len(habit_activity | user_activity_types), 1) if (habit_activity | user_activity_types) else 0.5
        
        # 3. Сложность vs уровень
        hlogs_first = hlogs.iloc[0]
        diff_map = {'check': 1, 'minutes': 0.5, 'count': 1.5}
        difficulty = hlogs_first['target_value'] * diff_map.get(hlogs_first['target_type'], 1)
        level_match = min(user_level / max(difficulty / 10, 1), 1.5)
        
        # 4. Финальный скор (взвешенная комбинация)
        base_score = (
            0.5 * avg_score + 
            0.2 * tag_match + 
            0.15 * activity_match + 
            0.15 * level_match
        )
        
        # 5. Шум для дифференциации (±5%)
        noise = np.random.uniform(-0.05, 0.05)
        final_score = np.clip(base_score + noise, 0, 1)
        
        # 6. Объяснение
        reasons = []
        if avg_score > 0.8:
            reasons.append(f"высокий успех ({completions}/{total} выполнений)")
        if tag_match > 0.5:
            reasons.append(f"совпадает с интересами ({len(habit_tags & user_tags)} общих тегов)")
        if activity_match > 0.5:
            reasons.append(f"подходит по типу активности")
        if level_match > 1.0:
            reasons.append("соответствует вашему уровню")
        if not reasons:
            reasons.append("персонализированная рекомендация")
        
        recs.append({
            'habit_id': int(hid),
            'habit_title': hlogs_first['habit_title'],
            'habit_description': hlogs_first['habit_description'] or 'Без описания',
            'target': f"{hlogs_first['target_value']} {hlogs_first['target_unit'] or 'раз'}",
            'score': round(final_score, 3),
            'avg_success_rate': round(avg_score, 3),
            'tag_match': round(tag_match, 2),
            'explanation': "; ".join(reasons[:2]),
            'completions': completions,
            'total_attempts': total,
        })
    
    # Сортировка по score
    recs.sort(key=lambda x: x['score'], reverse=True)
    return recs[:top_k]


# ==================== ВЫВОД ====================

def print_recommendations(recs, user_id):
    """Красивый вывод рекомендаций"""
    print("\n" + "=" * 70)
    print(f"🎯 ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЯ #{user_id}")
    print("=" * 70 + "\n")
    
    if not recs:
        print("⚠️ Нет рекомендаций (возможно, у пользователя уже все привычки)")
        return
    
    for i, r in enumerate(recs, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        
        print(f"{medal} {r['habit_title']}")
        print(f"   📝 {r['habit_description']}")
        print(f"   🎯 Цель: {r['target']}")
        print(f"   💡 {r['explanation']}")
        print(f"   📊 Уверенность: {r['score']:.1%} (успех у других: {r['avg_success_rate']:.1%})")
        print(f"   ✅ Выполнений: {r['completions']}/{r['total_attempts']}")
        print()
    
    print("=" * 70)
    print(f"📈 Диапазон уверенности: {recs[-1]['score']:.1%} – {recs[0]['score']:.1%}")
    print("=" * 70)


def save_to_file(recs, user_id):
    """Сохранение в JSON"""
    import json
    from datetime import datetime
    
    output = {
        'user_id': user_id,
        'generated_at': datetime.now().isoformat(),
        'recommendations': recs,
    }
    
    filename = f'recommendations_user_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Сохранено в: {filename}")


# ==================== ЗАПУСК ====================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Генерация рекомендаций для пользователя')
    parser.add_argument('--user', type=int, required=True, help='ID пользователя')
    parser.add_argument('--top', type=int, default=5, help='Количество рекомендаций')
    parser.add_argument('--save', action='store_true', help='Сохранить в JSON файл')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🐹 HabitHamster: Генерация рекомендаций")
    print("=" * 70)
    print(f"👤 Пользователь ID: {args.user}")
    print(f"📊 Количество: {args.top}")
    print("=" * 70 + "\n")
    
    try:
        # Загрузка данных
        print("🔄 Загрузка данных из БД...")
        logs, tags = load_data()
        print(f"✅ Загружено: {len(logs)} логов, {len(tags)} тегов\n")
        
        # Генерация
        recs = generate_recommendations(
            user_id=args.user, 
            top_k=args.top,
            logs=logs, 
            tags=tags
        )
        
        # Вывод
        print_recommendations(recs, args.user)
        
        # Сохранение
        if args.save:
            save_to_file(recs, args.user)
        
    except Exception as e:
        print(f"\n❌ Ошибка: {type(e).__name__}: {e}")
        print("\n💡 Проверьте:")
        print("   1. Параметры подключения к БД в начале скрипта")
        print("   2. Доступность сервера PostgreSQL")
        print("   3. Установлены ли зависимости: pip install psycopg2-binary sqlalchemy pandas numpy")
        sys.exit(1)