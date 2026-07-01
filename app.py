from flask import Flask, render_template, request, jsonify, session, redirect, Response
import mysql.connector
import re
import pandas as pd
import os
import math

app = Flask(__name__)
app.secret_key = 'acadbot3_secret_2025'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
DB_CONFIG = {
    'host': 'mysql-12d3b482-mrakeshreddy5944-2e40.l.aivencloud.com',
    'port': 26360,
    'user': 'avnadmin',
    # 'password':,   
    'database': 'acadbot_db',
    'ssl_ca': 'ca.pem',                  # SSL certificate required by Aiven
    'ssl_disabled': False
}

ADMIN_PASSWORD = 'admin123'

# ─────────────────────────────────────────────
# Teacher Credentials
# To add more teachers, just add a new entry:
# 'teacher name in lowercase': {'password': 'pass', 'name': 'Display Name', 'subject': 'Subject'}
# ─────────────────────────────────────────────
TEACHERS = {
    'dr. vamsheedar reddy':    {'password': 'teacher123', 'name': 'Dr. P. Vamsheedar Reddy',  'subject': 'AI & ML'},
    'dr. p. vamsheedar reddy': {'password': 'teacher123', 'name': 'Dr. P. Vamsheedar Reddy',  'subject': 'AI & ML'},
    'vamsheedar':              {'password': 'teacher123', 'name': 'Dr. P. Vamsheedar Reddy',  'subject': 'AI & ML'},
    'vamsheedar reddy':        {'password': 'teacher123', 'name': 'Dr. P. Vamsheedar Reddy',  'subject': 'AI & ML'},
    # Add more teachers below:
    # 'naresh kumar':          {'password': 'naresh123',  'name': 'Dr. P. Naresh Kumar',       'subject': 'Database Systems'},
    # 'ravi':                  {'password': 'ravi123',    'name': 'Mr. Ravi',                   'subject': 'Networks'},
}

def validate_teacher(name, password):
    key = name.strip().lower()
    # Exact match first
    if key in TEACHERS and TEACHERS[key]['password'] == password:
        return TEACHERS[key]
    # Partial match
    for k, v in TEACHERS.items():
        if (k in key or key in k) and v['password'] == password:
            return v
    return None


# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def get_student(roll):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM students WHERE roll_number=%s", (roll,))
    row = cur.fetchone(); db.close(); return row

def get_semester_results(roll, sem):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT r.subject_code, s.subject_name, s.credits,
               r.internal_marks, r.external_marks,
               r.total_marks, r.grade, r.grade_points, r.academic_year
        FROM results r JOIN subjects s ON r.subject_code=s.subject_code
        WHERE r.roll_number=%s AND r.semester=%s ORDER BY r.subject_code
    """, (roll, sem))
    rows = cur.fetchall(); db.close(); return rows

def get_all_results(roll):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT r.semester, r.subject_code, s.subject_name, s.credits,
               r.internal_marks, r.external_marks,
               r.total_marks, r.grade, r.grade_points, r.academic_year
        FROM results r JOIN subjects s ON r.subject_code=s.subject_code
        WHERE r.roll_number=%s ORDER BY r.semester, r.subject_code
    """, (roll,))
    rows = cur.fetchall(); db.close(); return rows

def get_semester_attendance(roll, sem):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT a.subject_code, s.subject_name, a.total_classes,
               a.attended_classes, a.attendance_percent, a.status, a.academic_year
        FROM attendance a JOIN subjects s ON a.subject_code=s.subject_code
        WHERE a.roll_number=%s AND a.semester=%s ORDER BY a.subject_code
    """, (roll, sem))
    rows = cur.fetchall(); db.close(); return rows

def get_all_attendance(roll):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT a.semester, a.subject_code, s.subject_name, a.total_classes,
               a.attended_classes, a.attendance_percent, a.status, a.academic_year
        FROM attendance a JOIN subjects s ON a.subject_code=s.subject_code
        WHERE a.roll_number=%s ORDER BY a.semester, a.subject_code
    """, (roll,))
    rows = cur.fetchall(); db.close(); return rows

def get_sgpa_summary(roll):
    db = get_db(); cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM sgpa_summary WHERE roll_number=%s ORDER BY semester", (roll,))
        rows = cur.fetchall()
    except:
        rows = []
    db.close(); return rows

