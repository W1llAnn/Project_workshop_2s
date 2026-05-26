"""Fix existing notification icons: ensure they have the fa- prefix."""

from django.db import migrations

_ACHIEVEMENT_ICONS = {
    'streak': 'fa-fire',
    'completion_count': 'fa-check-double',
    'total_time': 'fa-clock',
    'xp': 'fa-star',
    'custom': 'fa-award',
}


def fix_notification_icons(apps, schema_editor):
    Notification = apps.get_model('habits', 'Notification')
    for n in Notification.objects.filter(achievement__isnull=False).iterator():
        raw = n.achievement.icon
        if raw:
            if not raw.startswith('fa-'):
                n.icon = f'fa-{raw}'
        else:
            n.icon = _ACHIEVEMENT_ICONS.get(n.achievement.condition_type, 'fa-trophy')
        n.save(update_fields=['icon'])


def reverse_fix(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('habits', '0005_notification'),
    ]

    operations = [
        migrations.RunPython(fix_notification_icons, reverse_fix),
    ]
