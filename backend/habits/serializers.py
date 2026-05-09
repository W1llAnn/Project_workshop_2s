from rest_framework import serializers

from .models import Habit, HabitLog, HabitSchedule, Tag, TagCategory

class HabitSerializer(serializers.ModelSerializer):
    """
    Serializer для модели Habit.

    Переводит объект привычки из Django в JSON
    и помогает принимать JSON от frontend.
    """

    class Meta:
        model = Habit
        fields = [
            "id",
            "user",
            "title",
            "description",
            "target_type",
            "target_value",
            "target_unit",
            "color",
            "icon",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class HabitLogSerializer(serializers.ModelSerializer):
    """
    Serializer для модели HabitLog.

    Нужен для истории выполнения привычек.
    """

    class Meta:
        model = HabitLog
        fields = [
            "id",
            "habit",
            "user",
            "log_date",
            "status",
            "value",
            "duration_minutes",
            "note",
            "mood_score",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class HabitScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer для расписания привычки.

    Нужен, чтобы описывать частоту выполнения:
    ежедневно, еженедельно, дни недели, период действия.
    """

    class Meta:
        model = HabitSchedule
        fields = [
            "id",
            "habit",
            "frequency_type",
            "days_of_week",
            "times_per_period",
            "reminder_time",
            "start_date",
            "end_date",
        ]
        read_only_fields = [
            "id",
        ]


class TagCategorySerializer(serializers.ModelSerializer):
    """
    Serializer для категории тегов.

    Например:
    - Здоровье
    - Осознанность
    - Продуктивность
    """

    class Meta:
        model = TagCategory
        fields = [
            "id",
            "parent",
            "name",
            "slug",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]


class TagSerializer(serializers.ModelSerializer):
    """
    Serializer для тега привычки.

    Например:
    - Фитнес
    - Сон
    - Учёба
    - Медитация
    """

    class Meta:
        model = Tag
        fields = [
            "id",
            "category",
            "name",
            "slug",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]