def compute_sgpa(rows):
    t = sum(r['credits'] for r in rows)
    if not t: return 0.0
    return round(sum(r['grade_points'] * r['credits'] for r in rows) / t, 2)

def compute_cgpa(rows):
    t = sum(r['credits'] for r in rows)
    if not t: return 0.0
    return round(sum(r['grade_points'] * r['credits'] for r in rows) / t, 2)

def compute_cgpa_from_summary(sgpa_rows):
    valid = [r for r in sgpa_rows if r.get('sgpa') is not None]
    if not valid: return None
    return round(sum(r['sgpa'] for r in valid) / len(valid), 2)

def overall_att(rows):
    t = sum(r['total_classes'] for r in rows)
    a = sum(r['attended_classes'] for r in rows)
    if not t: return 0.0
    return round((a / t) * 100, 2)

def get_available_semesters(roll):
    db = get_db(); cur = db.cursor()
    sems_set = set()
    # Get from results table
    try:
        cur.execute("SELECT DISTINCT semester FROM results WHERE roll_number=%s", (roll,))
        for r in cur.fetchall():
            sems_set.add(r[0])
    except:
        pass
    # Also get from sgpa_summary (covers backlog students with no detailed results)
    try:
        cur.execute("SELECT DISTINCT semester FROM sgpa_summary WHERE roll_number=%s", (roll,))
        for r in cur.fetchall():
            sems_set.add(r[0])
    except:
        pass
    db.close()
    return sorted(sems_set)

def get_all_students():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM students ORDER BY roll_number")
    rows = cur.fetchall(); db.close(); return rows

def get_class_rankings():
    db = get_db(); cur = db.cursor(dictionary=True)
    try:
        # Use sgpa_summary for real data — include ALL students even those with backlogs
        cur.execute("""
            SELECT s.roll_number, s.name, s.branch,
                   AVG(CASE WHEN ss.sgpa IS NOT NULL THEN ss.sgpa ELSE NULL END) as cgpa,
                   SUM(CASE WHEN ss.has_backlogs=1 THEN ss.backlog_count ELSE 0 END) as total_backlogs,
                   COUNT(ss.semester) as sems_recorded
            FROM students s
            LEFT JOIN sgpa_summary ss ON s.roll_number=ss.roll_number
            GROUP BY s.roll_number, s.name, s.branch
            ORDER BY cgpa DESC
        """)
        rows = cur.fetchall()
    except:
        rows = []
    db.close(); return rows


# ─────────────────────────────────────────────
# Smart Attendance Calculator
# ─────────────────────────────────────────────
def smart_attendance_calc(attended, total):
    if total == 0:
        return {'current_percent': 0, 'attended': 0, 'total': 0,
                'classes_needed': 0, 'can_miss': 0, 'projected_percent': 0}
    current_pct = round((attended / total) * 100, 2)
    needed = 0
    can_miss = 0
    projected = current_pct
    if current_pct < 75:
        raw = (0.75 * total - attended) / 0.25
        needed = max(0, math.ceil(raw))
        projected = round(((attended + needed) / (total + needed)) * 100, 2)
    else:
        raw_miss = (attended / 0.75) - total
        can_miss = max(0, int(raw_miss))
    return {
        'current_percent': current_pct,
        'attended': attended,
        'total': total,
        'classes_needed': needed,
        'can_miss': can_miss,
        'projected_percent': projected
    }


# ─────────────────────────────────────────────
# NLP
# ─────────────────────────────────────────────
INTENTS = {
    'greeting':       [r'\b(hi|hello|hey|good morning|good afternoon|good evening)\b'],
    'help':           [r'\b(help|what can you do|commands|options)\b'],
    'get_sgpa':       [r'\b(sgpa|s\.g\.p\.a|semester gpa)\b'],
    'get_cgpa':       [r'\b(cgpa|c\.g\.p\.a|cumulative|overall gpa)\b'],
    'get_result':     [r'\b(result|results|marks|score|scores|performance)\b'],
    'get_attendance': [r'\b(attendance|present|absent|classes|percentage)\b'],
    'smart_calc':     [r'\b(calculate|calculator|how many|need to attend|can i miss|bunk)\b'],
    'get_history':    [r'\b(history|all semester|complete|full result|academic history)\b'],
    'who_am_i':       [r'\b(who am i|my profile|my info|my name)\b'],
    'farewell':       [r'\b(bye|goodbye|thanks|thank you)\b'],
}
SEM_RE = re.compile(r'\bsem(?:ester)?\s*([1-8])\b', re.IGNORECASE)
ROLL_RE = re.compile(r'\b(\d{12})\b')
SUB_RE  = re.compile(r'\b(CS\d{3}|OR\d{3}|DM\d{3}|M\d{3}|PHY\d{3}|CHE\d{3}|AI\d{3}|SE\d{3}|CN\d{3}|DBMS\d{3}|OS\d{3})\b', re.IGNORECASE)

