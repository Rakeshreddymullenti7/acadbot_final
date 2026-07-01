# AcadBot 3.0 — KMEC Academic Portal
### CS (AI & ML) · 3rd Year Mini Project · KMEC

---

## 🚀 What's New in 3.0

- ✅ **3 Separate Portals** — Student, Teacher, Admin
- ✅ **Smart Attendance Calculator** — tells you exactly how many classes to attend
- ✅ **Excel/CSV Upload** — import marks and attendance from files
- ✅ **Teacher Dashboard** — view any student + class analytics + rankings
- ✅ **Admin Panel** — manage students, upload data, delete records
- ✅ **Stunning UI** — cosmic dark theme with animations

---

## 📁 Project Structure

```
acadbot3/
├── app.py                    # Flask backend — all routes + NLP
├── requirements.txt          # Python dependencies
├── schema.sql                # MySQL database (from acadbot2)
├── uploads/                  # Uploaded Excel files (auto-created)
└── templates/
    ├── index.html            # Landing page — portal selection
    ├── student.html          # Student portal — chatbot
    ├── teacher_login.html    # Teacher login
    ├── teacher.html          # Teacher dashboard
    ├── admin_login.html      # Admin login
    └── admin.html            # Admin dashboard
```

---

## ⚙️ Setup Instructions

### Step 1 — Install dependencies
```bash
pip install flask mysql-connector-python pandas openpyxl
```

### Step 2 — Import database
Use the schema.sql from acadbot2 (already imported if you ran it before):
```sql
mysql -u root -p
source D:/bot2/acadbot2_project/acadbot2/schema.sql
```

### Step 3 — Configure app.py
Open `app.py` and update:
```python
DB_CONFIG = {
    'password': 'your_mysql_password',   # ← Change this
}
TEACHER_PASSWORD = 'teacher123'   # ← Change if needed
ADMIN_PASSWORD   = 'admin123'     # ← Change if needed
```

### Step 4 — Run
```cmd
D:
cd D:\acadbot3
python app.py
```

### Step 5 — Open browser
```
http://localhost:5000
```

---

## 🎯 Portal Guide

### 🎒 Student Portal
- Enter hall ticket number to login
- Ask in natural language: *"What is my CGPA?"*
- Smart attendance calculator: *"Calculate my attendance for CS302"*

### 👨‍🏫 Teacher Portal
- Password: `teacher123`
- Search and view any student's full academic profile
- Class analytics — rankings, averages, low attendance alerts

### ⚙️ Admin Portal
- Password: `admin123`
- Upload marks Excel → columns: `roll_number, subject_code, semester, academic_year, internal_marks, external_marks`
- Upload attendance Excel → columns: `roll_number, subject_code, semester, academic_year, total_classes, attended_classes`
- Add/delete students

---

## ⚡ Smart Attendance Calculator

The calculator tells students:
- Current attendance %
- How many classes they need to attend to reach 75%
- How many classes they can safely miss

**Formula:**
```
Classes needed = (0.75 × total - attended) / 0.25
```

**Usage:**
```
"Calculate my attendance for CS302"
"How many classes do I need to attend for CS301?"
```

---

## 👨‍💻 Team
- M. Rakesh Reddy — 245523753035
- P. Sushmith Reddy — 245523753042
- M. Pavan — 245523753030

**Guide:** Dr. P. Vamsheedar Reddy, Asst. Professor, CS Dept, KMEC
