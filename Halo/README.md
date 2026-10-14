# Campus Complaint System

Minimal university complaint system built with Python, Flask and SQLite.

## Included
- Admin, Student and Teacher roles
- Admin-created accounts and student registration photos
- One-time password change after first login
- Admin password reset without viewing existing passwords
- Student complaint creation and review
- Category-driven immutable severity: RED / YELLOW / GREEN / BLUE
- Roll-number binding + temporary photo verification
- Temporary verification image deletion after every verification attempt
- Complaint IDs and progress timeline
- Teacher assignment and status updates
- Sensitive RED complaints kept out of the ordinary teacher workflow
- CSRF protection, rate limiting, security headers, password hashing, input validation, audit log
- Responsive minimal UI

## Run
1. Python 3.11+ recommended.
2. `python -m venv .venv`
3. Activate the virtual environment.
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and change the secret and admin temporary password.
6. `python run.py`
7. Open http://127.0.0.1:5000

The SQLite database is created automatically on first run.

## Verification warning
The included OpenCV verification is an educational prototype, not production biometric authentication. A real university deployment needs a properly validated identity/biometric solution, privacy/consent review, secure storage and independent security testing.

## Updated complaint rules
- Students may submit multiple unresolved complaints; there is no two-complaint cap. Each submission requires an incident date/time, location, a description of at least 50 characters, and follow-up details of at least 20 characters when the incident was previously reported.
- After resolution, students can remove a complaint from their own history; admins can remove it from the admin view. These are soft-deletes, not physical deletion: the record and audit trail remain for accountability. Active complaints cannot be removed.


## Recent update
- Modernized interface with subtle entrance and hover animations.
- Added database-backed in-app notifications for complaint submission, assignment, and teacher status updates.
- Notifications are visible from the top navigation and mark as read when opened.
- Removes the unresolved-complaint cap and validates detailed incident information server-side.
- Flags overdue open complaints after severity-based targets (RED: 24 hours, YELLOW: 72 hours, GREEN: 7 days, BLUE: 10 days), prioritizes them in dashboards, and sends one-time notifications to admins and the assigned teacher.
- Resolved complaints can be hidden from the student's view or admin view; the underlying complaint and audit record are retained.


## Incident detail and overdue workflow
- Each complaint stores incident date/time, location, description, whether it was previously reported, and conditional follow-up details.
- Existing SQLite databases are migrated additively when the app starts; existing complaint records remain intact.
- Overdue notifications are generated when the admin or teacher dashboard is opened.

## Verification status
Static Python compilation and database-schema checks are run on the delivered project. A full Flask HTTP/runtime test requires installing the packages in `requirements.txt`; if the test environment has no package network access, runtime tests cannot be honestly reported as passed. Run `python -m unittest discover -s tests -v` after installing requirements for the included static/schema checks.

## Windows quick setup
Double-click `setup_windows.bat`. It creates a virtual environment, installs dependencies with retries, creates `.env` if missing, and starts the app. If pip reports `Temporary failure in name resolution` or `Name or service not known`, the computer cannot resolve the package index hostname; reconnect to the internet, check DNS/VPN/proxy/firewall, and rerun the script. Editing application code cannot fix a DNS/network failure.

## Reset the local administrator login

If the administrator login says “Invalid credentials”, open a terminal in this project folder and run:

```powershell
python reset_admin.py
```

Then start the app with `python run.py` and sign in using:

- Username: `admin`
- Temporary password: `ChangeMe_123`

You will be required to choose a new password after the first login. The reset command resets the existing local admin account; run it only when you intentionally need to reset admin access. The login password field includes an eye button to show or hide the password while typing.


## Deploy to a new repository
See `DEPLOYMENT.md`. This project includes a Render Blueprint (`render.yaml`) and a `Procfile`. Set a strong `ADMIN_TEMP_PASSWORD` during deployment and use persistent storage for the database and uploads.