def detect_intent(text):
    tl = text.lower()
    for intent, patterns in INTENTS.items():
        for p in patterns:
            if re.search(p, tl, re.IGNORECASE):
                return intent
    return 'unknown'

def extract_semester(text):
    m = SEM_RE.search(text)
    return int(m.group(1)) if m else None

def extract_subject(text):
    m = SUB_RE.search(text)
    return m.group(1).upper() if m else None


# ─────────────────────────────────────────────
# FIX: Lab subjects have max 50 marks (25+25)
# We need to handle grade calculation for labs correctly
# ─────────────────────────────────────────────
def fix_lab_grade(row):
    """Labs have max 50 marks. Fix F grades caused by wrong grade calculation."""
    subject_name = row.get('subject_name', '').lower()
    subject_code = row.get('subject_code', '').upper()
    total = float(row.get('total_marks', 0))

    is_lab = any(x in subject_name for x in ['lab', 'workshop', 'graphics', 'drawing'])
    if not is_lab:
        # Check by code pattern - codes ending in L are usually labs
        if subject_code.endswith('L') or 'L' in subject_code[-2:]:
            is_lab = True

    if is_lab:
        # Max marks for lab = 50, so grade based on percentage of 50
        pct = (total / 50) * 100
        if pct >= 90: grade, gp = 'O', 10
        elif pct >= 80: grade, gp = 'A+', 9
        elif pct >= 70: grade, gp = 'A', 8
        elif pct >= 60: grade, gp = 'B+', 7
        elif pct >= 50: grade, gp = 'B', 6
        elif pct >= 40: grade, gp = 'C', 5
        else: grade, gp = 'F', 0
        row = dict(row)
        row['grade'] = grade
        row['grade_points'] = gp
        row['is_lab'] = True
    return row


