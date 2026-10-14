import os, sqlite3
from flask import current_app
from werkzeug.security import generate_password_hash
SCHEMA='''
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('admin','student','teacher')), full_name TEXT NOT NULL,
 roll_number TEXT UNIQUE, department TEXT, year TEXT, section TEXT, original_photo TEXT,
 must_change_password INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS complaints (
 id INTEGER PRIMARY KEY AUTOINCREMENT, complaint_code TEXT NOT NULL UNIQUE, student_id INTEGER NOT NULL,
 department TEXT NOT NULL, year TEXT NOT NULL, section TEXT NOT NULL, category TEXT NOT NULL,
 severity TEXT NOT NULL, description TEXT NOT NULL, attachment TEXT, incident_date TEXT, incident_location TEXT, previous_report TEXT, follow_up_details TEXT, status TEXT NOT NULL DEFAULT 'Submitted',
 assigned_teacher_id INTEGER, student_hidden INTEGER NOT NULL DEFAULT 0, admin_hidden INTEGER NOT NULL DEFAULT 0, overdue_notified_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(student_id) REFERENCES users(id), FOREIGN KEY(assigned_teacher_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS complaint_updates (
 id INTEGER PRIMARY KEY AUTOINCREMENT, complaint_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
 status TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(complaint_id) REFERENCES complaints(id), FOREIGN KEY(actor_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS audit_logs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id INTEGER, action TEXT NOT NULL, target_type TEXT,
 target_id TEXT, ip_address TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(actor_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, complaint_id INTEGER,
 title TEXT NOT NULL, message TEXT NOT NULL, is_read INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(complaint_id) REFERENCES complaints(id));'''
def get_db():
    db=sqlite3.connect(current_app.config['DATABASE']); db.row_factory=sqlite3.Row; db.execute('PRAGMA foreign_keys=ON'); return db
def init_db(app):
    with app.app_context():
        db=get_db(); db.executescript(SCHEMA)
        cols={r['name'] for r in db.execute('PRAGMA table_info(complaints)')}
        if 'student_hidden' not in cols: db.execute('ALTER TABLE complaints ADD COLUMN student_hidden INTEGER NOT NULL DEFAULT 0')
        if 'admin_hidden' not in cols: db.execute('ALTER TABLE complaints ADD COLUMN admin_hidden INTEGER NOT NULL DEFAULT 0')
        # Safe additive migrations for databases created by earlier project versions.
        for name, sql_type in (('incident_date','TEXT'),('incident_location','TEXT'),('previous_report','TEXT'),('follow_up_details','TEXT'),('overdue_notified_at','TEXT')):
            if name not in cols: db.execute(f'ALTER TABLE complaints ADD COLUMN {name} {sql_type}')
        db.commit(); db.close()
def ensure_admin(app):
    with app.app_context():
        username=os.environ.get('ADMIN_USERNAME','admin'); temp=os.environ.get('ADMIN_TEMP_PASSWORD','ChangeMe_123')
        db=get_db(); row=db.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone()
        if not row:
            db.execute("INSERT INTO users(username,password_hash,role,full_name,must_change_password) VALUES(?,?,?,?,1)",(username,generate_password_hash(temp),'admin','System Administrator')); db.commit()
        db.close()
