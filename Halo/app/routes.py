import os, sqlite3, secrets
from datetime import datetime
from flask import render_template,request,redirect,url_for,session,flash,current_app,abort
from werkzeug.security import check_password_hash,generate_password_hash
from .db import get_db
from .security import login_required,role_required,safe_image_save,safe_attachment_save,delete_file
from .verification import face_similarity
CATEGORIES={'sexual_harassment':('Sexual harassment','RED'),'harassment':('Harassment / intimidation','RED'),'bullying':('Bullying','RED'),'threat':('Threat / violence','RED'),'serious_mental_harassment':('Serious mental harassment','RED'),'safety':('Student safety concern','RED'),'academic_serious':('Serious academic issue','YELLOW'),'hostel':('Hostel / accommodation issue','YELLOW'),'infrastructure':('Infrastructure / maintenance','GREEN'),'academic_routine':('Routine academic issue','GREEN'),'general':('General / casual university concern','BLUE')}
STATUSES=['Submitted','Under Review','Assigned','Investigation','Action Taken','Resolved']
# Target response times: critical 24h, high 3 days, normal 7 days, minor 10 days.
SLA_HOURS={'RED':24,'YELLOW':72,'GREEN':168,'BLUE':240}

def process_overdue_cases():
    """Flag overdue open cases and notify the assigned teacher/admin once."""
    db=get_db()
    rows=db.execute("""SELECT c.id,c.complaint_code,c.severity,c.assigned_teacher_id,c.student_id
        FROM complaints c WHERE c.status!='Resolved' AND c.overdue_notified_at IS NULL
        AND ((c.severity='RED' AND datetime(c.created_at)<=datetime('now','-24 hours'))
          OR (c.severity='YELLOW' AND datetime(c.created_at)<=datetime('now','-72 hours'))
          OR (c.severity='GREEN' AND datetime(c.created_at)<=datetime('now','-168 hours'))
          OR (c.severity='BLUE' AND datetime(c.created_at)<=datetime('now','-240 hours')))""").fetchall()
    admins=db.execute("SELECT id FROM users WHERE role='admin' AND active=1").fetchall()
    for row in rows:
        code=row['complaint_code']
        db.execute('UPDATE complaints SET overdue_notified_at=CURRENT_TIMESTAMP WHERE id=?',(row['id'],))
        for admin in admins:
            db.execute('INSERT INTO notifications(user_id,complaint_id,title,message) VALUES(?,?,?,?)',(admin['id'],row['id'],'Complaint overdue',f'{code} has exceeded its {SLA_HOURS[row["severity"]]}-hour response target and needs review.'))
        if row['assigned_teacher_id']:
            db.execute('INSERT INTO notifications(user_id,complaint_id,title,message) VALUES(?,?,?,?)',(row['assigned_teacher_id'],row['id'],'Complaint overdue',f'{code} has exceeded its response target. Please update its status.'))
    db.commit(); db.close()
def audit(action,target_type=None,target_id=None):
    db=get_db()
    try:
        db.execute('INSERT INTO audit_logs(actor_id,action,target_type,target_id,ip_address) VALUES(?,?,?,?,?)',(session.get('user_id'),action,target_type,str(target_id) if target_id else None,request.remote_addr))
        db.commit()
    finally:
        db.close()
def notify(user_id, title, message, complaint_id=None):
    if not user_id:
        return
    db=get_db()
    db.execute('INSERT INTO notifications(user_id,complaint_id,title,message) VALUES(?,?,?,?)',
               (user_id, complaint_id, title, message))
    db.commit()
    db.close()