# ─────────────────────────────────────────────
# Response Builder
# ─────────────────────────────────────────────
def build_response(user_message, roll):
    intent   = detect_intent(user_message)
    semester = extract_semester(user_message)
    subject  = extract_subject(user_message)

    if intent == 'greeting':
        s = get_student(roll)
        return {'type': 'text', 'message': f"Hello **{s['name']}**! 👋 Ask me about your results, attendance, SGPA, or CGPA!"}

    if intent == 'help':
        return {'type': 'help', 'message': "Here's what I can do:", 'commands': [
            {'icon': '📊', 'cmd': 'Show my Semester 3 results'},
            {'icon': '🎓', 'cmd': 'What is my CGPA?'},
            {'icon': '📈', 'cmd': 'What is my SGPA for Semester 2?'},
            {'icon': '📅', 'cmd': 'Show my attendance'},
            {'icon': '⚡', 'cmd': 'Calculate my attendance for CS302'},
            {'icon': '🏆', 'cmd': 'Show my complete academic history'},
            {'icon': '👤', 'cmd': 'Who am I?'},
        ]}

    student = get_student(roll)
    if not student:
        return {'type': 'error', 'message': 'Student not found.'}

    if intent == 'who_am_i':
        sems = get_available_semesters(roll)
        return {'type': 'profile', 'student': student, 'semesters_available': sems}

    # ── CGPA ──
    if intent == 'get_cgpa':
        summary = get_sgpa_summary(roll)
        if summary:
            cgpa = compute_cgpa_from_summary(summary)
            sgpas = [{'semester': r['semester'], 'sgpa': r.get('sgpa'),
                      'has_backlogs': r.get('has_backlogs', 0),
                      'backlog_count': r.get('backlog_count', 0),
                      'status': r.get('status', 'Unknown')} for r in summary]
            return {'type': 'cgpa', 'student': student, 'cgpa': cgpa, 'sgpa_list': sgpas}
        # Fallback to results table
        rows = get_all_results(roll)
        if not rows:
            return {'type': 'error', 'message': 'No results found yet.'}
        rows = [fix_lab_grade(r) for r in rows]
        sems = sorted(set(r['semester'] for r in rows))
        sgpas = [{'semester': s, 'sgpa': compute_sgpa([r for r in rows if r['semester'] == s]),
                  'has_backlogs': False, 'backlog_count': 0, 'status': 'Clear'} for s in sems]
        return {'type': 'cgpa', 'student': student, 'cgpa': compute_cgpa(rows), 'sgpa_list': sgpas}

    # ── SGPA ──
    if intent == 'get_sgpa':
        summary = get_sgpa_summary(roll)
        if summary:
            if semester:
                sd = [r for r in summary if r['semester'] == semester]
                if not sd:
                    return {'type': 'error', 'message': f'No SGPA data for Semester {semester}.'}
                r = sd[0]
                return {'type': 'sgpa', 'student': student, 'semester': semester,
                        'sgpa': r.get('sgpa'), 'has_backlogs': r.get('has_backlogs', 0),
                        'backlog_count': r.get('backlog_count', 0)}
            sgpas = [{'semester': r['semester'], 'sgpa': r.get('sgpa'),
                      'has_backlogs': r.get('has_backlogs', 0),
                      'backlog_count': r.get('backlog_count', 0),
                      'status': r.get('status', 'Unknown')} for r in summary]
            return {'type': 'sgpa_all', 'student': student, 'sgpa_list': sgpas}
        if not semester:
            rows = get_all_results(roll)
            rows = [fix_lab_grade(r) for r in rows]
            sems = sorted(set(r['semester'] for r in rows))
            sgpas = [{'semester': s, 'sgpa': compute_sgpa([r for r in rows if r['semester'] == s]),
                      'has_backlogs': False, 'backlog_count': 0, 'status': 'Clear'} for s in sems]
            return {'type': 'sgpa_all', 'student': student, 'sgpa_list': sgpas}
        rows = get_semester_results(roll, semester)
        if not rows:
            return {'type': 'error', 'message': f'No results for Semester {semester}.'}
        rows = [fix_lab_grade(r) for r in rows]
        return {'type': 'sgpa', 'student': student, 'semester': semester,
                'sgpa': compute_sgpa(rows), 'has_backlogs': False, 'backlog_count': 0}

    # ── Results ──
    if intent == 'get_result':
        if not semester:
            sems = get_available_semesters(roll)
            return {'type': 'ask_semester', 'message': f"Which semester? Available: {', '.join('Sem '+str(s) for s in sems)}"}

        # Try results table for subject-wise marks
        rows = get_semester_results(roll, semester)
        if rows:
            rows = [fix_lab_grade(r) for r in rows]
            # FIX: Use real SGPA from sgpa_summary instead of recalculating from marks
            summary = get_sgpa_summary(roll)
            real_sgpa = None
            for r in summary:
                if r['semester'] == semester:
                    real_sgpa = r.get('sgpa')
                    break
            # Use real SGPA if available, else calculate from marks
            display_sgpa = real_sgpa if real_sgpa is not None else compute_sgpa(rows)
            return {'type': 'semester_result', 'student': student, 'semester': semester,
                    'results': rows, 'sgpa': display_sgpa}

        # If no results in results table, check sgpa_summary
        summary = get_sgpa_summary(roll)
        sem_data = [r for r in summary if r['semester'] == semester]
        if sem_data:
            s = sem_data[0]
            if s.get('has_backlogs'):
                return {
                    'type': 'text',
                    'message': f"⚠️ **Semester {semester} — Backlog Detected**\n\nSGPA data shows **{s.get('backlog_count', 0)} backlog(s)** in this semester.\n\nDetailed subject-wise marks are not available in the database for this semester. Please contact the exam cell for your mark sheet.",
                }
            else:
                return {
                    'type': 'text',
                    'message': f"📊 **Semester {semester} SGPA: {s.get('sgpa', 'N/A')}**\n\nDetailed subject-wise marks are not yet loaded in the database for this semester. Ask your admin to upload the marks Excel file.",
                }

        return {'type': 'error', 'message': f'No results found for Semester {semester}. Please check if marks have been uploaded.'}

    # ── Attendance ──
    if intent in ('get_attendance', 'smart_calc'):
        if (intent == 'smart_calc' or 'calculat' in user_message.lower() or 'how many' in user_message.lower()):
            target_sem = semester or (get_available_semesters(roll) or [None])[-1]
            if target_sem:
                att_rows = get_semester_attendance(roll, target_sem)
                if subject:
                    att_rows = [a for a in att_rows if a['subject_code'].upper() == subject.upper()]
                if att_rows:
                    a = att_rows[0]
                    calc = smart_attendance_calc(a['attended_classes'], a['total_classes'])
                    calc['subject_name'] = a['subject_name']
                    calc['subject_code'] = a['subject_code']
                    return {'type': 'smart_calc', 'calc': calc}
            return {'type': 'ask_semester', 'message': 'Please specify the subject code. E.g: *"Calculate my attendance for CS302"*'}

        if semester:
            rows = get_semester_attendance(roll, semester)
            if not rows:
                return {'type': 'error', 'message': f'No attendance for Semester {semester}.'}
            return {'type': 'attendance', 'student': student, 'semester': semester,
                    'attendance': rows, 'overall': overall_att(rows)}
        else:
            rows = get_all_attendance(roll)
            if not rows:
                return {'type': 'error', 'message': 'No attendance data found.'}
            sems = sorted(set(r['semester'] for r in rows))
            grouped = [{'semester': s, 'rows': [r for r in rows if r['semester'] == s],
                        'overall': overall_att([r for r in rows if r['semester'] == s])} for s in sems]
            return {'type': 'attendance_all', 'student': student, 'grouped': grouped,
                    'overall': overall_att(rows)}

    # ── History ──
    if intent == 'get_history':
        rows = get_all_results(roll)
        if not rows:
            return {'type': 'error', 'message': 'No results found yet.'}
        rows = [fix_lab_grade(r) for r in rows]
        # Use real SGPAs from sgpa_summary
        summary = get_sgpa_summary(roll)
        real_sgpa_map = {r['semester']: r.get('sgpa') for r in summary}
        sems = sorted(set(r['semester'] for r in rows))
        grouped = []
        for s in sems:
            sem_rows = [r for r in rows if r['semester'] == s]
            real_sgpa = real_sgpa_map.get(s)
            sgpa = real_sgpa if real_sgpa is not None else compute_sgpa(sem_rows)
            grouped.append({'semester': s, 'results': sem_rows, 'sgpa': sgpa})
        # CGPA from sgpa_summary (real data)
        cgpa = compute_cgpa_from_summary(summary) if summary else compute_cgpa(rows)
        return {'type': 'history', 'student': student, 'grouped': grouped, 'cgpa': cgpa}

    if intent == 'farewell':
        return {'type': 'text', 'message': 'Goodbye! 👋 Best of luck with your studies!'}

    return {'type': 'text',
            'message': "🤔 I didn't get that. Try:\n- *Show my Semester 3 results*\n- *What is my CGPA?*\n- *Calculate my attendance for CS302*\n\nType **help** for all commands."}


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ── Student ──
@app.route('/student/login')
def student_login():
    return render_template('student.html')

