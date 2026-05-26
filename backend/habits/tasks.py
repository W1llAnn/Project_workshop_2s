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
        recommendation = recommend_for_user(user_id=user.pk, top_k=1)

        message = f'Новая рекомендация привычки: {recommendation[0]["habit_title"]}, {recommendation[0]["explanation"]}'
        title = 'У вас новая рекомендация'
        
        exists_notification = Notification.objects.filter(user_id=user_id, title=title).latest('created_at')

        # костыльно защищаемся от дублей
        if exists_notification.message != message:
            Notification.objects.create(
                user=user,
                notif_type='recommendation',
                title='У вас новая рекомендация привычки',
                message=message,
                icon='fa-lightbulb-o',
            )
