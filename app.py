
import os
import random
import smtplib
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

if DATABASE_URL:
    import psycopg2

MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'duolingo_super_secret_key')


def get_db():
    if DATABASE_URL:
        ssl_arg = {} if 'sslmode=' in DATABASE_URL else {'sslmode': 'require'}
        conn = psycopg2.connect(DATABASE_URL, **ssl_arg)
        return conn, True
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'database.db')
    conn = sqlite3.connect(db_path)
    return conn, False


def init_db():
    try:
        conn, is_pg = get_db()
        c = conn.cursor()

        if is_pg:
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    age INTEGER,
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
        else:
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    age INTEGER,
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
        c.close()
        conn.close()
    except Exception as e:
        print("init_db xatosi:", e)


init_db()


def send_2fa_code(to_email: str, code: str) -> bool:
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
        msg['To'] = to_email
        msg['Subject'] = 'NexusAcademy - Tasdiqlash kodi (2FA)'

        body = (
            "Assalomu alaykum!\n\n"
            "NexusAcademy platformasiga kirish / ro'yxatdan o'tish uchun "
            f"6 xonali tasdiqlash kodingiz:\n\n{code}\n\n"
            "Agar bu so'rovni siz yubormagan bo'lsangiz, ushbu xabarga e'tibor bermang."
        )
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Mail yuborish xatosi:", e)
        return False