@app.route('/api/validate_student', methods=['POST'])
def validate_student():
    data = request.get_json()
    roll = data.get('roll_number', '').strip()
    student = get_student(roll)
    if student:
        session['student_roll'] = roll
        return jsonify({'valid': True, 'student': {
            'name': student['name'], 'roll_number': student['roll_number'],
            'branch': student['branch'], 'batch_year': student['batch_year']
        }})
    return jsonify({'valid': False})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    msg  = data.get('message', '').strip()
    roll = data.get('roll') or session.get('student_roll')
    if not msg or not roll:
        return jsonify({'type': 'error', 'message': 'Missing message or roll number.'})
    try:
        return jsonify(build_response(msg, roll))
    except Exception as e:
        return jsonify({'type': 'error', 'message': f'Error: {str(e)}'})

@app.route('/student/download_result', methods=['POST'])
def download_result():
    data    = request.get_json()
    roll    = data.get('roll_number', '').strip()
    student = get_student(roll)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    summary = get_sgpa_summary(roll)
    all_att = get_all_attendance(roll)
    cgpa    = compute_cgpa_from_summary(summary) if summary else 'N/A'
    rows_html = ''
    for r in summary:
        sgpa_display = r['sgpa'] if r.get('sgpa') else f"Backlogs ({r.get('backlog_count', 0)})"
        rows_html += f"<tr><td>Semester {r['semester']}</td><td>{sgpa_display}</td><td>{r.get('status','')}</td></tr>"
    html = f'''<!DOCTYPE html><html><head><style>
    body{{font-family:Arial;padding:40px;color:#333}}
    h1{{color:#6C63FF}} table{{width:100%;border-collapse:collapse;margin-top:20px}}
    th{{background:#6C63FF;color:white;padding:10px;text-align:left}}
    td{{padding:8px 10px;border-bottom:1px solid #eee}}
    .cgpa{{font-size:36px;font-weight:bold;color:#6C63FF;text-align:center;padding:20px}}
    </style></head><body>
    <h1>AcadBot — Academic Report</h1>
    <p><b>{student['name']}</b> | Roll: {student['roll_number']} | Branch: {student['branch']} | Batch: {student['batch_year']}</p>
    <p>Keshav Memorial Engineering College, Narasaraopet</p>
    <div class="cgpa">CGPA: {cgpa}</div>
    <table><thead><tr><th>Semester</th><th>SGPA</th><th>Status</th></tr></thead>
    <tbody>{rows_html}</tbody></table>
    <p style="margin-top:30px;color:#888;font-size:12px">Generated by AcadBot · KMEC</p>
    </body></html>'''
    return Response(html, mimetype='text/html',
        headers={'Content-Disposition': f'attachment;filename={roll}_result.html'})