def register_routes(app,limiter):
 @app.route('/')
 def index(): return render_template('index.html')
 @app.route('/login',methods=['GET','POST'])
 @limiter.limit('10 per minute',methods=['POST'])
 def login():
    if request.method=='POST':
        u=request.form.get('username','').strip(); p=request.form.get('password',''); db=get_db(); user=db.execute('SELECT * FROM users WHERE username=? AND active=1',(u,)).fetchone(); db.close()
        if not user or not check_password_hash(user['password_hash'],p): flash('Invalid credentials.','danger'); return render_template('login.html')
        session.clear(); session.update(user_id=user['id'],role=user['role'],username=user['username'],must_change_password=bool(user['must_change_password'])); audit('LOGIN')
        return redirect(url_for('first_password_change' if user['must_change_password'] else 'dashboard'))
    return render_template('login.html')
 @app.route('/logout')
 def logout(): session.clear(); return redirect(url_for('index'))
 @app.route('/first-password-change',methods=['GET','POST'])
 @login_required
 def first_password_change():
    if not session.get('must_change_password'): return redirect(url_for('dashboard'))
    if request.method=='POST':
        p1=request.form.get('password',''); p2=request.form.get('confirm_password','')
        if len(p1)<10 or p1!=p2: flash('Passwords must match and contain at least 10 characters.','danger'); return render_template('first_password.html')
        db=get_db(); db.execute('UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?',(generate_password_hash(p1),session['user_id'])); db.commit(); db.close(); session['must_change_password']=False; audit('FIRST_PASSWORD_CHANGE','user',session['user_id']); return redirect(url_for('dashboard'))
    return render_template('first_password.html')
 @app.route('/dashboard')
 @login_required
 def dashboard(): return redirect(url_for({'student':'student_dashboard','teacher':'teacher_dashboard','admin':'admin_dashboard'}[session['role']]))
 @app.route('/student')
 @role_required('student')
 def student_dashboard():
    db=get_db(); c=db.execute('SELECT * FROM complaints WHERE student_id=? AND student_hidden=0 ORDER BY created_at DESC',(session['user_id'],)).fetchall(); db.close(); return render_template('student.html',complaints=c)
 @app.route('/student/complaint',methods=['GET','POST'])
 @role_required('student')
 def new_complaint():
    if request.method=='POST':
        db=get_db(); student=db.execute("SELECT * FROM users WHERE id=? AND role='student' AND active=1",(session['user_id'],)).fetchone(); db.close()
        category=request.form.get('category',''); desc=request.form.get('description','').strip(); dept=request.form.get('department','').strip(); year=request.form.get('year','').strip(); section=request.form.get('section','').strip()
        incident_date=request.form.get('incident_date','').strip(); incident_location=request.form.get('incident_location','').strip()
        previous_report=request.form.get('previous_report','no').strip().lower(); follow_up_details=request.form.get('follow_up_details','').strip()
        if category not in CATEGORIES or len(desc)<50 or not dept or not year or not section or not incident_date or not incident_location:
            flash('Complete every required field. Describe what happened in at least 50 characters, and include when and where it happened.','danger'); return render_template('complaint.html',categories=CATEGORIES)
        if previous_report not in ('yes','no') or (previous_report=='yes' and len(follow_up_details)<20):
            flash('If this incident was reported before, enter at least 20 characters explaining the earlier report and what happened afterward.','danger'); return render_template('complaint.html',categories=CATEGORIES)
        if not student or not student['roll_number'] or not student['original_photo']: flash('Account is not fully registered for verification. Contact admin.','danger'); return render_template('complaint.html',categories=CATEGORIES)
        temp_dir=os.path.join(current_app.config['UPLOAD_FOLDER'],'temp'); original_dir=os.path.join(current_app.config['UPLOAD_FOLDER'],'originals'); attach_dir=os.path.join(current_app.config['UPLOAD_FOLDER'],'complaints'); temp_name=None
        try:
            temp_name=safe_image_save(request.files.get('verification_photo'),temp_dir); ok,score,msg=face_similarity(os.path.join(original_dir,student['original_photo']),os.path.join(temp_dir,temp_name)); delete_file(os.path.join(temp_dir,temp_name)); temp_name=None
            if not ok: audit('PHOTO_VERIFICATION_FAILED','user',session['user_id']); flash('Photo verification failed.','danger'); return render_template('complaint.html',categories=CATEGORIES)
            attachment=safe_attachment_save(request.files.get('attachment'),attach_dir); label,severity=CATEGORIES[category]; code='CMP-'+datetime.now().strftime('%Y')+'-'+secrets.token_hex(3).upper(); db=get_db(); db.execute('INSERT INTO complaints(complaint_code,student_id,department,year,section,category,severity,description,attachment,incident_date,incident_location,previous_report,follow_up_details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(code,student['id'],dept,year,section,label,severity,desc,attachment,incident_date,incident_location,previous_report,follow_up_details if previous_report=='yes' else None)); cid=db.execute('SELECT last_insert_rowid()').fetchone()[0]; db.execute('INSERT INTO complaint_updates(complaint_id,actor_id,status,note) VALUES(?,?,?,?)',(cid,session['user_id'],'Submitted','Complaint submitted and verified.')); db.commit()
            admins=db.execute("SELECT id FROM users WHERE role='admin' AND active=1").fetchall()
            db.close()
            notify(student['id'], 'Complaint submitted', f'{code} was submitted successfully.', cid)
            for a in admins: notify(a['id'], 'New complaint submitted', f'{code} needs review.', cid)
            audit('COMPLAINT_CREATED','complaint',cid); flash(f'Complaint {code} submitted successfully.','success'); return redirect(url_for('student_dashboard'))
        except ValueError as e:
            if temp_name: delete_file(os.path.join(temp_dir,temp_name))
            flash(str(e),'danger')
        except Exception:
            if temp_name: delete_file(os.path.join(temp_dir,temp_name))
            app.logger.exception('Complaint submission failed')
            flash('The complaint could not be submitted due to a processing error. Please try again or contact the administrator.','danger')
    return render_template('complaint.html',categories=CATEGORIES)
 @app.route('/complaint/<int:cid>')
 @login_required
 def complaint_detail(cid):
    db=get_db(); c=db.execute('SELECT c.*,u.full_name student_name,u.roll_number FROM complaints c JOIN users u ON u.id=c.student_id WHERE c.id=?',(cid,)).fetchone(); updates=db.execute('SELECT cu.*,u.full_name actor_name FROM complaint_updates cu JOIN users u ON u.id=cu.actor_id WHERE complaint_id=? ORDER BY cu.created_at',(cid,)).fetchall(); db.close()
    if not c: abort(404)
    if (session.get('role')=='student' and c['student_hidden']) or (session.get('role')=='admin' and c['admin_hidden']): abort(404)
    allowed=session['role']=='admin' or (session['role']=='student' and c['student_id']==session['user_id']) or (session['role']=='teacher' and c['assigned_teacher_id']==session['user_id'] and c['severity']!='RED')
    if not allowed: abort(403)
    return render_template('complaint_detail.html',complaint=c,updates=updates)
 @app.route('/teacher')
 @role_required('teacher')
 def teacher_dashboard():
    process_overdue_cases()
    db=get_db(); c=db.execute("SELECT c.*,u.full_name student_name, CASE WHEN c.status!='Resolved' AND ((c.severity='RED' AND datetime(c.created_at)<=datetime('now','-24 hours')) OR (c.severity='YELLOW' AND datetime(c.created_at)<=datetime('now','-72 hours')) OR (c.severity='GREEN' AND datetime(c.created_at)<=datetime('now','-168 hours')) OR (c.severity='BLUE' AND datetime(c.created_at)<=datetime('now','-240 hours'))) THEN 1 ELSE 0 END AS is_overdue FROM complaints c JOIN users u ON u.id=c.student_id WHERE c.assigned_teacher_id=? AND c.severity!='RED' ORDER BY is_overdue DESC,c.created_at DESC",(session['user_id'],)).fetchall(); db.close(); return render_template('teacher.html',complaints=c)
 @app.route('/teacher/complaint/<int:cid>/update',methods=['POST'])
 @role_required('teacher')
 def teacher_update(cid):
    status=request.form.get('status'); note=request.form.get('note','').strip(); db=get_db(); c=db.execute("SELECT * FROM complaints WHERE id=? AND assigned_teacher_id=? AND severity!='RED'",(cid,session['user_id'])).fetchone()
    if not c: db.close(); abort(403)
    if status not in STATUSES or not note: db.close(); flash('Valid status and note are required.','danger'); return redirect(url_for('complaint_detail',cid=cid))
    db.execute('UPDATE complaints SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(status,cid)); db.execute('INSERT INTO complaint_updates(complaint_id,actor_id,status,note) VALUES(?,?,?,?)',(cid,session['user_id'],status,note)); db.commit()
    student_id=c['student_id']
    db.close()
    notify(student_id, 'Complaint status updated', f'{c["complaint_code"]} is now: {status}.', cid)
    audit('COMPLAINT_STATUS_UPDATED','complaint',cid); flash('Complaint updated.','success'); return redirect(url_for('complaint_detail',cid=cid))
 @app.route('/admin')
 @role_required('admin')
 def admin_dashboard():
    process_overdue_cases()
    db=get_db(); stats={r['severity']:r['n'] for r in db.execute('SELECT severity,COUNT(*) n FROM complaints GROUP BY severity')}; complaints=db.execute("SELECT c.*,u.full_name student_name,t.full_name teacher_name, CASE WHEN c.status!='Resolved' AND ((c.severity='RED' AND datetime(c.created_at)<=datetime('now','-24 hours')) OR (c.severity='YELLOW' AND datetime(c.created_at)<=datetime('now','-72 hours')) OR (c.severity='GREEN' AND datetime(c.created_at)<=datetime('now','-168 hours')) OR (c.severity='BLUE' AND datetime(c.created_at)<=datetime('now','-240 hours'))) THEN 1 ELSE 0 END AS is_overdue FROM complaints c JOIN users u ON u.id=c.student_id LEFT JOIN users t ON t.id=c.assigned_teacher_id WHERE c.admin_hidden=0 ORDER BY is_overdue DESC,CASE c.severity WHEN 'RED' THEN 1 WHEN 'YELLOW' THEN 2 WHEN 'GREEN' THEN 3 ELSE 4 END,c.created_at DESC").fetchall(); teachers=db.execute("SELECT id,username,full_name,department FROM users WHERE role='teacher' AND active=1").fetchall(); logs=db.execute('SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 50').fetchall(); db.close(); return render_template('admin.html',stats=stats,complaints=complaints,teachers=teachers,logs=logs)
 @app.route('/complaint/<int:cid>/delete',methods=['POST'])
 @login_required
 def delete_resolved_complaint(cid):
    db=get_db(); c=db.execute('SELECT * FROM complaints WHERE id=?',(cid,)).fetchone()
    if not c: db.close(); abort(404)
    role=session.get('role')
    if c['status']!='Resolved': db.close(); flash('Only resolved complaints can be removed from history.','warning'); return redirect(url_for('dashboard'))
    if role=='student' and c['student_id']==session['user_id']:
        db.execute('UPDATE complaints SET student_hidden=1 WHERE id=?',(cid,)); action='STUDENT_HID_COMPLAINT'
    elif role=='admin':
        db.execute('UPDATE complaints SET admin_hidden=1 WHERE id=?',(cid,)); action='ADMIN_HID_COMPLAINT'
    else: db.close(); abort(403)
    db.commit(); db.close(); audit(action,'complaint',cid); flash('Resolved complaint removed from your view. Audit history is retained.','success'); return redirect(url_for('dashboard'))
 @app.route('/notifications')
 @login_required
 def notifications():
    db=get_db()
    items=db.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 100',(session['user_id'],)).fetchall()
    db.execute('UPDATE notifications SET is_read=1 WHERE user_id=?',(session['user_id'],))
    db.commit(); db.close()
    return render_template('notifications.html',items=items)
 @app.route('/admin/complaint/<int:cid>/update',methods=['POST'])
 @role_required('admin')
 def admin_update_complaint(cid):
    status=request.form.get('status','')
    note=request.form.get('note','').strip()
    if status not in STATUSES or not note:
        flash('Choose a valid status and enter an update note.','danger')
        return redirect(url_for('complaint_detail',cid=cid))
    db=get_db()
    c=db.execute('SELECT * FROM complaints WHERE id=?',(cid,)).fetchone()
    if not c:
        db.close(); abort(404)
    db.execute('UPDATE complaints SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(status,cid))
    db.execute('INSERT INTO complaint_updates(complaint_id,actor_id,status,note) VALUES(?,?,?,?)',(cid,session['user_id'],status,note))
    db.commit(); student_id=c['student_id']; code=c['complaint_code']; assigned=c['assigned_teacher_id']; db.close()
    notify(student_id,'Complaint status updated',f'{code} is now: {status}.',cid)
    if assigned: notify(assigned,'Complaint status updated',f'{code} is now: {status}.',cid)
    audit('ADMIN_COMPLAINT_STATUS_UPDATED','complaint',cid)
    flash('Complaint status updated.','success')
    return redirect(url_for('complaint_detail',cid=cid))
 @app.route('/admin/users',methods=['POST'])
 @role_required('admin')
 def admin_create_user():
    role=request.form.get('role'); username=request.form.get('username','').strip(); full=request.form.get('full_name','').strip(); roll=request.form.get('roll_number','').strip() or None; dept=request.form.get('department','').strip() or None; year=request.form.get('year','').strip() or None; section=request.form.get('section','').strip() or None; temp=request.form.get('temporary_password',''); photo_name=None
    if role not in ('student','teacher') or not username or not full or len(temp)<10:
        flash('Valid role, name, username and temporary password (10+ characters) are required.','danger'); return redirect(url_for('admin_dashboard'))
    if role == 'student' and (not roll or not dept or not year or not section):
        flash('Student accounts require a unique roll number, department, year and section.','danger'); return redirect(url_for('admin_dashboard'))
    db=None
    try:
        db=get_db()
        if role=='student': photo_name=safe_image_save(request.files.get('photo'),os.path.join(current_app.config['UPLOAD_FOLDER'],'originals'))
        db.execute('INSERT INTO users(username,password_hash,role,full_name,roll_number,department,year,section,original_photo,must_change_password) VALUES(?,?,?,?,?,?,?,?,?,1)',(username,generate_password_hash(temp),role,full,roll,dept,year,section,photo_name))
        db.commit()
        db.close(); db=None
        audit('USER_CREATED','user',username)
        flash('Account created.','success')
    except (ValueError,sqlite3.IntegrityError):
        if db is not None:
            db.close()
        if photo_name: delete_file(os.path.join(current_app.config['UPLOAD_FOLDER'],'originals',photo_name))
        flash('Could not create account. Username/roll number may already exist or photo is invalid.','danger')
    return redirect(url_for('admin_dashboard'))
 @app.route('/admin/assign/<int:cid>',methods=['POST'])
 @role_required('admin')
 def admin_assign(cid):
    tid=request.form.get('teacher_id'); db=get_db(); t=db.execute("SELECT id FROM users WHERE id=? AND role='teacher' AND active=1",(tid,)).fetchone(); c=db.execute('SELECT severity FROM complaints WHERE id=?',(cid,)).fetchone()
    if not t or not c: db.close(); abort(400)
    if c['severity']=='RED': db.close(); flash('Critical red complaints use the sensitive-case workflow and are not assigned to ordinary teachers.','warning'); return redirect(url_for('admin_dashboard'))
    db.execute("UPDATE complaints SET assigned_teacher_id=?,status='Assigned',updated_at=CURRENT_TIMESTAMP WHERE id=?",(tid,cid)); db.execute('INSERT INTO complaint_updates(complaint_id,actor_id,status,note) VALUES(?,?,?,?)',(cid,session['user_id'],'Assigned','Assigned by administrator.')); db.commit()
    student_row=db.execute('SELECT student_id,assigned_teacher_id,complaint_code FROM complaints WHERE id=?',(cid,)).fetchone()
    db.close()
    notify(student_row['student_id'], 'Complaint assigned', f'{student_row["complaint_code"]} has been assigned for handling.', cid)
    notify(int(tid), 'Complaint assigned to you', f'{student_row["complaint_code"]} is now assigned to you.', cid)
    audit('COMPLAINT_ASSIGNED','complaint',cid); flash('Complaint assigned.','success'); return redirect(url_for('admin_dashboard'))
 @app.route('/admin/reset/<int:uid>',methods=['POST'])
 @role_required('admin')
 def admin_reset(uid):
    temp=request.form.get('temporary_password','');
    if len(temp)<10: flash('Temporary password must be at least 10 characters.','danger'); return redirect(url_for('admin_dashboard'))
    db=get_db(); db.execute("UPDATE users SET password_hash=?,must_change_password=1 WHERE id=? AND role!='admin'",(generate_password_hash(temp),uid)); db.commit(); db.close(); audit('PASSWORD_RESET','user',uid); flash('Password reset.','success'); return redirect(url_for('admin_dashboard'))
 @app.route('/admin/deactivate/<int:uid>',methods=['POST'])
 @role_required('admin')
 def admin_deactivate(uid):
    db=get_db(); db.execute("UPDATE users SET active=0 WHERE id=? AND role!='admin'",(uid,)); db.commit(); db.close(); audit('USER_DEACTIVATED','user',uid); flash('Account deactivated.','success'); return redirect(url_for('admin_dashboard'))
