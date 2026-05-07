from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class User(AbstractUser):
    """
    Расширенная модель пользователя.
    Поля: username, email, password (хешируется автоматически), is_active,
    created_at (date_joined), updated_at (добавляем вручную).
    """
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    """Профиль пользователя с игровыми характеристиками."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    level = models.IntegerField(default=1, verbose_name='Уровень')
    xp = models.IntegerField(default=0, verbose_name='Опыт (XP)')
    current_streak = models.IntegerField(default=0, verbose_name='Текущая серия')
    best_streak = models.IntegerField(default=0, verbose_name='Лучшая серия')
    mascot_name = models.CharField(max_length=50, blank=True, default='Хома', verbose_name='Имя маскота')
    mascot_mood = models.CharField(
        max_length=20,
        choices=[('happy', 'Счастлив'), ('sad', 'Грустный'), ('neutral', 'Нейтральный')],
        default='neutral',
        verbose_name='Настроение маскота'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f'Профиль {self.user.username}'


class Habit(models.Model):
    """Привычка пользователя."""
    TARGET_TYPE_CHOICES = [
        ('check', 'Отметка'),
        ('minutes', 'Минуты'),
        ('count', 'Количество'),
    ]
    TARGET_UNIT_CHOICES = [
        ('times', 'раз(а)'),
        ('minutes', 'минут'),
        ('pages', 'страниц'),
        ('steps', 'шагов'),
        ('glasses', 'стаканов'),
        ('kilometers', 'километров'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='habits',
        verbose_name='Пользователь'
    )
    title = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES, default='check', verbose_name='Тип цели')
    target_value = models.IntegerField(default=1, verbose_name='Целевое значение')
    target_unit = models.CharField(max_length=20, choices=TARGET_UNIT_CHOICES, blank=True, verbose_name='Единица измерения')
    color = models.CharField(max_length=7, default='#4CAF50', verbose_name='Цвет (HEX)')
    icon = models.CharField(max_length=50, blank=True, verbose_name='Иконка')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'habits'
        verbose_name = 'Привычка'
        verbose_name_plural = 'Привычки'

    def __str__(self):
        return self.title


class HabitSchedule(models.Model):
    """Расписание привычки."""
    FREQUENCY_CHOICES = [
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
        ('custom', 'Своё'),
    ]

    habit = models.OneToOneField(
        Habit,
        on_delete=models.CASCADE,
        related_name='schedule',
        verbose_name='Привычка'
    )
    frequency_type = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily', verbose_name='Тип частоты')
    days_of_week = models.JSONField(default=list, blank=True, verbose_name='Дни недели (1-7)')
    times_per_period = models.IntegerField(default=1, verbose_name='Количество раз за период')
    reminder_time = models.TimeField(null=True, blank=True, verbose_name='Время напоминания')
    start_date = models.DateField(default=timezone.now, verbose_name='Дата начала')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')

    class Meta:
        db_table = 'habit_schedules'
        verbose_name = 'Расписание привычки'
        verbose_name_plural = 'Расписания привычек'

    def __str__(self):
        return f'Расписание {self.habit.title}'


class HabitLog(models.Model):
    """Запись выполнения привычки за день."""
    STATUS_CHOICES = [
        ('done', 'Выполнено'),
        ('missed', 'Пропущено'),
        ('skipped', 'Осознанно пропущено'),
        ('partial', 'Частично'),
    ]

    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='Привычка'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='habit_logs',
        verbose_name='Пользователь'
    )
    log_date = models.DateField(verbose_name='Дата выполнения')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='done', verbose_name='Статус')
    value = models.IntegerField(default=0, verbose_name='Фактическое значение')
    duration_minutes = models.IntegerField(default=0, verbose_name='Потрачено минут')
    note = models.TextField(blank=True, null=True, verbose_name='Заметка')
    mood_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка настроения (1-5)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'habit_logs'
        verbose_name = 'Лог привычки'
        verbose_name_plural = 'Логи привычек'
        constraints = [
            models.UniqueConstraint(fields=['habit', 'log_date'], name='unique_habit_log_per_day')
        ]
        indexes = [
            models.Index(fields=['habit', 'log_date']),
            models.Index(fields=['user', 'log_date']),
        ]

    def __str__(self):
        return f'{self.habit.title} - {self.log_date} - {self.status}'