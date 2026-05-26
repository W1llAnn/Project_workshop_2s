from django.db import migrations, models


def mark_existing_profiles_complete(apps, schema_editor):
    UserProfile = apps.get_model('habits', 'UserProfile')
    UserProfile.objects.update(onboarding_completed=True)


class Migration(migrations.Migration):

    dependencies = [
        ('habits', '0007_alter_notification_notif_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='onboarding_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_existing_profiles_complete, migrations.RunPython.noop),
    ]
