import sqlite3
import json
import uuid
from datetime import datetime

DB_PATH = "exam_system.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Table for tests
    c.execute('''CREATE TABLE IF NOT EXISTS tests (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    subject TEXT,
                    grade TEXT,
                    questions_json TEXT,
                    duration INTEGER,
                    created_at TIMESTAMP
                )''')
    
    # Table for submissions
    c.execute('''CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    test_id TEXT,
                    student_name TEXT,
                    answers_json TEXT,
                    score REAL,
                    total_questions INTEGER,
                    submitted_at TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES tests (id)
                )''')
    
    conn.commit()
    conn.close()

def save_test(title, subject, grade, questions, duration):
    test_id = str(uuid.uuid4())[:8] # Short ID for easier sharing
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO tests (id, title, subject, grade, questions_json, duration, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (test_id, title, subject, grade, json.dumps(questions), duration, datetime.now()))
    conn.commit()
    conn.close()
    return test_id

def get_test(test_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM tests WHERE id = ?", (test_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "title": row[1],
            "subject": row[2],
            "grade": row[3],
            "questions": json.loads(row[4]),
            "duration": row[5],
            "created_at": row[6]
        }
    return None

def save_submission(test_id, student_name, answers, score, total_q):
    sub_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO submissions (id, test_id, student_name, answers_json, score, total_questions, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (sub_id, test_id, student_name, json.dumps(answers), score, total_q, datetime.now()))
    conn.commit()
    conn.close()
    return sub_id

def get_submissions(test_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM submissions WHERE test_id = ? ORDER BY submitted_at DESC", (test_id,))
    rows = c.fetchall()
    conn.close()
    return [{
        "id": r[0],
        "student_name": r[2],
        "answers": json.loads(r[3]),
        "score": r[4],
        "total_q": r[5],
        "submitted_at": r[6]
    } for r in rows]

def check_existing_submission(test_id, student_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM submissions WHERE test_id = ? AND student_name = ?", (test_id, student_name))
    row = c.fetchone()
    conn.close()
    return row is not None

def update_submission_score(submission_id, new_score):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE submissions SET score = ? WHERE id = ?", (new_score, submission_id))
    conn.commit()
    conn.close()

# Initialize on import
init_db()
