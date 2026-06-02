import random
from habits.models import Notification
from ml_recommendations.recommender import recommend_for_user, train_model
from celery import shared_task


@shared_task
def train_recommendation_model_task():
    print('Старт процесса обучения модели')
    train_model()
    print('Итерация обучения модели завершена')


@shared_task
def create_user_recommendations_task(user_id: int | None = None):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    users = User.objects.all()

    if user_id:
        users = users.filter(id=user_id)

    for user in users:
        recommendation = recommend_for_user(user_id=user.pk, top_k=5)

        try:
            rec = recommendation[random.randint(0, 4)]
            print(rec)
        except IndexError:
            print(f'skip for user_id={user.pk}')
            continue
        message = f'Новая рекомендация привычки: {rec["habit_title"]}, {rec["explanation"]}'
        title = 'У вас новая рекомендация привычки'
        
        exists_notification = Notification.objects.filter(user_id=user.pk, title=title).last()

        # костыльно защищаемся от дублей
        if not exists_notification or exists_notification.message != message:
            Notification.objects.create(
                user=user,
                notif_type='recommendation',
                title=title,
                message=message,
                icon='fa-lightbulb',
                extra_data={
                    'habit_title': rec['habit_title'],
                    'habit_id': rec.get('habit_id'),
                    'explanation': rec['explanation'],
                    'score': rec.get('score'),
                    'create_data': {
                        'title': rec['habit_title'],
                        'icon': 'spa',
                        'color': 'green',
                        'target_type': 'check',
                        'target_value': 1,
                        'target_unit': 'times',
                        'tags': [],
                        'description': rec.get('explanation', ''),
                    },
                },
            )
