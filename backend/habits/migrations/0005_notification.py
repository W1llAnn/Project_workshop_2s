# Generated migration for the Notification model.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('habits', '0004_drop_monthly_frequency'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notif_type', models.CharField(
                    choices=[
                        ('achievement', 'Достижение'),
                        ('level_up', 'Повышение уровня'),
                        ('streak', 'Серия'),
                        ('system', 'Системное'),
                    ],
                    default='achievement',
                    max_length=24,
                )),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField(blank=True, default='')),
                ('icon', models.CharField(blank=True, default='fa-trophy', max_length=64)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('achievement', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='notifications',
                    to='habits.achievement',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Уведомление',
                'verbose_name_plural': 'Уведомления',
                'ordering': ['-created_at'],
            },
        ),
    ]
