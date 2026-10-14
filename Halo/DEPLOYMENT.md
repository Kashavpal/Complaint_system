# Deployment guide (new GitHub repository)

## Before uploading
1. Extract this ZIP. The files are at the project root (there is no extra enclosing project folder).
2. Create a **new, empty** GitHub repository.
3. Upload/commit all extracted project files and folders to the repository root. Keep `.gitignore`; do not upload `.env`, local databases, student photos, or complaint uploads.

## Deploy to Render
This project includes `render.yaml` and a `Procfile`. The Render blueprint config uses a persistent disk for SQLite and uploaded files; a persistent disk may incur a paid-plan charge.

1. In Render, choose **New → Blueprint** and connect the new GitHub repository.
2. When prompted, set `ADMIN_TEMP_PASSWORD` to a strong, unique temporary password. Do not leave it blank or use the sample password. Render generates `SECRET_KEY` automatically.
3. Deploy. The start command is `gunicorn run:app --bind 0.0.0.0:$PORT`.
4. Open the service URL and sign in as username `admin` with the temporary password you configured. Change the password when prompted.
5. Create student and teacher accounts from the admin interface.

## Other hosting providers
Use Python 3.11 or newer, install dependencies with `pip install -r requirements.txt`, set a strong random `SECRET_KEY`, set a unique `ADMIN_TEMP_PASSWORD`, and start with `gunicorn run:app --bind 0.0.0.0:$PORT` (adapt `$PORT` to your host's required port syntax). Set `COOKIE_SECURE=1` when served over HTTPS.

**Persistence warning:** SQLite and uploaded photos/attachments must be stored on a persistent disk/volume. If the host has an ephemeral filesystem, data can disappear after redeploy/restart. Configure `DATABASE_PATH` and `UPLOAD_FOLDER` to locations on that persistent volume. Do not deploy real student records until you have verified backups, access controls, consent/privacy requirements, and the host's data-retention policy.

## Run locally on Windows
1. Install Python 3.11+.
2. Copy `.env.example` to `.env` and change the secret and temporary admin password.
3. Run `setup_windows.bat`, or manually run `python -m venv .venv`, activate it, `pip install -r requirements.txt`, and `python run.py`.
4. Open `http://127.0.0.1:5000`.

## Checks
Run `python -m unittest discover -s tests -v` after installing requirements. The included tests are static/schema checks; they do not replace an end-to-end test of login, uploads, notifications, and deployment. The identity/photo verification feature is an educational prototype and is not production-grade biometric authentication.
