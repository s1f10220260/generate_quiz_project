from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='/home/')),
    path('home/', views.home_view, name='home'),
    path('quiz/start', views.start_quiz, name='start_quiz'),
    path('quiz/take', views.take_quiz, name='take_quiz'),
    path('register_user/', views.register_user, name='register_user'),
    path('summary/', views.summary, name='summary'),
    path('quiz_list/', views.quiz_list, name='quiz_list'),
    path('user_response_list/', views.user_response_list, name='user_response_list'),
    path('difficulty_evaluation/', views.difficulty_evaluation, name='difficulty_evaluation'),
]
