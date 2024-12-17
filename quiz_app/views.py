import random
from django.shortcuts import render, redirect
from .models import Quiz, UserResponse, User
from django.db.models import F
import json
from django.utils.timezone import now
from django.conf import settings
import uuid

import openai
#API_KEY,API_BASEを設定
client = openai.OpenAI(
    api_key = settings.OPENAI_API_KEY,
    base_url = settings.OPENAI_API_BASE,
    )

def home_view(request):
    return render(request, 'quiz_app/home.html')

def start_quiz(request):
    # セッションの初期設定
    request.session['session_id'] = str(uuid.uuid4())  # セッションIDを生成
    request.session['current_index'] = 0
    request.session['quiz_iteration'] = 0  # 反復カウンター
    request.session['quizzes'] = []  # クイズリストを初期化
    request.session['quiz_ids'] = []
    
    return redirect('take_quiz')
        
def generate_quiz_batch(request):
    session_id = request.session.get('session_id')
    user_id = request.session.get('user_id')  # セッションからユーザーIDを取得
    user = User.objects.get(id=user_id)  # ユーザーオブジェクトを取得

    # クイズIDリストをリセット
    request.session['quiz_ids'] = []
    
    recent_responses = UserResponse.objects.filter(
        session_id=session_id,
        user_id = user_id
    ).order_by('-created_at')[:10]

    # 過去の評価データをプロンプトに組み込む
    feedback_text = "\n".join([(
        "{\n"
        f'  "問題": "{resp.quiz.question}",\n'
        f'  "選択肢1": "{resp.quiz.option_1}",\n'
        f'  "選択肢2": "{resp.quiz.option_2}",\n'
        f'  "選択肢3": "{resp.quiz.option_3}",\n'
        f'  "選択肢4": "{resp.quiz.option_4}",\n'
        f'  "正解番号": {resp.quiz.correct_answer},\n'
        f'  "難易度": {resp.perceived_difficulty}\n'
        "}"
    ) for resp in recent_responses
    ]) if recent_responses else "なし"

    difficulty_list = list(range(1, 11))
    
    for _ in range(10):  # 10問生成
        difficulty = random.choice(difficulty_list)  # ランダムに一つ選択
        difficulty_list.remove(difficulty)  # 選択した要素をリストから削除
        
        prompt = f"""
        #命令文:
        あなたは{{プロの日本史教師}}です。以下の#制約条件に従い、{{最高の4択問題}}を作成してください。

        #制約条件:
        ・問題のテーマは「日本史」に限定してください。
        ・難易度(1~10)を{difficulty}に設定し、それに応じた問題を作成してください。難易度１を簡単な基本問題、難易度１０を難しい応用問題と定義します。
        ・以下の#フィードバックを参考に、問題の難易度や表現を調整してください。ただし、同様の問題は出題しないこと。
        ・歴史的な事実や人物に関しては情報の正確性を最優先してください。
        ・出題の根拠が不明確な選択肢や曖昧な表現を避けてください。
        ・以下の#出力形式に従い、{{JSON形式}}で出力を行い、余分な説明は出力しないこと。

        #フィードバック:
        {feedback_text}

        #出力形式:
        {{
            "問題": "string", 
            "選択肢1": "string",
            "選択肢2": "string",
            "選択肢3": "string",
            "選択肢4": "string",
            "正解番号": 1~4
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            response_format={"type": "json_object"}
        )

        quiz_data = json.loads(response.choices[0].message.content)
        quiz = Quiz.objects.create(
            question=quiz_data.get("問題"),
            option_1=quiz_data.get("選択肢1"),
            option_2=quiz_data.get("選択肢2"),
            option_3=quiz_data.get("選択肢3"),
            option_4=quiz_data.get("選択肢4"),
            correct_answer=int(quiz_data.get("正解番号")),
            difficulty=difficulty,
            user = user    
        )
        request.session['quiz_ids'].append(quiz.id)

    # セッションデータを保存
    request.session.modified = True

def take_quiz(request):
    current_index = request.session.get('current_index', 0)
    quiz_ids = request.session.get('quiz_ids', [])
    iteration = request.session.get('quiz_iteration', 0)
    
    user_id = request.session.get('user_id')  # セッションからユーザーIDを取得
    user = User.objects.get(id=user_id)  # ユーザーオブジェクトを取得
    
    if current_index >= len(quiz_ids):
        request.session['quiz_iteration'] += 1  # 反復カウンターを増加
        
        # 3セット終了したときの処理
        if iteration >= 3:  # 3セット終了
            return redirect('summary')  # 終了ページへ
        
        # 次のクイズを生成
        generate_quiz_batch(request)
        request.session['current_index'] = 0 #インデックスをリセット
        
        return redirect('take_quiz')

    quiz = Quiz.objects.get(id=quiz_ids[current_index])

    # POSTリクエストの処理（回答の保存）
    if request.method == 'POST':
        selected_option = int(request.POST.get('selected_option', -1))
        is_correct = (selected_option == quiz.correct_answer)

        # 回答をデータベースに保存
        UserResponse.objects.create(
            quiz=quiz,
            user=user,
            selected_option=selected_option,
            is_correct=is_correct,
            session_id=request.session['session_id'],
        )

        # 次の問題へ進む
        request.session['current_index'] += 1
        
        # 10問終了後に自動的にdifficulty_evaluationページに移動
        if request.session['current_index'] >= 10:
            return redirect('difficulty_evaluation')
    
        # 10問経過していない場合、次の問題へ進む
        return redirect('take_quiz')

    context = {'quiz': quiz}
    return render(request, 'quiz_app/take_quiz.html', context)

def summary(request):
    return render(request, 'quiz_app/summary.html')

def quiz_list(request):
    quizzes = Quiz.objects.select_related('user').all().order_by('id')
    
    return render(request, 'quiz_app/quiz_list.html', {'quizzes': quizzes,})

def user_response_list(request):
    # UserResponseのすべてのデータを取得
    responses = UserResponse.objects.select_related('quiz').all().order_by('created_at')

    # ページにデータを渡す
    return render(request, 'quiz_app/user_response_list.html', {'responses': responses})

def difficulty_evaluation(request):
    session_id = request.session.get('session_id')
    responses = UserResponse.objects.filter(session_id=session_id, perceived_difficulty__isnull=True).annotate(
        correct_answer=F('quiz__correct_answer')
    ).order_by('id')[:10]

    if request.method == 'POST':
        difficulties = request.POST.getlist('difficulty')
        for response, difficulty in zip(responses, difficulties):
            response.perceived_difficulty = int(difficulty)
            response.save()
        return redirect('take_quiz')

    context = {'responses': responses}
    return render(request, 'quiz_app/difficulty_evaluation.html', context)

def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('username').strip()
        
        # ユーザー名が空かチェック
        if not username:
            return render(request, 'quiz_app/home.html', {'error': 'userを入力してください。'})
        
        # 同じ名前のユーザーが存在する場合のチェック
        if User.objects.filter(name=username).exists():
            return render(request, 'quiz_app/home.html', {'error': 'このuserは既に使われています。'})
        
        # 新しいユーザーを作成し、セッションに保存
        user = User.objects.create(name=username)
        request.session['user_id'] = user.id  # セッションにユーザーIDを保存
        
        return redirect('start_quiz')  # クイズ開始ページへリダイレクト
    
    # POST以外の場合は、ホームページを表示
    return render(request, 'quiz_app/home.html')