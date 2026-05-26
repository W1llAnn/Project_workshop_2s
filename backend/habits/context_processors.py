"""Inject the user's profile and a shared "add habit" form into templates."""
from habits.forms import HabitForm
from habits.models import Notification, UserProfile


def profile_context(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return {
        'profile': profile,
        # Always available so the shared "create habit" modal in base.html
        # works on every authenticated page (dashboard, habit_detail, …).
        'add_form': HabitForm(),
        'unread_notifications_count': unread_count,
    }
