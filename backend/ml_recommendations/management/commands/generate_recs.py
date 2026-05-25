from django.core.management.base import BaseCommand
from ml_recommendations.recommender import recommend_for_user

class Command(BaseCommand):
    help = 'Сгенерировать рекомендации для пользователя'
    
    def add_arguments(self, parser):
        parser.add_argument('--user', type=int, required=True, help='ID пользователя')
        parser.add_argument('--top', type=int, default=5, help='Количество рекомендаций')
    
    def handle(self, *args, **options):
        user_id = options['user']
        top_k = options['top']
        
        self.stdout.write(f"👤 Рекомендации для пользователя #{user_id}:\n")
        try:
            recs = recommend_for_user(user_id, top_k=top_k)
            if recs:
                for i, r in enumerate(recs, 1):
                    self.stdout.write(
                        f"{i}. {r['habit_title']}\n"
                        f"   💡 {r['explanation']}\n"
                        f"   📊 {r['score']:.1%}\n"
                    )
            else:
                self.stdout.write(self.style.WARNING("⚠️ Нет рекомендаций (мало данных?)"))
        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f"❌ {e}\n💡 Запустите: python manage.py train_model"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка: {e}"))