"""
🐹 HabitHamster: Minimal Hybrid Recommender
Всё в одном файле: обучение + предсказание + объяснения
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from lightgbm import LGBMClassifier
from django.conf import settings
from django.db.models import Avg

# Пути
MODEL_DIR = Path(settings.BASE_DIR) / 'ml_models'
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / 'rec_model_v1.pkl'


# ==================== ДАННЫЕ ====================

def load_data():
    """Загрузка данных из БД в pandas"""
    from django.db import connection
    
    # Логи + привычки + пользователи
    logs_query = """
    SELECT 
        hl.user_id, hl.habit_id, hl.status, hl.log_date,
        h.title as habit_title, h.target_type, h.target_value,
        up.level as user_level, up.current_streak
    FROM habits_habitlog hl
    JOIN habits_habit h ON hl.habit_id = h.id
    JOIN habits_userprofile up ON hl.user_id = up.user_id
    WHERE h.is_active = true
    """
    logs = pd.read_sql(logs_query, connection)
    
    # Теги (упрощённо: один тег на привычку)
    tags_query = """
    SELECT DISTINCT ON (ht.habit_id) 
        ht.habit_id, t.slug as tag_slug, at.name as activity_type
    FROM habits_habittag ht
    JOIN habits_tag t ON ht.tag_id = t.id
    LEFT JOIN habits_activitytype at ON t.activity_type_id = at.id
    """
    tags = pd.read_sql(tags_query, connection)
    
    return logs, tags


def calc_interaction_score(status):
    """Простое кодирование статуса"""
    return {'done': 1.0, 'partial': 0.6, 'skipped': 0.1, 'missed': 0.0}.get(status, 0.0)


# ==================== ОБУЧЕНИЕ ====================

def train_model(model_name='rec_model_v1'):
    """Обучение гибридной модели (упрощённо)"""
    print("🔄 Загрузка данных...")
    logs, tags = load_data()
    
    if len(logs) < 50:
        raise ValueError(f"Мало данных: {len(logs)} логов (нужно ≥50)")
    
    # Подготовка признаков
    logs['score'] = logs['status'].apply(calc_interaction_score)
    logs['weight'] = np.exp(-(pd.Timestamp.now().date() - pd.to_datetime(logs['log_date']).dt.date).days / 30)
    
    # Агрегация user-habit
    interaction = (
        logs.groupby(['user_id', 'habit_id'])
        .apply(lambda x: np.average(x['score'], weights=x['weight'] + 0.01))
        .reset_index().rename(columns={0: 'weighted_score'})
    )
    
    # Матрица для CF
    matrix = interaction.pivot(index='user_id', columns='habit_id', values='weighted_score').fillna(0)
    
    # Простые признаки для каждой пары
    data = []
    for _, row in interaction.iterrows():
        uid, hid = row['user_id'], row['habit_id']
        
        # Пользователь
        ulogs = logs[logs['user_id'] == uid]
        user_feat = {
            'level': ulogs['user_level'].mean(),
            'streak': ulogs['current_streak'].max(),
            'avg_score': ulogs['score'].mean(),
        }
        
        # Привычка
        hlogs = logs[logs['habit_id'] == hid].iloc[0]
        diff_map = {'check': 1, 'minutes': 0.5, 'count': 1.5}
        difficulty = hlogs['target_value'] * diff_map.get(hlogs['target_type'], 1)
        
        # Теги (упрощённо)
        habit_tags = set(tags[tags['habit_id'] == hid]['tag_slug'].dropna())
        user_tags = set(tags[tags['habit_id'].isin(ulogs['habit_id'])]['tag_slug'].dropna())
        tag_match = len(habit_tags & user_tags) / max(len(habit_tags | user_tags), 1) if (habit_tags | user_tags) else 0.5
        
        # CF: похожие пользователи
        if len(matrix) > 1 and uid in matrix.index:
            user_vec = matrix.loc[uid].values.reshape(1, -1)
            sims = cosine_similarity(user_vec, matrix.values)[0]
            cf_score = np.mean([interaction[(interaction['user_id'] == matrix.index[i]) & (interaction['habit_id'] == hid)]['weighted_score'].iloc[0] 
                               for i in np.argsort(sims)[-5:] if i != uid and len(interaction[(interaction['user_id'] == matrix.index[i]) & (interaction['habit_id'] == hid)]) > 0] or [0.5])
        else:
            cf_score = 0.5
        
        # Целевая: успех = среднее ≥0.7
        target = 1 if row['weighted_score'] >= 0.7 else 0
        
        data.append({
            'user_level': user_feat['level'],
            'user_streak': user_feat['streak'],
            'user_avg_score': user_feat['avg_score'],
            'habit_difficulty': min(difficulty / 50, 1.0),
            'tag_match': tag_match,
            'cf_score': cf_score,
            'target': target,
            'user_id': uid, 'habit_id': hid
        })
    
    df = pd.DataFrame(data)
    if len(df) < 30:
        raise ValueError(f"Мало пар для обучения: {len(df)}")
    
    # Обучение
    X = df.drop(['target', 'user_id', 'habit_id'], axis=1)
    y = df['target']
    
    model = LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, 
                          class_weight='balanced', verbose=-1, random_state=42)
    model.fit(X, y)
    
    # Сохранение
    joblib.dump({'model': model, 'features': list(X.columns), 'matrix': matrix}, MODEL_PATH)
    print(f"✅ Модель сохранена: {MODEL_PATH}")
    print(f"📊 Обучено на {len(df)} примерах, {X.shape[1]} признаков")
    
    return model


# ==================== ПРЕДСКАЗАНИЕ ====================

def recommend_for_user(user_id: int, top_k: int = 5, min_score: float = 0.5):
    """Генерация рекомендаций для пользователя"""
    
    # Загрузка модели
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Модель не найдена. Запустите: python manage.py train_model")
    
    data = joblib.load(MODEL_PATH)
    model, features, matrix = data['model'], data['features'], data['matrix']
    
    # Данные
    logs, tags = load_data()
    user_habits = set(logs[logs['user_id'] == user_id]['habit_id'])
    
    # Признаки пользователя
    ulogs = logs[logs['user_id'] == user_id]
    if len(ulogs) == 0:
        return _fallback_recommendations(user_id, top_k)
    
    user_feat = {
        'level': ulogs['user_level'].mean(),
        'streak': ulogs['current_streak'].max(),
        'avg_score': ulogs['score'].mean(),
    }
    user_tags = set(tags[tags['habit_id'].isin(ulogs['habit_id'])]['tag_slug'].dropna())
    
    # Кандидаты: привычки других пользователей
    candidates = logs[~logs['habit_id'].isin(user_habits)]['habit_id'].unique()[:100]
    
    recs = []
    for hid in candidates:
        hlogs = logs[logs['habit_id'] == hid].iloc[0]
        
        # Признаки привычки
        diff_map = {'check': 1, 'minutes': 0.5, 'count': 1.5}
        difficulty = hlogs['target_value'] * diff_map.get(hlogs['target_type'], 1)
        
        habit_tags = set(tags[tags['habit_id'] == hid]['tag_slug'].dropna())
        tag_match = len(habit_tags & user_tags) / max(len(habit_tags | user_tags), 1) if (habit_tags | user_tags) else 0.5
        
        # CF скор
        if user_id in matrix.index and hid in matrix.columns:
            user_vec = matrix.loc[user_id].values.reshape(1, -1)
            sims = cosine_similarity(user_vec, matrix.values)[0]
            cf_score = np.mean([matrix.iloc[i][hid] for i in np.argsort(sims)[-5:] 
                               if i != user_id and hid in matrix.columns and matrix.iloc[i].get(hid, 0) > 0] or [0.5])
        else:
            cf_score = 0.5
        
        # Фичи для модели
        X = pd.DataFrame([{
            'user_level': user_feat['level'],
            'user_streak': user_feat['streak'],
            'user_avg_score': user_feat['avg_score'],
            'habit_difficulty': min(difficulty / 50, 1.0),
            'tag_match': tag_match,
            'cf_score': cf_score,
        }])
        
        # Предсказание
        proba = model.predict_proba(X[features])[0][1]
        
        if proba >= min_score:
            # Объяснение
            reasons = []
            if tag_match > 0.4: reasons.append("совпадает с вашими интересами")
            if user_feat['level'] >= difficulty / 10: reasons.append("подходит вашему уровню")
            if cf_score > 0.6: reasons.append("похожие пользователи выполняют")
            
            recs.append({
                'habit_id': int(hid),
                'habit_title': hlogs['habit_title'],
                'score': round(proba, 3),
                'explanation': "; ".join(reasons[:2]) if reasons else "персонализировано",
            })
    
    # Сортировка + шум для дифференциации
    np.random.seed(user_id)
    for r in recs:
        r['score'] = round(np.clip(r['score'] + np.random.uniform(-0.02, 0.02), 0, 1), 3)
    
    recs.sort(key=lambda x: x['score'], reverse=True)
    return recs[:top_k]


def _fallback_recommendations(user_id: int, top_k: int):
    """Fallback: популярные привычки"""
    logs, _ = load_data()
    popular = (
        logs.groupby('habit_id')['score']
        .agg(['mean', 'count'])
        .assign(final=lambda x: x['mean'] * np.log1p(x['count']))
        .sort_values('final', ascending=False)
        .head(top_k * 2)
    )
    
    return [
        {
            'habit_id': int(hid),
            'habit_title': logs[logs['habit_id'] == hid]['habit_title'].iloc[0],
            'score': round(row['final'], 3),
            'explanation': "популярная привычка",
        }
        for hid, row in popular.iterrows()
    ][:top_k]