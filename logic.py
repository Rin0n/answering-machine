import sqlite3
import speech_recognition as sr
DB_PATH = 'database.db'
FAQ = {
    1: {
        "question": "Как оформить заказ?",
        "answer": (
            "Для оформления заказа, пожалуйста, выберите интересующий вас товар "
            "и нажмите кнопку «Добавить в корзину», затем перейдите в корзину "
            "и следуйте инструкциям для завершения покупки."
        ),
    },
    2: {
        "question": "Как узнать статус моего заказа?",
        "answer": (
            "Вы можете узнать статус вашего заказа, войдя в свой аккаунт на нашем "
            "сайте и перейдя в раздел «Мои заказы». Там будет указан текущий статус."
        ),
    },
    3: {
        "question": "Как отменить заказ?",
        "answer": (
            "Если вы хотите отменить заказ, пожалуйста, свяжитесь с нашей службой "
            "поддержки как можно скорее. Мы постараемся помочь вам с отменой до отправки."
        ),
    },
    4: {
        "question": "Что делать, если товар пришёл повреждённым?",
        "answer": (
            "При получении повреждённого товара сразу свяжитесь с нашей службой "
            "поддержки и предоставьте фотографии повреждений. Мы поможем с обменом "
            "или возвратом товара."
        ),
    },
    5: {
        "question": "Как связаться с технической поддержкой?",
        "answer": (
            "Вы можете связаться с нашей технической поддержкой через номер телефона, "
            "указанный на сайте, или написать нам прямо в этот чат-бот."
        ),
    },
    6: {
        "question": "Как узнать информацию о доставке?",
        "answer": (
            "Информацию о доставке вы можете найти на странице оформления заказа. "
            "Там указаны доступные способы доставки и сроки."
        ),
    },
}
 
 
def create_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
 
    # Пользователи
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id      INTEGER PRIMARY KEY,
            name    TEXT,
            joined  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
 
    # Вопросы (справочник)
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id       INTEGER PRIMARY KEY,
            question TEXT NOT NULL
        )
    ''')
 
    # Ответы (справочник)
    c.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id          INTEGER PRIMARY KEY,
            question_id INTEGER NOT NULL,
            answer      TEXT NOT NULL,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    ''')
 
    # Лог всех обращений пользователей
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_requests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            question_id  INTEGER,              
            request_type TEXT NOT NULL,          
            raw_text     TEXT,                   
            timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)     REFERENCES users(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    ''')
 
    conn.commit()
    conn.close()
 

def fill_faq():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM questions")
    if c.fetchone()[0] > 0:
        conn.close()
        return  
 
    for qid, data in FAQ.items():
        c.execute("INSERT INTO questions (id, question) VALUES (?, ?)", (qid, data["question"]))
        c.execute("INSERT INTO answers (question_id, answer) VALUES (?, ?)", (qid, data["answer"]))
 
    conn.commit()
    conn.close()

def init_db():
    create_tables()
    fill_faq()

def add_user(user_id, name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()

def log_request(user_id: int, request_type: str, question_id: int = None, raw_text: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO user_requests (user_id, question_id, request_type, raw_text) VALUES (?, ?, ?, ?)",
        (user_id, question_id, request_type, raw_text),
    )
    conn.commit()
    conn.close()

def get_answer(question_id: int) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT answer FROM answers WHERE question_id = ?", (question_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

