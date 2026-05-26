"""Signals: profile auto-creation, gamification on log save / delete."""
from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from habits.models import HabitLog, UserProfile
from habits.services.gamification import (
    award_xp_for_log,
    check_achievements,
    deduct_xp_for_log,
    refresh_streaks,
)
from habits.services.insights import generate_insights


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(pre_save, sender=HabitLog)
def capture_old_status(sender, instance: HabitLog, **kwargs):
    if instance.pk:
        try:
            old = HabitLog.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except HabitLog.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=HabitLog)
def on_habit_log_saved(sender, instance: HabitLog, created, **kwargs):
    profile, _ = UserProfile.objects.get_or_create(user=instance.user)
    if created and instance.status in {'done', 'partial'}:
        award_xp_for_log(profile, instance)
    elif not created and instance._old_status in {'done', 'partial'} and instance.status not in {'done', 'partial'}:
        deduct_xp_for_log(profile, instance)
    refresh_streaks(profile)
    check_achievements(profile)
    if created:
        generate_insights(instance.user)


@receiver(post_delete, sender=HabitLog)
def on_habit_log_deleted(sender, instance: HabitLog, **kwargs):
    profile = UserProfile.objects.filter(user=instance.user).first()
    if profile is not None:
        if instance.status in {'done', 'partial'}:
            deduct_xp_for_log(profile, instance)
        refresh_streaks(profile)
