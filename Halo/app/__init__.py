import os
from flask import Flask
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from .db import init_db, ensure_admin
from .routes import register_routes
load_dotenv()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=['200 per hour'])
def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY','dev-only-change-me'),
        DATABASE=os.environ.get('DATABASE_PATH', os.path.join(app.instance_path,'campus_complaints.sqlite3')),
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', os.path.join(app.root_path,'uploads')), MAX_CONTENT_LENGTH=16*1024*1024,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '0').lower() in ('1', 'true', 'yes'))
    # Create all upload directories on a clean install before any upload route runs.
    for folder in ('originals', 'temp', 'complaints'):
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], folder), exist_ok=True)
    csrf.init_app(app); limiter.init_app(app); init_db(app); ensure_admin(app); register_routes(app, limiter)
    @app.before_request
    def enforce_first_password_change():
        # Prevent users with temporary passwords from bypassing the one-time change screen.
        from flask import session, request, redirect, url_for
        if session.get('user_id') and session.get('must_change_password'):
            allowed = {'first_password_change', 'logout', 'static'}
            if request.endpoint not in allowed:
                return redirect(url_for('first_password_change'))

    @app.errorhandler(413)
    def too_large(e):
        from flask import flash, redirect, request
        flash('Upload is too large. Attachment max 10 MB, photo max 5 MB.','danger')
        return redirect(request.referrer or '/')

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options']='nosniff'; response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'"
        return response
    return app