CURRICULUM = {
    'python': {
        'name': 'Python Dasturlash',
        'icon': '💻',
        'topics': [
            {'level': i, 'title': f"{i}-mavzu: Python asoslari va amaliyot {i}", 'questions': [
                {'q': f"Python'da {i}-mavzuga oid asosiy tushuncha qaysi?", 'options': ['Operator', 'Funksiya', 'O‘zgaruvchi', 'Barchasi to‘g‘ri'], 'answer': 3},
                {'q': f"Kodni bajarish tartibi nimaga asoslanadi {i}?", 'options': ['Ketma-ketlik', 'Tasodif', 'Xatolik', 'Cheksizlik'], 'answer': 0},
                {'q': f"Qaysi biri ma'lumot turi emas {i}?", 'options': ['int', 'str', 'loop', 'float'], 'answer': 2},
                {'q': f"print() funksiyasi vazifasi nima {i}?", 'options': ['O‘qish', 'Ekranga chiqarish', 'O‘chirish', 'Saqlash'], 'answer': 1},
                {'q': f"Matnli ma'lumot qaysi turga kiradi {i}?", 'options': ['str', 'int', 'bool', 'list'], 'answer': 0},
                {'q': f"Mantiqiy qiymat qaysi {i}?", 'options': ['True/False', '1/0', 'Yes/No', 'A va B'], 'answer': 3},
                {'q': f"Arifmetik amalni belgilang {i}?", 'options': ['+', '-', '*', 'Barchasi'], 'answer': 3},
                {'q': f"Kommentariya qanday belgilanadi {i}?", 'options': ['#', '//', '/*', '<!--'], 'answer': 0},
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


def get_current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    conn, is_pg = get_db()
    c = conn.cursor()
    ph = '%s' if is_pg else '?'
    c.execute(f'SELECT id, username, email, phone, age, xp, hearts, streak FROM users WHERE id = {ph}', (uid,))
    row = c.fetchone()
    c.close()
    conn.close()
    if not row:
        return None
    return {
        'id': row[0], 'username': row[1], 'email': row[2], 'phone': row[3],
        'age': row[4], 'xp': row[5], 'hearts': row[6], 'streak': row[7]
    }


@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')
        email = (request.form.get('email') or '').strip().lower()
        phone = (request.form.get('phone') or '').strip()

        if not email or not phone:
            flash("Gmail va telefon raqamingizni kiriting!", "error")
            return render_template('login.html', step='auth')

        conn, is_pg = get_db()
        c = conn.cursor()
        ph = '%s' if is_pg else '?'

        c.execute(f'SELECT id, username, email, phone FROM users WHERE email = {ph}', (email,))
        existing_user = c.fetchone()
        c.close()
        conn.close()

        if action == 'register':
            if existing_user:
                flash("Bu Gmail allaqachon ro'yxatdan o'tgan! Kirish bo'limidan kiring.", "error")
                return render_template('login.html', step='auth')

            code = f"{random.randint(100000, 999999)}"
            session['pending_2fa'] = {
                'mode': 'register',
                'email': email,
                'phone': phone,
                'code': code
            }
            sent = send_2fa_code(email, code)
            if sent:
                flash(f"6 xonali tasdiqlash kodi {email} manziliga yuborildi!", "success")
            else:
                flash("Gmail yuborish sozlamalari (MAIL_USERNAME / MAIL_PASSWORD) hali kiritilmagan.", "error")
            return render_template('login.html', step='verify', email=email)

        elif action == 'login':
            if not existing_user:
                flash("Bu Gmail topilmadi! Avval ro'yxatdan o'ting.", "error")
                return render_template('login.html', step='auth')

            if existing_user[3] and existing_user[3] != phone:
                flash("Bu Gmail boshqa telefon raqam bilan bog'langan!", "error")
                return render_template('login.html', step='auth')

            code = f"{random.randint(100000, 999999)}"
            session['pending_2fa'] = {
                'mode': 'login',
                'user_id': existing_user[0],
                'username': existing_user[1],
                'email': existing_user[2],
                'phone': phone,
                'code': code
            }
            sent = send_2fa_code(email, code)
            if sent:
                flash(f"6 xonali tasdiqlash kodi {email} manziliga yuborildi!", "success")
            else:
                flash("Gmail yuborish sozlamalari (MAIL_USERNAME / MAIL_PASSWORD) hali kiritilmagan.", "error")
            return render_template('login.html', step='verify', email=email)

    return render_template('login.html', step='auth')


@app.route('/verify-code', methods=['POST'])
def verify_code():
    pending = session.get('pending_2fa')
    if not pending:
        flash("Tasdiqlash muddati tugagan. Qaytadan urinib ko'ring.", "error")
        return redirect(url_for('login'))

    entered_code = (request.form.get('code') or '').strip()
    if entered_code != pending.get('code'):
        flash("Tasdiqlash kodi noto'g'ri!", "error")
        return render_template('login.html', step='verify', email=pending.get('email'))

    conn, is_pg = get_db()
    c = conn.cursor()
    ph = '%s' if is_pg else '?'

    if pending['mode'] == 'register':
        c.execute(f'SELECT id FROM users WHERE email = {ph}', (pending['email'],))
        if c.fetchone():
            c.close()
            conn.close()
            session.pop('pending_2fa', None)
            flash("Bu Gmail allaqachon ro'yxatdan o'tgan!", "error")
            return redirect(url_for('login'))

        default_username = pending['email'].split('@')[0]
        if is_pg:
            c.execute(
                f'INSERT INTO users (username, email, phone) VALUES ({ph}, {ph}, {ph}) RETURNING id',
                (default_username, pending['email'], pending['phone'])
            )
            new_id = c.fetchone()[0]
            for subj in CURRICULUM:
                c.execute(
                    f'INSERT INTO progress (user_id, subject, unlocked_level) VALUES ({ph}, {ph}, 1) ON CONFLICT DO NOTHING',
                    (new_id, subj)
                )
        else:
            c.execute(
                f'INSERT INTO users (username, email, phone) VALUES ({ph}, {ph}, {ph})',
                (default_username, pending['email'], pending['phone'])
            )
            new_id = c.lastrowid
            for subj in CURRICULUM:
                c.execute(
                    f'INSERT OR IGNORE INTO progress (user_id, subject, unlocked_level) VALUES ({ph}, {ph}, 1)',
                    (new_id, subj)
                )

        conn.commit()
        c.close()
        conn.close()
        session.pop('pending_2fa', None)
        session['user_id'] = new_id
        return redirect(url_for('dashboard'))

    user_id = pending.get('user_id')
    conn.commit()
    c.close()
    conn.close()
    session.pop('pending_2fa', None)
    session['user_id'] = user_id
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    subject = request.args.get('subject', 'python')
    if subject not in CURRICULUM:
        subject = 'python'

    conn, is_pg = get_db()
    c = conn.cursor()
    ph = '%s' if is_pg else '?'
    c.execute(f'SELECT unlocked_level FROM progress WHERE user_id = {ph} AND subject = {ph}', (user['id'], subject))
    row = c.fetchone()
    c.close()
    conn.close()

    unlocked_level = row[0] if row else 1
    return render_template(
        'dashboard.html',
        user=user,
        curriculum=CURRICULUM,
        current_subject=subject,
        unlocked_level=unlocked_level
    )


@app.route('/quiz/<subject>/<int:level>')
def quiz(subject, level):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if subject not in CURRICULUM:
        return redirect(url_for('dashboard'))

    topics = CURRICULUM[subject]['topics']
    topic = next((t for t in topics if t['level'] == level), None)
    if not topic:
        return redirect(url_for('dashboard', subject=subject))

    return render_template('quiz.html', user=user, subject=subject, topic=topic)


@app.route('/leaderboard')
def leaderboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    conn, is_pg = get_db()
    c = conn.cursor()
    c.execute('SELECT id, username, xp, streak FROM users ORDER BY xp DESC, id ASC LIMIT 20')
    rows = c.fetchall()
    c.close()
    conn.close()

    leaders = [{'id': r[0], 'username': r[1], 'xp': r[2], 'streak': r[3]} for r in rows]
    return render_template('leaderboard.html', user=user, leaders=leaders)


@app.route('/profile')
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('profile.html', user=user)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)