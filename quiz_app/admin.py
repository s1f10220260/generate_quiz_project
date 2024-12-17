# quiz_project/quiz_app/admin.py

from django.contrib import admin
from .models import Quiz, UserResponse

admin.site.register(Quiz)
admin.site.register(UserResponse)