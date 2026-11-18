import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'duolingo_super_secret_key'

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            xp INTEGER DEFAULT 0,
            hearts INTEGER DEFAULT 5,
            streak INTEGER DEFAULT 1
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            user_id INTEGER,
            subject TEXT,
            unlocked_level INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, subject)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 4 ta fan va har birida 40 tadan mavzu (Jami 160 ta mavzu va 1600 ta test imkoniyati / 400 ta asosiy testlar)
CURRICULUM = {
    'python': {
        'name': 'Python Dasturlash',
        'icon': '💻',
        'topics': [
            {'level': i, 'title': f"{i}-mavzu: Python asoslari va amaliyot {i}", 'questions': [
                {'q': f"Python'da {i}-mavzuga oid asosiy tushuncha qaysi?", 'options': ['Operator', 'Funksiya', 'O‘zgaruvchi', 'Barchasi to‘g‘ri'], 'answer': 3},
                {'q': f"Kodni bajarish tartibi nimaga asoslanadi {i}?", 'options': ['Ketma-ketlik', tasodif := 'Tasodif', 'Xatolik', 'Cheksizlik'], 'answer': 0},
                {'q': f"Qaysi biri ma'lumot turi emas {i}?", 'options': ['int', 'str', 'loop', 'float'], 'answer': 2},
                {'q': f"print() funksiyasi vazifasi nima {i}?", 'options': ['O‘qish', 'Ekranga chiqarish', 'O‘chirish', 'Saqlash'], 'answer': 1},
                {'q': f"Matnli ma'lumot qaysi turga kiradi {i}?", 'options': ['str', 'int', 'bool', 'list'], 'answer': 0},
                {'q': f"Mantiqiy qiymat qaysi {i}?", 'options': ['True/False', '1/0', 'Yes/No', 'A va B'], 'answer': 3},
                {'q': f"arifmetik amalni belgilang {i}?", 'options': ['+', '-', '*', 'Barchasi'], 'answer': 3},
                {'q': f"kommentariya qanday belgilanadi {i}?", 'options': ['#', '//', '/*', '<!--'], 'answer': 0},
                {'q': f"input() funksiyasi nima qiladi {i}?", 'options': ['Ma’lumot kiritadi', 'Chiqaradi', 'Hisoblaydi', 'O‘chiradi'], 'answer': 0},
                {'q': f"int('125') natijasi nima {i}?", 'options': ['125 (son)', '"125" (matn)', 'Xato', 'True'], 'answer': 0}
            ]} for i in range(1, 41)
        ]
    },
    'english': {
        'name': 'Ingliz tili',
        'icon': '🇬🇧',
        'topics': [
            {'level': i, 'title': f"{i}-mavzu: Ingliz tili grammatikasi {i}", 'questions': [
                {'q': f"Ingliz tilida nechta asosiy zamon bor {i}?", 'options': ['12 ta', '16 ta', '3 ta', '4 ta'], 'answer': 2},
                {'q': f"I ___ a student ({i}-misol).", 'options': ['is', 'are', 'am', 'be'], 'answer': 2},
                {'q': f"He ___ football every day ({i}).", 'options': ['play', 'plays', 'playing', 'played'], 'answer': 1},
                {'q': f"Qaysi biri yordamchi fe'l {i}?", 'options': ['Do/Does', 'Apple', 'Run', 'Book'], 'answer': 0},
                {'q': f"They ___ from London ({i}).", 'options': ['is', 'am', 'are', 'was'], 'answer': 2},
                {'q': f"She ___ a doctor ({i}).", 'options': ['am', 'are', 'is', 'were'], 'answer': 2},
                {'q': f"Apple so'zining ma'nosi {i}?", 'options': ['Olma', 'Banan', 'Uzum', 'Nok'], 'answer': 0},
                {'q': f"Book so'zining ma'nosi {i}?", 'options': ['Qalam', 'Kitob', 'Daftar', 'Sumka'], 'answer': 1},
                {'q': f"Good morning tarjimasi {i}?", 'options': ['Xayrli kech', 'Xayrli tong', 'Salom', 'Xayr'], 'answer': 1},
                {'q': f"We ___ not like coffee ({i}).", 'options': ['does', 'do', 'is', 'has'], 'answer': 1}
            ]} for i in range(1, 41)
        ]
    },
    'math': {
        'name': 'Matematika',
        'icon': '📐',
        'topics': [
            {'level': i, 'title': f"{i}-mavzu: Matematik mantiq va misollar {i}", 'questions': [
                {'q': f"15 * 4 + {i} = ?", 'options': [str(60+i), str(70+i), str(50+i), str(65+i)], 'answer': 0},
                {'q': f"144 / 12 + {i} = ?", 'options': [str(12+i), str(14+i), str(10+i), str(15+i)], 'answer': 0},
                {'q': f"2x + {i} = 20 bo'lsa, x nechchi {i}?", 'options': [str((20-i)/2), '5', '10', '2'], 'answer': 0},
                {'q': f"Kvadratning yuzi formulasi {i}?", 'options': ['a*b', 'a^2', '4*a', '2*(a+b)'], 'answer': 1},
                {'q': f"Doiraning yuzi {i}?", 'options': ['pi*r^2', '2*pi*r', 'a^2', '4*pi'], 'answer': 0},
                {'q': f"10 ning {i}-darajasi oxiri nechta nol bilan tugaydi?", 'options': [str(i), '1', '2', '0'], 'answer': 0},
                {'q': f"Uchburchak burchaklari yig'indisi {i}?", 'options': ['180', '360', '90', '270'], 'answer': 0},
                {'q': f"Tub sonni ko'rsating {i}?", 'options': ['2', '4', '6', '9'], 'answer': 0},
                {'q': f"100 ning {i}% i nechchi {i}?", 'options': [str(i), '10', '50', '100'], 'answer': 0},
                {'q': f"81 dan kvadrat ildiz {i}?", 'options': ['9', '8', '7', '6'], 'answer': 0}
            ]} for i in range(1, 41)
        ]
    },
    'uzbek': {
        'name': "O'zbek tili",
        'icon': '🇺🇿',
        'topics': [
            {'level': i, 'title': f"{i}-mavzu: O'zbek tili va adabiyoti {i}", 'questions': [
                {'q': f"O'zbek alifbosida nechta harf bor {i}?", 'options': ['29 ta', '28 ta', '30 ta', '32 ta'], 'answer': 0},
                {'q': f"Qaysi so'z to'g'ri yozilgan {i}?", 'options': ['Xushmuomila', 'Hushmuomala', 'Xushmomila', 'Hushmomila'], 'answer': 0},
                {'q': f"Unli tovushlar soni {i}?", 'options': ['6 ta', '5 ta', '7 ta', '4 ta'], 'answer': 0},
                {'q': f"Kitob so'zining turkumi {i}?", 'options': ['Ot', 'Sifat', "Fe'l", 'Son'], 'answer': 0},
                {'q': f"Yugurmoq so'rog'i {i}?", 'options': ['Nima qilmoq?', 'Kim?', 'Qanday?', 'Nechta?'], 'answer': 0},
                {'q': f"Bosh kelishik qo'shimchasi {i}?", 'options': ['Nol (-)', '-ning', '-ni', '-da'], 'answer': 0},
                {'q': f"Sinonim so'zlarni toping {i}?", 'options': ['Chiroyli - Go‘zal', 'Katta - Kichik', 'Issiq - Sovuq', 'Oq - Qora'], 'answer': 0},
                {'q': f"Antonim so'zlarni toping {i}?", 'options': ['Tez - Sekin', 'Tez - Chaqqon', 'Katta - Ulkan', 'Chiroyli - Ko‘rkam'], 'answer': 0},
                {'q': f"Fe'l zamonlari nechta {i}?", 'options': ['3 ta', '2 ta', '4 ta', '5 ta'], 'answer': 0},
                {'q': f"Qaratqich kelishigi qo'shimchasi {i}?", 'options': ['-ning', '-ni', '-ga', '-dan'], 'answer': 0}
            ]} for i in range(1, 41)
        ]
    }
}

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username').strip()
        password = request.form.get('password')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        if action == 'register':
            hashed_pw = generate_password_hash(password)
            try:
                c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_pw))
                conn.commit()
                flash("Muvaffaqiyatli ro'yxatdan o'tdingiz! Endi tizimga kiring.", "success")
            except sqlite3.IntegrityError:
                flash("Bu login band! Boshqa nom tanlang.", "error")
        elif action == 'login':
            c.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
            user = c.fetchone()
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                conn.close()
                return redirect(url_for('dashboard'))
            else:
                flash("Login yoki parol noto'g'ri!", "error")
        conn.close()

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT xp, hearts, streak FROM users WHERE id = ?', (session['user_id'],))
    user_data = c.fetchone()
    
    unlocked = {}
    for sub_id in CURRICULUM.keys():
        c.execute('SELECT unlocked_level FROM progress WHERE user_id = ? AND subject = ?', (session['user_id'], sub_id))
        row = c.fetchone()
        if not row:
            c.execute('INSERT INTO progress (user_id, subject, unlocked_level) VALUES (?, ?, 1)', (session['user_id'], sub_id))
            unlocked[sub_id] = 1
        else:
            unlocked[sub_id] = row[0]
    conn.commit()
    conn.close()

    user = {'username': session['username'], 'xp': user_data[0], 'hearts': user_data[1], 'streak': user_data[2]}
    return render_template('dashboard.html', user=user, curriculum=CURRICULUM, unlocked=unlocked)

