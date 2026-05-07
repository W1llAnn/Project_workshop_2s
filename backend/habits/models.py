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

    
class TagCategory(models.Model):
    """Категория для тегов (иерархическая)."""
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Слаг')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tag_categories'
        verbose_name = 'Категория тега'
        verbose_name_plural = 'Категории тегов'

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Тег привычки."""
    category = models.ForeignKey(
        TagCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tags',
        verbose_name='Категория'
    )
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Слаг')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tags'
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class HabitTag(models.Model):
    """Связь многие-ко-многим между привычками и тегами."""
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='habit_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='habit_tags')

    class Meta:
        db_table = 'habit_tags'
        verbose_name = 'Связь привычки и тега'
        verbose_name_plural = 'Связи привычек и тегов'
        constraints = [
            models.UniqueConstraint(fields=['habit', 'tag'], name='unique_habit_tag')
        ]

    def __str__(self):
        return f'{self.habit.title} - {self.tag.name}'


class Achievement(models.Model):
    """Справочник достижений."""
    CONDITION_CHOICES = [
        ('streak', 'Серия дней'),
        ('completion_count', 'Количество выполнений'),
        ('total_time', 'Суммарное время'),
        ('xp', 'Количество XP'),
        ('custom', 'Своё условие'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='Системный код')
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    condition_type = models.CharField(max_length=30, choices=CONDITION_CHOICES, verbose_name='Тип условия')
    condition_value = models.IntegerField(verbose_name='Значение условия')
    xp_reward = models.IntegerField(default=0, verbose_name='Награда XP')
    icon = models.CharField(max_length=100, blank=True, null=True, verbose_name='Иконка')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'achievements'
        verbose_name = 'Достижение'
        verbose_name_plural = 'Достижения'

    def __str__(self):
        return self.title


class UserAchievement(models.Model):
    """Полученные пользователем достижения."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='user_achievements')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_achievements'
        verbose_name = 'Достижение пользователя'
        verbose_name_plural = 'Достижения пользователей'
        constraints = [
            models.UniqueConstraint(fields=['user', 'achievement'], name='unique_user_achievement')
        ]

    def __str__(self):
        return f'{self.user.username} - {self.achievement.title}'


class Challenge(models.Model):
    """Справочник челленджей."""
    CONDITION_CHOICES = [
        ('completion_count', 'Количество выполнений'),
        ('tag_completion_count', 'Количество выполнений по тегу'),
        ('streak', 'Серия дней'),
        ('total_time', 'Суммарное время'),
        ('custom', 'Своё условие'),
    ]

    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    condition_type = models.CharField(max_length=30, choices=CONDITION_CHOICES, verbose_name='Тип условия')
    condition_value = models.IntegerField(verbose_name='Значение условия')
    xp_reward = models.IntegerField(default=0, verbose_name='Награда XP')
    start_date = models.DateField(null=True, blank=True, verbose_name='Дата начала')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'challenges'
        verbose_name = 'Челлендж'
        verbose_name_plural = 'Челленджи'

    def __str__(self):
        return self.title


class UserChallenge(models.Model):
    """Участие пользователя в челленджах."""
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('completed', 'Завершён'),
        ('failed', 'Провален'),
        ('cancelled', 'Отменён'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_challenges')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='user_challenges')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    progress = models.IntegerField(default=0, verbose_name='Прогресс')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата присоединения')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')

    class Meta:
        db_table = 'user_challenges'
        verbose_name = 'Участие в челлендже'
        verbose_name_plural = 'Участия в челленджах'
        constraints = [
            models.UniqueConstraint(fields=['user', 'challenge'], name='unique_user_challenge')
        ]

    def __str__(self):
        return f'{self.user.username} - {self.challenge.title} ({self.status})'


class UserInsight(models.Model):
    """Персональные инсайты пользователя."""
    INSIGHT_CHOICES = [
        ('weak_day', 'Слабый день'),
        ('best_day', 'Лучший день'),
        ('streak', 'Серия'),
        ('tag_analytics', 'Аналитика по тегам'),
        ('mascot_message', 'Сообщение маскота'),
        ('custom', 'Своё'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='insights')
    insight_type = models.CharField(max_length=30, choices=INSIGHT_CHOICES, verbose_name='Тип инсайта')
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Текст сообщения')
    payload = models.JSONField(default=dict, blank=True, verbose_name='Доп. данные')
    period_start = models.DateField(null=True, blank=True, verbose_name='Начало периода')
    period_end = models.DateField(null=True, blank=True, verbose_name='Конец периода')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_insights'
        verbose_name = 'Инсайт пользователя'
        verbose_name_plural = 'Инсайты пользователей'
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.title}'