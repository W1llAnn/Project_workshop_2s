"""
5 примеров работы модели рекомендаций
Запуск: python backend\ml_recommendations\demo_examples.py
"""

from recommendation import recommend_habits


def print_user_profile(num, title, test_input):
    print(f"\n{'='*60}")
    print(f"👤 Пользователь #{num}: {title}")
    print(f"{'='*60}")
    print("Входные данные:")
    for key, value in test_input.items():
        print(f"  • {key}: {value}")


def print_recommendations(result):
    print(f"\n📊 Вектор предпочтений:")
    for cat, val in result["user_vector"].items():
        bar = "█" * int(val * 20)
        print(f"  {cat:20} {val:.3f} {bar}")
    
    print(f"\n🎯 Рекомендованные привычки:")
    for i, habit in enumerate(result["recommendations"], 1):
        print(f"\n  {i}. {habit['title']}")
        print(f"     🏷  Категория: {habit['category']}")
        print(f"     ⏱  Время: {habit['time_required']}")
        print(f"     🕐 Лучше: {', '.join(habit['best_time'])}")
        print(f"     🏷  Теги: {', '.join(habit['tags'])}")
    
    print(f"\n📈 Метаданные:")
    print(f"  • Фильтр по времени: {result['metadata']['time_filtered']}")
    print(f"  • Диверсификация: {result['metadata']['diversity_applied']}")
    print(f"  • Кандидатов всего: {result['metadata']['total_candidates']}")
    print(f"  • Выше порога: {result['metadata']['scored_above_threshold']}")


# ============================================================================
# 5 ПРИМЕРОВ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

# Пример 1: Продуктивность + чтение (вечерний человек)
user_1 = {
    "goals": ["productivity"],
    "sport_frequency": "1-2 times/week",
    "difficulties": ["concentration"],
    "free_time": "15 minutes",
    "preferred_time": ["evening"],
    "interests": ["reading", "productivity"]
}

# Пример 2: Здоровье + фитнес (утренний человек)
user_2 = {
    "goals": ["health", "fitness"],
    "sport_frequency": "3-5 times/week",
    "difficulties": ["exercise"],
    "free_time": "30 minutes",
    "preferred_time": ["morning"],
    "interests": ["sport", "nutrition"]
}

# Пример 3: Снижение стресса + сон (ночной человек, проблемы со сном)
user_3 = {
    "goals": ["sleep", "mindfulness"],
    "sport_frequency": "never",
    "difficulties": ["wake_up", "rest"],
    "free_time": "5 minutes",
    "preferred_time": ["night"],
    "interests": ["meditation", "sleep"]
}

# Пример 4: Обучение + саморазвитие (студент, гибкое время)
user_4 = {
    "goals": ["learning", "self_development"],
    "sport_frequency": "1-2 times/week",
    "difficulties": ["read"],
    "free_time": "1 hour+",
    "preferred_time": ["afternoon", "evening"],
    "interests": ["languages", "reading", "self_development"]
}

# Пример 5: Баланс (много целей, нет явных предпочтений по времени)
user_5 = {
    "goals": ["productivity", "health", "learning"],
    "sport_frequency": "every day",
    "difficulties": ["drink_water", "concentration"],
    "free_time": "15 minutes",
    "preferred_time": ["morning", "evening"],
    "interests": ["sport", "productivity", "finance"]
}


# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🧪" * 30)
    print("ДЕМО: 5 примеров работы модели рекомендаций")
    print("🧪" * 30)
    
    examples = [
        (1, "Продуктивность + чтение (вечер)", user_1),
        (2, "Здоровье + фитнес (утро)", user_2),
        (3, "Стресс + сон (ночь)", user_3),
        (4, "Обучение + саморазвитие (студент)", user_4),
        (5, "Баланс всех сфер (активный)", user_5),
    ]
    
    for num, title, test_input in examples:
        print_user_profile(num, title, test_input)
        result = recommend_habits(test_input)
        print_recommendations(result)
    
    print(f"\n{'='*60}")
    print("✅ Все 5 примеров завершены!")
    print(f"{'='*60}\n")