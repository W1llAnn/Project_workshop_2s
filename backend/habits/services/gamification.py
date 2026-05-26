"""XP, levels and achievements."""
from __future__ import annotations

from django.db.models import Sum
from django.utils import timezone

from habits.models import Achievement, HabitLog, Notification, UserAchievement, UserProfile
from habits.services.streak import user_current_streak


XP_PER_DONE = 10
XP_PER_PARTIAL = 4
XP_PER_MINUTE = 1


def _xp_for_log(log: HabitLog) -> int:
    """Calculate XP a HabitLog is worth (no side effects)."""
    delta = 0
    if log.status == 'done':
        delta += XP_PER_DONE
    elif log.status == 'partial':
        delta += XP_PER_PARTIAL
    delta += min(log.duration_minutes, 60) * XP_PER_MINUTE // 4
    return delta


def award_xp_for_log(profile: UserProfile, log: HabitLog) -> int:
    """Award XP for a saved HabitLog. Returns delta XP."""
    delta = _xp_for_log(log)
    if delta <= 0:
        return 0
    profile.xp += delta
    while profile.xp >= profile.xp_for_next_level:
        profile.xp -= profile.xp_for_next_level
        profile.level += 1
    profile.save(update_fields=['xp', 'level', 'updated_at'])
    return delta


def deduct_xp_for_log(profile: UserProfile, log: HabitLog) -> int:
    """Deduct XP when a habit log is undone. De-levels if needed, never goes below 0."""
    delta = _xp_for_log(log)
    if delta <= 0:
        return 0
    profile.xp -= delta
    while profile.xp < 0 and profile.level > 1:
        profile.level -= 1
        profile.xp += profile.xp_for_next_level
    if profile.xp < 0:
        profile.xp = 0
    profile.save(update_fields=['xp', 'level', 'updated_at'])
    return delta


def refresh_streaks(profile: UserProfile) -> None:
    streak = user_current_streak(profile.user)
    profile.current_streak = streak
    if streak > profile.best_streak:
        profile.best_streak = streak
    if streak >= 5:
        profile.mascot_mood = 'excited'
    elif streak >= 1:
        profile.mascot_mood = 'happy'
    else:
        profile.mascot_mood = 'sad'
    profile.save(update_fields=['current_streak', 'best_streak', 'mascot_mood', 'updated_at'])


# Icon mapping for achievement condition types.
_ACHIEVEMENT_ICONS = {
    'streak': 'fa-fire',
    'completion_count': 'fa-check-double',
    'total_time': 'fa-clock',
    'xp': 'fa-star',
    'custom': 'fa-award',
}


def check_achievements(profile: UserProfile) -> list[Achievement]:
    """Unlock any achievements whose conditions the user has now met."""
    user = profile.user
    unlocked_codes = set(
        UserAchievement.objects.filter(user=user).values_list('achievement__code', flat=True)
    )
    candidates = Achievement.objects.exclude(code__in=unlocked_codes)
    newly_unlocked: list[Achievement] = []
    completion_count = HabitLog.objects.filter(user=user, status__in=['done', 'partial']).count()
    total_minutes = HabitLog.objects.filter(
        user=user, status__in=['done', 'partial']
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0
    for achievement in candidates:
        unlocked = False
        if achievement.condition_type == 'streak':
            unlocked = profile.best_streak >= achievement.condition_value
        elif achievement.condition_type == 'completion_count':
            unlocked = completion_count >= achievement.condition_value
        elif achievement.condition_type == 'total_time':
            unlocked = total_minutes >= achievement.condition_value
        elif achievement.condition_type == 'xp':
            unlocked = profile.level >= achievement.condition_value
        if unlocked:
            UserAchievement.objects.create(
                user=user, achievement=achievement, unlocked_at=timezone.now()
            )
            # Create a notification for the bell dropdown.
            # Ensure the icon stored on the Notification is a full FontAwesome
            # class (e.g. "fa-spa" or "fa-trophy"). In templates we render
            # the icon as `class="fas ${icon}"`, so persist the `fa-` prefix
            # if the achievement record only contains the short name like
            # "spa" or "book".
            raw_icon = achievement.icon
            if raw_icon:
                icon = raw_icon if raw_icon.startswith('fa-') else f'fa-{raw_icon}'
            else:
                icon = _ACHIEVEMENT_ICONS.get(achievement.condition_type, 'fa-trophy')
            Notification.objects.create(
                user=user,
                notif_type='achievement',
                title=f'🏆 {achievement.title}',
                message=achievement.description or f'Награда: +{achievement.xp_reward} XP',
                achievement=achievement,
                icon=icon,
            )
            profile.xp += achievement.xp_reward
            newly_unlocked.append(achievement)
    if newly_unlocked:
        # Re-level after bonus XP.
        while profile.xp >= profile.xp_for_next_level:
            profile.xp -= profile.xp_for_next_level
            profile.level += 1
        profile.save(update_fields=['xp', 'level', 'updated_at'])
    return newly_unlocked
