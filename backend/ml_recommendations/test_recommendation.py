"""
Простые тесты для функции recommend_habits
Запуск: python -m pytest backend/ml_recommendations/test_recommendation.py -v
Или: python backend/ml_recommendations/test_recommendation.py
"""

import json
from recommendation import recommend_habits, build_user_vector, normalize_vector, cosine_similarity


def test_recommend_habits_basic():
    """Базовый тест: функция возвращает 3 рекомендации."""
    test_input = {
        "goals": ["productivity"],
        "sport_frequency": "1-2 times/week",
        "difficulties": ["concentration"],
        "free_time": "15 minutes",
        "preferred_time": ["evening"],
        "interests": ["reading", "productivity"]
    }
    
    result = recommend_habits(test_input)
    
    assert "recommendations" in result
    assert len(result["recommendations"]) == 3
    assert "user_vector" in result
    assert "metadata" in result
    print("✅ test_recommend_habits_basic passed")


def test_recommend_habits_with_json_string():
    """Тест: функция принимает JSON-строку."""
    test_json = json.dumps({
        "goals": ["health", "sleep"],
        "sport_frequency": "never",
        "difficulties": ["wake_up"],
        "free_time": "5 minutes",
        "preferred_time": ["morning"],
        "interests": ["meditation"]
    })
    
    result = recommend_habits(test_json)
    
    assert len(result["recommendations"]) == 3
    assert result["metadata"]["time_filtered"] is True
    print("✅ test_recommend_habits_with_json_string passed")


def test_user_vector_building():
    """Тест: корректное формирование вектора пользователя."""
    test_input = {
        "goals": ["productivity"],
        "sport_frequency": "1-2 times/week",
        "difficulties": ["concentration"],
        "free_time": "15 minutes",
        "preferred_time": ["evening"],
        "interests": ["reading", "productivity"]
    }
    
    vector = build_user_vector(test_input)
    
    # Вектор должен быть нормализован (L2-норма ≈ 1 или 0)
    vector_norm = (vector ** 2).sum() ** 0.5
    assert abs(vector_norm - 1.0) < 1e-6 or vector_norm == 0.0
    
    # productivity и learning должны быть среди самых высоких
    assert vector[2] > 0.3  # productivity (индекс 2 в ONBOARDING_CATEGORIES)
    print("✅ test_user_vector_building passed")


def test_cosine_similarity():
    """Тест: косинусное сходство работает корректно."""
    vec1 = normalize_vector({"productivity": 1.0, "learning": 0.5})
    vec2 = normalize_vector({"productivity": 1.0, "learning": 0.5})
    vec3 = normalize_vector({"fitness": 1.0, "health": 1.0})
    
    # Одинаковые векторы → сходство = 1
    assert abs(cosine_similarity(vec1, vec2) - 1.0) < 1e-6
    
    # Ортогональные векторы → сходство ≈ 0
    assert cosine_similarity(vec1, vec3) >= 0.0
    assert cosine_similarity(vec1, vec3) <= 0.3
    print("✅ test_cosine_similarity passed")


def test_diversity_in_recommendations():
    """Тест: рекомендации из разных категорий (при включённой диверсификации)."""
    test_input = {
        "goals": ["productivity", "health", "learning"],
        "sport_frequency": "3-5 times/week",
        "difficulties": [],
        "free_time": "30 minutes",
        "preferred_time": [],
        "interests": ["sport", "reading", "meditation"]
    }
    
    result = recommend_habits(test_input)
    categories = [h["category"] for h in result["recommendations"]]
    
    # При включённой диверсификации категории должны быть уникальны
    # (или хотя бы 2 из 3 разных, если в БД мало вариантов)
    unique_cats = len(set(categories))
    assert unique_cats >= 2, f"Expected diverse categories, got: {categories}"
    print("✅ test_diversity_in_recommendations passed")


def test_time_filtering():
    """Тест: фильтрация по времени суток."""
    test_input = {
        "goals": ["sleep"],
        "sport_frequency": "never",
        "difficulties": ["wake_up"],
        "free_time": "5 minutes",
        "preferred_time": ["night"],
        "interests": []
    }
    
    result = recommend_habits(test_input)
    
    # Метаданные должны показать, что фильтрация применялась
    assert result["metadata"]["time_filtered"] is True
    print("✅ test_time_filtering passed")


def test_empty_input():
    """Тест: обработка пустых/минимальных входных данных."""
    result = recommend_habits({})
    
    assert "recommendations" in result
    # Даже с пустым входом должны вернуться какие-то рекомендации (fallback)
    assert len(result["recommendations"]) >= 1
    print("✅ test_empty_input passed")


if __name__ == "__main__":
    # Запуск всех тестов при прямом вызове файла
    print("🧪 Запуск тестов recommendation.py...\n")
    
    test_recommend_habits_basic()
    test_recommend_habits_with_json_string()
    test_user_vector_building()
    test_cosine_similarity()
    test_diversity_in_recommendations()
    test_time_filtering()
    test_empty_input()
    
    print("\n✅ Все тесты пройдены!")