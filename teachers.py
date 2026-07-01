# Teacher credentials — add more teachers here
TEACHERS = {
    'dr. vamsheedar reddy': {'password': 'teacher123', 'name': 'Dr. P. Vamsheedar Reddy', 'subject': 'CS Department'},
    'dr. vamsheedar':       {'password': 'teacher123', 'name': 'Dr. P. Vamsheedar Reddy', 'subject': 'CS Department'},
    'vamsheedar':           {'password': 'teacher123', 'name': 'Dr. P. Vamsheedar Reddy', 'subject': 'CS Department'},
}

def validate_teacher(name, password):
    key = name.strip().lower()
    if key in TEACHERS and TEACHERS[key]['password'] == password:
        return TEACHERS[key]
    return None
