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

    # Table for folders
    c.execute('''CREATE TABLE IF NOT EXISTS folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    note TEXT,
                    created_at TIMESTAMP
                )''')
    
    # Table for saved questions
    c.execute('''CREATE TABLE IF NOT EXISTS saved_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_id INTEGER,
                    subject TEXT,
                    grade TEXT,
                    questions_json TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (folder_id) REFERENCES folders (id)
                )''')
    
    conn.commit()
    conn.close()

def save_test(title, subject, grade, questions, duration):
    test_id = str(uuid.uuid4())[:8]
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
            "id": row[0], "title": row[1], "subject": row[2], "grade": row[3],
            "questions": json.loads(row[4]), "duration": row[5], "created_at": row[6]
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
    return [{"id": r[0], "student_name": r[2], "answers": json.loads(r[3]), "score": r[4], "total_q": r[5], "submitted_at": r[6]} for r in rows]

def check_existing_submission(test_id, student_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM submissions WHERE test_id = ? AND student_name = ?", (test_id, student_name))
    row = c.fetchone()
    conn.close()
    return row is not None

def create_folder(name, note=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO folders (name, note, created_at) VALUES (?, ?, ?)", (name, note, datetime.now()))
    conn.commit()
    conn.close()

def get_folders():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM folders ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "note": r[2]} for r in rows]

def save_questions_to_folder(folder_id, subject, grade, questions):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO saved_questions (folder_id, subject, grade, questions_json, created_at) VALUES (?, ?, ?, ?, ?)",
              (folder_id, subject, grade, json.dumps(questions), datetime.now()))
    conn.commit()
    conn.close()

def get_questions_from_folder(folder_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT questions_json FROM saved_questions WHERE folder_id = ?", (folder_id,))
    rows = c.fetchall()
    conn.close()
    all_mc = []; all_es = []
    for r in rows:
        qs = json.loads(r[0])
        all_mc.extend(qs.get("mc", [])); all_mc.extend(qs.get("Multiple Choice", []))
        all_es.extend(qs.get("es", [])); all_es.extend(qs.get("Essay", []))
    return {"Multiple Choice": all_mc, "Essay": all_es}

def get_recent_submissions(limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT s.id, s.test_id, s.student_name, s.score, s.total_questions, s.submitted_at, t.grade, t.title, s.answers_json
                 FROM submissions s
                 JOIN tests t ON s.test_id = t.id
                 ORDER BY s.submitted_at DESC
                 LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [{
        "id": r[0], "test_id": r[1], "student_name": r[2], "score": r[3],
        "total_q": r[4], "submitted_at": r[5], "grade": r[6], "test_title": r[7], "answers": json.loads(r[8])
    } for r in rows]

def update_submission_score(submission_id, new_score):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE submissions SET score = ? WHERE id = ?", (new_score, submission_id))
    conn.commit()
    conn.close()

def delete_folder(folder_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Delete associated questions first
    c.execute("DELETE FROM saved_questions WHERE folder_id = ?", (folder_id,))
    # Delete folder
    c.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
    conn.commit()
    conn.close()

def delete_submission(submission_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
    conn.commit()
    conn.close()

init_db()
