from rest_framework import serializers

from .models import Habit, HabitLog, HabitSchedule, Tag, TagCategory


class HabitSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Habit
        fields = "__all__"
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Название привычки обязательно.")

        if len(value) < 2:
            raise serializers.ValidationError("Название должно быть минимум 2 символа.")

        return value

    def validate_target_value(self, value):
        if value < 1:
            raise serializers.ValidationError("Цель должна быть больше 0.")

        return value

    def validate(self, attrs):
        target_type = attrs.get("target_type", getattr(self.instance, "target_type", "check"))
        target_unit = attrs.get("target_unit", getattr(self.instance, "target_unit", ""))

        if target_type == "minutes" and target_unit not in ["minutes", ""]:
            raise serializers.ValidationError(
                {
                    "target_unit": "Для цели в минутах лучше выбрать единицу 'minutes'."
                }
            )

        return attrs


class HabitLogSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = HabitLog
        fields = "__all__"
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]


class HabitScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitSchedule
        fields = "__all__"


class TagCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TagCategory
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"