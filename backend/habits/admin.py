from django.contrib import admin
from .models import (
    User, UserProfile, Habit, HabitSchedule, HabitLog, TagCategory,
    Tag, HabitTag, Achievement, UserAchievement, Challenge,
    UserChallenge, UserInsight
)

admin.site.register(User)
admin.site.register(UserProfile)
admin.site.register(Habit)
admin.site.register(HabitSchedule)
admin.site.register(HabitLog)
admin.site.register(TagCategory)
admin.site.register(Tag)
admin.site.register(HabitTag)
admin.site.register(Achievement)
admin.site.register(UserAchievement)
admin.site.register(Challenge)
admin.site.register(UserChallenge)
admin.site.register(UserInsight)