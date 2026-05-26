from django.core.management.base import BaseCommand
from ml_recommendations.recommender import train_model


class Command(BaseCommand):
    help = 'Обучить модель рекомендаций (одна команда)'
    
    def handle(self, *args, **options):
        self.stdout.write("🚀 Обучение модели...")
        train_model()
        self.stdout.write(self.style.SUCCESS("✅ Готово!"))            