# ── Teacher ──
@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        name = request.form.get('name', '')
        pwd  = request.form.get('password', '')
        teacher = validate_teacher(name, pwd)
        if teacher:
            session['teacher']         = True
            session['teacher_name']    = teacher['name']
            session['teacher_subject'] = teacher['subject']
            return redirect('/teacher/dashboard')
        return render_template('teacher_login.html',
                               error='Wrong name or password!', name=name)
    return render_template('teacher_login.html', error=None, name='')

@app.route('/teacher/dashboard')
def teacher_dashboard():
    if not session.get('teacher'):
        return redirect('/teacher/login')
    students = get_all_students()
    return render_template('teacher.html', students=students,
                           teacher_name=session.get('teacher_name', 'Teacher'),
                           teacher_subject=session.get('teacher_subject', ''))

@app.route('/api/teacher/student', methods=['POST'])
def teacher_get_student():
    if not session.get('teacher'):
        return jsonify({'error': 'Unauthorized'}), 401
    data    = request.get_json()
    roll    = data.get('roll_number', '').strip()
    student = get_student(roll)
    if not student:
        return jsonify({'error': 'Student not found'})
    summary  = get_sgpa_summary(roll)
    all_att  = get_all_attendance(roll)
    cgpa     = compute_cgpa_from_summary(summary) if summary else None

    if summary:
        sems = sorted(set(r['semester'] for r in summary))
        sem_data = []
        for s in sems:
            sd  = [r for r in summary if r['semester'] == s]
            sa  = [a for a in all_att if a['semester'] == s]
            sem_data.append({
                'semester': s,
                'sgpa': sd[0].get('sgpa') if sd else None,
                'has_backlogs': sd[0].get('has_backlogs', 0) if sd else 0,
                'backlog_count': sd[0].get('backlog_count', 0) if sd else 0,
                'status': sd[0].get('status', 'Unknown') if sd else 'Unknown',
                'results': [],
                'attendance': sa,
                'overall_att': overall_att(sa) if sa else 0
            })
    else:
        all_results = get_all_results(roll)
        all_results = [fix_lab_grade(r) for r in all_results]
        sems = sorted(set(r['semester'] for r in all_results))
        sem_data = []
        for s in sems:
            sr = [r for r in all_results if r['semester'] == s]
            sa = [a for a in all_att if a['semester'] == s]
            sem_data.append({'semester': s, 'sgpa': compute_sgpa(sr),
                             'has_backlogs': 0, 'backlog_count': 0, 'status': 'Clear',
                             'results': sr, 'attendance': sa,
                             'overall_att': overall_att(sa) if sa else 0})
        cgpa = compute_cgpa(all_results) if all_results else None

    return jsonify({'student': student, 'cgpa': cgpa,
                    'overall_att': overall_att(all_att), 'semesters': sem_data})

