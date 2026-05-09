from rest_framework import serializers

from .models import Habit, HabitLog


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