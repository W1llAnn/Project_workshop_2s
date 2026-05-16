"""DRF views."""
from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from habits.api.serializers import (
    AchievementSerializer,
    HabitLogSerializer,
    HabitSerializer,
    InsightSerializer,
    LoginSerializer,
    RegisterSerializer,
    TagCategorySerializer,
    TagSerializer,
    UserAchievementSerializer,
    UserProfileSerializer,
)
from habits.models import (
    Achievement,
    Habit,
    HabitLog,
    Tag,
    TagCategory,
    UserAchievement,
    UserInsight,
    UserProfile,
)
from habits.services.analytics import (
    completion_rate_for_habit,
    habit_completed_count,
    habit_heatmap,
    habit_total_minutes,
    user_summary,
)
from habits.services.streak import habit_best_streak, habit_current_streak


# ---------------------------------------------------------------------------
# Auth.
# ---------------------------------------------------------------------------


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(UserProfileSerializer(user.profile).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response({'detail': 'Неверный логин или пароль'}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        return Response(UserProfileSerializer(user.profile).data)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detail': 'ok'})


class MeView(APIView):
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data)