@app.route('/api/teacher/class_analytics')
def class_analytics():
    if not session.get('teacher'):
        return jsonify({'error': 'Unauthorized'}), 401
    rankings = get_class_rankings()
    data = []
    for r in rankings:
        cgpa_val = round(float(r['cgpa']), 2) if r.get('cgpa') else None
        data.append({
            'name':     r['name'],
            'roll':     r['roll_number'],
            'cgpa':     cgpa_val,
            'backlogs': int(r.get('total_backlogs') or 0)
        })
    # FIX Bug 1: Clear students first (by CGPA desc), backlog students after (by CGPA desc), no-data last
    def rank_sort(x):
        if x['cgpa'] is None:
            return (2, 0)
        if x['backlogs'] > 0:
            return (1, -(x['cgpa']))
        return (0, -(x['cgpa']))
    data.sort(key=rank_sort)
    return jsonify({'students': data})

@app.route('/teacher/logout')
def teacher_logout():
    session.pop('teacher', None)
    session.pop('teacher_name', None)
    session.pop('teacher_subject', None)
    return redirect('/teacher/login')

# ── Admin ──
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin/dashboard')
        return render_template('admin_login.html', error='Wrong password!')
    return render_template('admin_login.html', error=None)

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin/login')
    students = get_all_students()
    return render_template('admin.html', students=students, student_count=len(students))

@app.route('/admin/upload_marks', methods=['POST'])
def upload_marks():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'})
    try:
        df    = pd.read_csv(file) if file.filename.endswith('.csv') else pd.read_excel(file)
        db    = get_db(); cur = db.cursor()
        count = 0
        for _, row in df.iterrows():
            cur.execute("""INSERT INTO results
                (roll_number,subject_code,semester,academic_year,internal_marks,external_marks)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE internal_marks=%s,external_marks=%s""",
                (str(row['roll_number']), str(row['subject_code']), int(row['semester']),
                 str(row['academic_year']), float(row['internal_marks']), float(row['external_marks']),
                 float(row['internal_marks']), float(row['external_marks'])))
            count += 1
        db.commit(); db.close()
        return jsonify({'success': True, 'message': f'✅ Imported {count} records!'})
    except Exception as e:
        return jsonify({'error': f'Failed: {str(e)}'})

@app.route('/admin/upload_attendance', methods=['POST'])
def upload_attendance():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'})
    try:
        df    = pd.read_csv(file) if file.filename.endswith('.csv') else pd.read_excel(file)
        db    = get_db(); cur = db.cursor()
        count = 0
        for _, row in df.iterrows():
            cur.execute("""INSERT INTO attendance
                (roll_number,subject_code,semester,academic_year,total_classes,attended_classes)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE total_classes=%s,attended_classes=%s""",
                (str(row['roll_number']), str(row['subject_code']), int(row['semester']),
                 str(row['academic_year']), int(row['total_classes']), int(row['attended_classes']),
                 int(row['total_classes']), int(row['attended_classes'])))
            count += 1
        db.commit(); db.close()
        return jsonify({'success': True, 'message': f'✅ Imported {count} records!'})
    except Exception as e:
        return jsonify({'error': f'Failed: {str(e)}'})

@app.route('/admin/add_student', methods=['POST'])
def add_student():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    try:
        db = get_db(); cur = db.cursor()
        cur.execute("INSERT INTO students (roll_number,name,branch,batch_year,email) VALUES (%s,%s,%s,%s,%s)",
                    (data['roll_number'], data['name'], data['branch'],
                     int(data['batch_year']), data.get('email', '')))
        db.commit(); db.close()
        return jsonify({'success': True, 'message': f"✅ Student {data['name']} added!"})
    except Exception as e:
        return jsonify({'error': f'Failed: {str(e)}'})

@app.route('/admin/delete_student', methods=['POST'])
def delete_student():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    roll = request.get_json().get('roll_number')
    try:
        db = get_db(); cur = db.cursor()
        cur.execute("DELETE FROM attendance WHERE roll_number=%s", (roll,))
        cur.execute("DELETE FROM results WHERE roll_number=%s", (roll,))
        try:
            cur.execute("DELETE FROM sgpa_summary WHERE roll_number=%s", (roll,))
        except:
            pass
        cur.execute("DELETE FROM students WHERE roll_number=%s", (roll,))
        db.commit(); db.close()
        return jsonify({'success': True, 'message': f'✅ Student {roll} deleted!'})
    except Exception as e:
        return jsonify({'error': f'Failed: {str(e)}'})

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin/login')

if __name__ == '__main__':
    app.run(debug=True, port=5000)