@app.route('/quiz/<subject>/<int:level>')
def quiz(subject, level):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if subject not in CURRICULUM:
        return redirect(url_for('dashboard'))

    topics = CURRICULUM[subject]['topics']
    topic = next((t for t in topics if t['level'] == level), None)
    if not topic:
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT hearts FROM users WHERE id = ?', (session['user_id'],))
    hearts = c.fetchone()[0]
    conn.close()

    if hearts <= 0:
        hearts = 5

    return render_template('quiz.html', subject=subject, subject_name=CURRICULUM[subject]['name'], topic=topic, hearts=hearts)

@app.route('/api/complete_quiz', methods=['POST'])
def complete_quiz():
    if 'user_id' not in session:
        return jsonify({'status': 'error'}), 401

    data = request.json
    subject = data.get('subject')
    level = int(data.get('level'))
    earned_xp = int(data.get('xp', 0))
    hearts_left = int(data.get('hearts', 5))
    passed = data.get('passed', False)

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET xp = xp + ?, hearts = ? WHERE id = ?', (earned_xp, max(1, hearts_left), session['user_id']))
    
    if passed:
        c.execute('SELECT unlocked_level FROM progress WHERE user_id = ? AND subject = ?', (session['user_id'], subject))
        curr_level = c.fetchone()[0]
        if level >= curr_level:
            c.execute('UPDATE progress SET unlocked_level = ? WHERE user_id = ? AND subject = ?', (level + 1, session['user_id'], subject))

    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 4-OYNA: Reyting jadvali (Leaderboard)
@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT username, xp, streak FROM users ORDER BY xp DESC LIMIT 10')
    top_users = c.fetchall()

    c.execute('SELECT username, xp, hearts, streak FROM users WHERE id = ?', (session['user_id'],))
    user_data = c.fetchone()
    conn.close()

    user = {'username': user_data[0], 'xp': user_data[1], 'hearts': user_data[2], 'streak': user_data[3]}
    return render_template('leaderboard.html', user=user, top_users=top_users)

# 5-OYNA: Shaxsiy profil (Profile)
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT username, xp, hearts, streak FROM users WHERE id = ?', (session['user_id'],))
    user_data = c.fetchone()
    
    c.execute('SELECT SUM(unlocked_level - 1) FROM progress WHERE user_id = ?', (session['user_id'],))
    completed_row = c.fetchone()
    completed_topics = completed_row[0] if completed_row and completed_row[0] else 0
    conn.close()

    user = {
        'username': user_data[0],
        'xp': user_data[1],
        'hearts': user_data[2],
        'streak': user_data[3],
        'completed_topics': completed_topics
    }
    return render_template('profile.html', user=user)
    import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
