from habits.models import Notification
from ml_recommendations.recommender import recommend_for_user, train_model
from celery import shared_task


@shared_task
def train_recommendation_model_task():
    print('Старт процесса обучения модели')
    train_model()
    print('Итерация обучения модели завершена')


@shared_task
def create_user_recommendations_task():
    from django.contrib.auth import get_user_model

    User = get_user_model()
    users = User.objects.all()

    for user in users:
        recommendation = recommend_for_user(user_id=user.pk, top_k=1)

        Notification.objects.create(
            user=user,
            notif_type='recommendation',
            title='У вас новая рекомендация привычки',
            message=f'Новая рекомендация привычки: {recommendation["habit_title"]}, {recommendation["explanation"]}',
            icon='fa-award',
        )
