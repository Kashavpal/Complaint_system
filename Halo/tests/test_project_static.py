"""Dependency-light checks for the Campus Complaint System source tree."""
import ast
import re
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ProjectStaticTests(unittest.TestCase):
    def test_python_files_compile(self):
        files = list(ROOT.rglob('*.py'))
        self.assertGreaterEqual(len(files), 5)
        for file in files:
            ast.parse(file.read_text(encoding='utf-8'), filename=str(file))

    def test_database_schema_executes_and_has_required_tables(self):
        tree = ast.parse((ROOT/'app/db.py').read_text(encoding='utf-8'))
        schema = next(n.value.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCHEMA' for t in n.targets))
        db = sqlite3.connect(':memory:')
        db.executescript(schema)
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'users','complaints','complaint_updates','audit_logs','notifications'}.issubset(tables))
        complaint_cols = {r[1] for r in db.execute('PRAGMA table_info(complaints)')}
        self.assertTrue({'student_hidden','admin_hidden','status','severity','assigned_teacher_id','incident_date','incident_location','previous_report','follow_up_details','overdue_notified_at'}.issubset(complaint_cols))
        notification_cols = {r[1] for r in db.execute('PRAGMA table_info(notifications)')}
        self.assertTrue({'user_id','complaint_id','title','message','is_read'}.issubset(notification_cols))
        db.close()

    def test_unresolved_complaint_cap_removed_and_detail_validation_added(self):
        source = (ROOT/'app/routes.py').read_text(encoding='utf-8')
        form = (ROOT/'app/templates/complaint.html').read_text(encoding='utf-8')
        self.assertNotIn('active_count >= 2', source)
        self.assertIn('len(desc)<50', source)
        self.assertIn('incident_date', source)
        self.assertIn('incident_location', source)
        self.assertIn('previous_report', source)
        self.assertIn('minlength="50"', form)
        self.assertIn('follow_up_details', form)

    def test_overdue_case_escalation_is_configured(self):
        source = (ROOT/'app/routes.py').read_text(encoding='utf-8')
        self.assertIn('def process_overdue_cases()', source)
        self.assertIn('Complaint overdue', source)
        self.assertIn('SLA_HOURS', source)
        self.assertIn('AS is_overdue', source)
        self.assertIn('overdue_notified_at', source)

    def test_resolved_hide_is_role_scoped_and_audited(self):
        source = (ROOT/'app/routes.py').read_text(encoding='utf-8')
        self.assertIn("if c['status']!='Resolved'", source)
        self.assertIn("role=='student' and c['student_id']==session['user_id']", source)
        self.assertIn("elif role=='admin'", source)
        self.assertIn("STUDENT_HID_COMPLAINT", source)
        self.assertIn("ADMIN_HID_COMPLAINT", source)

    def test_notification_events_and_page_exist(self):
        source = (ROOT/'app/routes.py').read_text(encoding='utf-8')
        self.assertIn("@app.route('/notifications')", source)
        self.assertIn("def notify(", source)
        for event in ('Complaint submitted','New complaint submitted','Complaint assigned','Complaint status updated'):
            self.assertIn(event, source)
        self.assertTrue((ROOT/'app/templates/notifications.html').exists())

    def test_sensitive_red_cases_not_assigned_to_regular_teachers(self):
        source = (ROOT/'app/routes.py').read_text(encoding='utf-8')
        self.assertIn("if c['severity']=='RED'", source)
        self.assertIn("c['severity']!='RED'", source)
        self.assertIn("def admin_update_complaint", source)


    def test_admin_reset_defaults_and_login_password_toggle(self):
        reset_source = (ROOT/'reset_admin.py').read_text(encoding='utf-8')
        login = (ROOT/'app/templates/login.html').read_text(encoding='utf-8')
        toggle = (ROOT/'app/static/js/password-toggle.js').read_text(encoding='utf-8')
        db_source = (ROOT/'app/db.py').read_text(encoding='utf-8')
        self.assertIn('ADMIN_USERNAME = "admin"', reset_source)
        self.assertIn('ADMIN_TEMP_PASSWORD = "ChangeMe_123"', reset_source)
        self.assertIn("temp=os.environ.get('ADMIN_TEMP_PASSWORD','ChangeMe_123')", db_source)
        self.assertIn('toggle-login-password', login)
        self.assertIn('password-toggle.js', login)
        self.assertIn("field.type = reveal ? 'text' : 'password'", toggle)

    def test_csrf_and_security_headers_are_configured(self):
        source = (ROOT/'app/__init__.py').read_text(encoding='utf-8')
        self.assertIn('csrf.init_app(app)', source)
        self.assertIn('X-Content-Type-Options', source)
        self.assertIn('Content-Security-Policy', source)

if __name__ == '__main__':
    unittest.main()
