from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
class Quiz(models.Model):
    question = models.CharField(max_length=255)
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    correct_answer = models.IntegerField()  # 正解の選択肢を1, 2, 3, 4で指定
    difficulty = models.IntegerField()  # 難易度
    user = models.ForeignKey(User, on_delete=models.CASCADE) #Userと紐づけ

class UserResponse(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE) #Quizと紐づけ
    user = models.ForeignKey(User, on_delete=models.CASCADE) #Userと紐づけ
    selected_option = models.IntegerField()  # ユーザーが選んだ選択肢
    is_correct = models.BooleanField()
    perceived_difficulty = models.IntegerField(null=True, blank=True)  # ユーザーが感じた難易度 (1-10)
    session_id = models.CharField(max_length=255, default='', db_index=True)  # セッションIDで回答を紐付け
    created_at = models.DateTimeField(auto_now_add=True)
