
from flask import Flask, request, redirect, render_template_string, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os
import secrets

app = Flask(__name__)
if not os.path.exists(".secret_key"):
    with open(".secret_key", "w") as f:
        f.write(secrets.token_hex(32))
with open(".secret_key") as f:
    app.secret_key = f.read().strip()

DB = "hospital.db"
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = str(user_id)
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM users WHERE id=? AND active=1", (user_id,)).fetchone()
    return User(row["id"], row["username"], row["role"]) if row else None

LOGIN_PAGE = """<!doctype html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hospital Login</title><style>
body{font-family:Arial;background:#edf3f7;padding:24px}
.card{background:white;padding:22px;border-radius:12px;max-width:400px;margin:40px auto}
input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0}
button{background:#087f8c;color:white;border:0;border-radius:6px}
</style></head><body>
<style>
.erp-logo-download {
position:fixed;top:12px;right:12px;z-index:99999;
background:#087f8c;color:white;padding:11px 15px;
border-radius:8px;text-decoration:none;
font-weight:bold;font-family:Arial,sans-serif;
box-shadow:0 2px 8px #0003;
}
</style>
<a class="erp-logo-download"
href="/static/hospital-erp-logo.svg"
download="hospital-erp-logo.svg">⬇ Download Logo</a>
<div class="card">
<h2>Hospital Management</h2><h3>Staff Login</h3>
<form method="post"><label>Username</label><input name="username" required>
<label>Password</label><input name="password" type="password" required>
<button type="submit">Login</button></form>
{% if error %}<p>{{ error }}</p>{% endif %}
</div></body></html>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    error = ""
    if request.method == "POST":
        with sqlite3.connect(DB) as con:
            con.row_factory = sqlite3.Row
            user = con.execute("SELECT * FROM users WHERE username=? AND active=1",
                               (request.form.get("username", "").strip(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            login_user(User(user["id"], user["username"], user["role"]))
            return redirect("/")
        error = "Invalid username or password"
    return render_template_string(LOGIN_PAGE, error=error)

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect("/login")

def connect_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                phone TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS cms_pages (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT ''
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS nurses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                phone TEXT NOT NULL,
                qualification TEXT DEFAULT '',
                department TEXT DEFAULT '',
                shift TEXT DEFAULT ''
            )
        """)



        con.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('Income','Expense')),
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                amount REAL NOT NULL CHECK(amount > 0),
                transaction_date TEXT NOT NULL
            )
        """)

PAGE = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hospital Management</title>
<style>
body {font-family:Arial;background:#edf3f7;margin:0;padding:18px}
main {max-width:800px;margin:auto}
h1 {color:#087f8c}
.card {background:white;padding:18px;border-radius:12px;margin:16px 0}
input,select,button {box-sizing:border-box;width:100%;padding:12px;margin:7px 0}
button,.btn {background:#087f8c;color:white;border:0;border-radius:6px;padding:11px;text-decoration:none;display:inline-block}
.danger {background:#b42318}
.patient {padding:14px 0;border-bottom:1px solid #ddd}
.actions {display:flex;gap:8px;flex-wrap:wrap}
.actions a,.actions button {width:auto}
</style>
</head>
<body>
<!-- HMS SIDEBAR -->
<style>
.menu-toggle{position:fixed;top:12px;left:12px;z-index:1002;background:#087f8c;color:white;border:0;border-radius:8px;padding:12px;font-size:20px;width:auto}
.sidebar{position:fixed;top:0;left:-280px;width:250px;height:100%;overflow-y:auto;background:#123b46;color:white;padding:65px 15px 20px;box-sizing:border-box;z-index:1001;transition:left .25s}
.sidebar.open{left:0}
.sidebar a{display:block;color:white;text-decoration:none;padding:13px;margin:5px 0;border-radius:7px;background:#205763}
.sidebar a:hover{background:#087f8c}
.menu-overlay{display:none;position:fixed;inset:0;background:#0008;z-index:1000}
.menu-overlay.open{display:block}
@media(min-width:900px){body.menu-open main{margin-left:270px}}
</style>
<button class="menu-toggle" onclick="toggleMenu()" aria-label="Toggle sidebar">☰</button>
<div class="menu-overlay" id="menuOverlay" onclick="toggleMenu()"></div>
<nav class="sidebar" id="sidebar">
<h2>🏥 Hospital Menu</h2>
<a href="/">👤 Patients</a>
<a href="/ambulance">🚑 Ambulance</a><a href="/nurses">👩‍⚕️ Nurse Management</a>
<a href="/pharmacy">💊 Pharmacy</a><a href="/accounts">💰 Accounts</a>
<a href="/exam-reports">🧪 Exam Reports</a>
<a href="/billing">🧾 Billing / PDF</a>
<a href="/users">👥 Users</a>
<a href="/admin">🛡️ Admin</a>
<a href="/settings">⚙️ Settings</a>
<a href="/admin/users">👥 User Management</a>
<a href="/front-cms">🌐 Front CMS</a>
<a href="/login">🔐 Login</a>
<form method="post" action="/logout" style="margin-top:10px">
<button type="submit" style="width:100%;padding:13px;background:#b42318;color:white;border:0;border-radius:7px">🚪 Logout</button>
</form>
</nav>
<script>
function toggleMenu(){
 document.getElementById('sidebar').classList.toggle('open');
 document.getElementById('menuOverlay').classList.toggle('open');
}
</script>
<main>
<div style="text-align:center; margin:20px auto; padding:20px; background:#ffffff; border-radius:12px; max-width:900px; box-shadow:0 2px 8px #0001;">
<img src="/static/hospital-erp-logo.png"
     alt="Hospital ERP Logo"
     style="width:280px;max-width:90%;height:auto;display:block;margin:0 auto 12px;">
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;max-width:900px;margin:20px auto;">
<div style="background:#e7f5f5;padding:18px;border-radius:12px;text-align:center;"><div>👤 Total Patients</div><strong style="font-size:28px;color:#087f8c;">{{ total_patients }}</strong></div>
<div style="background:#edf1ff;padding:18px;border-radius:12px;text-align:center;"><div>👨‍⚕️ Total Doctors</div><strong style="font-size:28px;color:#334e9b;">{{ total_doctors }}</strong></div>
<div style="background:#fff4df;padding:18px;border-radius:12px;text-align:center;"><div>📅 Appointments</div><strong style="font-size:28px;color:#a56b00;">{{ total_appointments }}</strong></div>
<div style="background:#e9f7ed;padding:18px;border-radius:12px;text-align:center;"><div>💰 Income</div><strong style="font-size:28px;color:#218044;">{{ "%.2f"|format(total_income) }}</strong></div>
<div style="background:#fff0ed;padding:18px;border-radius:12px;text-align:center;"><div>💸 Expense</div><strong style="font-size:28px;color:#b42318;">{{ "%.2f"|format(total_expense) }}</strong></div>
<div style="background:#e7f5f5;padding:18px;border-radius:12px;text-align:center;"><div>📊 Profit</div><strong style="font-size:28px;color:#087f8c;">{{ "%.2f"|format(total_profit) }}</strong></div>
</div>
<h1 style="margin:0 0 14px; color:#087f8c; font-size:36px; font-weight:800; text-align:center; letter-spacing:0.5px;">🏥 Hospital ERP</h1>
<p style="margin:0 0 14px; color:#52616b;">Patient Management Dashboard</p>
<p style="margin:5px 0;"><strong>CEO:</strong> Md. Mizanur Rahman.</p>
<p style="margin:5px 0;"><strong>Mail:</strong> <a href="mailto:efite.com.bd@gmail.com">efite.com.bd@gmail.com</a></p>
<nav style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin:12px auto 20px;max-width:900px;background:#087f8c;padding:12px;border-radius:10px;">
<a style="color:white;text-decoration:none;padding:8px 10px" href="/">Home</a>
<a style="color:white;text-decoration:none;padding:8px 10px" href="/about">About Hospital</a>
<a style="color:white;text-decoration:none;padding:8px 10px" href="/services">Services</a>
<a style="color:white;text-decoration:none;padding:8px 10px" href="/doctors">Doctors</a>
<a style="color:white;text-decoration:none;padding:8px 10px" href="/departments">Departments</a>
<a style="color:white;text-decoration:none;padding:8px 10px" href="/notices">Notice / News</a>
<a style="color:white;text-decoration:none;padding:8px 10px" href="/contact">Contact</a>
<a style="color:white;text-decoration:none;padding:8px 10px" href="/cms">Front CMS</a>
</nav>

</div>

<div class="card">
<h2>Total Patients: {{ patients|length }}</h2>
<h3>{{ 'Edit Patient' if editing else 'Register Patient' }}</h3>
<form method="post" action="{{ '/edit/' ~ editing['id'] if editing else '/add' }}">
<label>Full name</label>
<input name="name" maxlength="100" required value="{{ editing['name'] if editing else '' }}">
<label>Age</label>
<input name="age" type="number" min="0" max="130" required value="{{ editing['age'] if editing else '' }}">
<label>Gender</label>
<select name="gender" required>
<option value="">Select gender</option>
{% for g in ['Male','Female','Other'] %}
<option value="{{ g }}" {% if editing and editing['gender']==g %}selected{% endif %}>{{ g }}</option>
{% endfor %}
</select>
<label>Phone</label>
<input name="phone" maxlength="20" required value="{{ editing['phone'] if editing else '' }}">
<button type="submit">{{ 'Save Changes' if editing else 'Register Patient' }}</button>
{% if editing %}<a class="btn" href="/">Cancel</a>{% endif %}
</form>
</div>

<div class="card">
<h2>Patient Records</h2>
<form method="get" action="/">
<input name="q" placeholder="Search name, ID or phone" value="{{ q }}">
<button type="submit">Search Patients</button>
</form>
{% for p in patients %}
<div class="patient">
<strong>{{ p['name'] }}</strong><br>
Patient ID: {{ p['id'] }}<br>
Age: {{ p['age'] }} | Gender: {{ p['gender'] }}<br>
Phone: {{ p['phone'] }}
<div class="actions">
<a class="btn" href="/edit/{{ p['id'] }}">Edit</a>
<form method="post" action="/delete/{{ p['id'] }}"
onsubmit="return confirm('Delete this patient record?')">
<button class="danger" type="submit">Delete</button>
</form>
</div>
</div>
{% else %}
<p>No matching patients found.</p>
{% endfor %}
</div>
</main>
</body>
</html>
"""

@app.route("/")
@login_required
def home():
    q = request.args.get("q", "").strip()

    with connect_db() as con:
        if q.isdigit():
            patients = con.execute(
                """SELECT * FROM patients
                WHERE name LIKE ? OR phone LIKE ? OR id = ?
                ORDER BY id DESC""",
                (f"%{q}%", f"%{q}%", int(q))
            ).fetchall()
        else:
            patients = con.execute(
                """SELECT * FROM patients
                WHERE name LIKE ? OR phone LIKE ?
                ORDER BY id DESC""",
                (f"%{q}%", f"%{q}%")
            ).fetchall()

        stats = con.execute(
            """SELECT
                (SELECT COUNT(*) FROM patients),
                (SELECT COALESCE(SUM(paid), 0) FROM bills),
                (SELECT COALESCE(SUM(amount), 0) FROM accounts WHERE transaction_type='Income'),
                (SELECT COALESCE(SUM(amount), 0) FROM accounts WHERE transaction_type='Expense')
            """
        ).fetchone()

        total_patients, bill_revenue, extra_income, total_expense = stats
        total_income = float(bill_revenue or 0) + float(extra_income or 0)
        total_profit = total_income - float(total_expense or 0)
        total_revenue = total_income

    return render_template_string(
        PAGE, patients=patients, q=q, editing=None,
        total_patients=total_patients,
        total_doctors=0,
        total_appointments=0,
        total_revenue=total_revenue,
        total_income=total_income,
        total_expense=total_expense,
        total_profit=total_profit
    )

@app.route("/add", methods=["POST"])
@login_required
def add_patient():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", type=int)
    gender = request.form.get("gender", "")
    phone = request.form.get("phone", "").strip()

    if (not name or age is None or not 0 <= age <= 130
        or gender not in ("Male", "Female", "Other")
        or not phone or len(phone) > 20):
        return "Invalid patient details", 400

    with connect_db() as con:
        con.execute(
            """INSERT INTO patients (name, age, gender, phone)
            VALUES (?, ?, ?, ?)""",
            (name, age, gender, phone)
        )
    return redirect("/")

@app.route("/edit/<int:patient_id>")
@login_required
def edit_page(patient_id):
    with connect_db() as con:
        patient = con.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        patients = con.execute(
            "SELECT * FROM patients ORDER BY id DESC"
        ).fetchall()
    if patient is None:
        return "Patient not found", 404
    return render_template_string(
        PAGE, patients=patients, q="", editing=patient
    )

@app.route("/edit/<int:patient_id>", methods=["POST"])
@login_required
def edit_patient(patient_id):
    name = request.form.get("name", "").strip()
    age = request.form.get("age", type=int)
    gender = request.form.get("gender", "")
    phone = request.form.get("phone", "").strip()

    if (not name or age is None or not 0 <= age <= 130
        or gender not in ("Male", "Female", "Other")
        or not phone or len(phone) > 20):
        return "Invalid patient details", 400

    with connect_db() as con:
        con.execute(
            """UPDATE patients SET name=?, age=?, gender=?, phone=?
            WHERE id=?""",
            (name, age, gender, phone, patient_id)
        )
    return redirect("/")

@app.route("/delete/<int:patient_id>", methods=["POST"])
@login_required
def delete_patient(patient_id):
    with connect_db() as con:
        con.execute("DELETE FROM patients WHERE id=?", (patient_id,))
    return redirect("/")




@app.route("/ambulance", methods=["GET", "POST"])
@login_required
def ambulance_page():
    with connect_db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS ambulances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_no TEXT NOT NULL,
            driver_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available'
        )""")
        if request.method == "POST":
            vehicle_no = request.form.get("vehicle_no", "").strip()
            driver_name = request.form.get("driver_name", "").strip()
            phone = request.form.get("phone", "").strip()
            status = request.form.get("status", "Available")
            if vehicle_no and driver_name and phone and status in ("Available", "On Trip", "Maintenance"):
                con.execute("INSERT INTO ambulances (vehicle_no, driver_name, phone, status) VALUES (?, ?, ?, ?)",
                            (vehicle_no, driver_name, phone, status))
            return redirect("/ambulance")
        rows = con.execute("SELECT * FROM ambulances ORDER BY id DESC").fetchall()
    return render_template_string("""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Ambulance Management</title>
    <style>body{font-family:Arial;background:#edf3f7;padding:20px}
    .card{background:white;padding:18px;border-radius:12px;margin:15px auto;max-width:650px}
    input,select,button{box-sizing:border-box;width:100%;padding:12px;margin:7px 0}
    button{background:#087f8c;color:white;border:0;border-radius:6px}
    a{color:#087f8c}</style></head><body>
    <div class="card"><a href="/">← Dashboard</a><h1>🚑 Ambulance Management</h1>
    <form method="post"><label>Vehicle number</label><input name="vehicle_no" required>
    <label>Driver name</label><input name="driver_name" required>
    <label>Phone</label><input name="phone" required>
    <label>Status</label><select name="status"><option>Available</option><option>On Trip</option><option>Maintenance</option></select>
    <button type="submit">Add Ambulance</button></form></div>
    <div class="card"><h2>Ambulance Records ({{ rows|length }})</h2>
    {% for a in rows %}<p><b>{{ a['vehicle_no'] }}</b><br>Driver: {{ a['driver_name'] }}<br>
    Phone: {{ a['phone'] }}<br>Status: {{ a['status'] }}</p>
    <a href="/ambulance/edit/{{ a['id'] }}">Edit</a>
    <form method="post" action="/ambulance/delete/{{ a['id'] }}" onsubmit="return confirm('Delete this ambulance record?')">
    <button type="submit">Delete</button></form><hr>
    {% else %}<p>No ambulance records yet.</p>{% endfor %}</div></body></html>
    """, rows=rows)




@app.route("/nurses", methods=["GET", "POST"])
@login_required
def nurses_page():
    with connect_db() as con:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            age = request.form.get("age", "").strip()
            gender = request.form.get("gender", "").strip()
            phone = request.form.get("phone", "").strip()
            qualification = request.form.get("qualification", "").strip()
            department = request.form.get("department", "").strip()
            shift = request.form.get("shift", "").strip()

            if name and age.isdigit() and int(age) >= 18 and gender and phone:
                con.execute("""
                    INSERT INTO nurses
                    (name, age, gender, phone, qualification, department, shift)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, int(age), gender, phone, qualification, department, shift))
                return redirect("/nurses")

        rows = con.execute("SELECT * FROM nurses ORDER BY id DESC").fetchall()

    return render_template_string("""
    <!doctype html>
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Nurse Management</title>
    <style>
    body{font-family:Arial;background:#edf3f7;padding:18px}
    .card{background:white;padding:18px;border-radius:12px;margin-bottom:18px;overflow-x:auto}
    input,select{width:100%;padding:11px;margin:7px 0;box-sizing:border-box}
    button{background:#087f5b;color:white;padding:12px;border:0;border-radius:7px;cursor:pointer}
    .delete{background:#c62828}
    .edit{background:#087f8c;color:white;padding:8px 12px;border-radius:6px;text-decoration:none}
    table{width:100%;border-collapse:collapse;min-width:700px}
    th,td{padding:9px;border-bottom:1px solid #ddd;text-align:left}
    </style></head><body>
    <div class="card">
    <a href="/">← Dashboard</a>
    <h1>👩‍⚕️ Nurse Management</h1>
    <h2>Register Nurse</h2>
    <form method="POST">
    <input name="name" placeholder="Nurse full name" required>
    <input name="age" type="number" min="18" placeholder="Age" required>
    <select name="gender" required>
    <option value="">Select gender</option>
    <option>Male</option><option>Female</option><option>Other</option>
    </select>
    <input name="phone" placeholder="Phone number" required>
    <input name="qualification" placeholder="Qualification">
    <input name="department" placeholder="Department">
    <select name="shift">
    <option value="">Select shift</option>
    <option>Morning</option><option>Evening</option><option>Night</option>
    </select>
    <button type="submit">Save Nurse</button>
    </form></div>

    <div class="card">
    <h2>Registered Nurses ({{ rows|length }})</h2>
    <table>
    <tr><th>Name</th><th>Age</th><th>Gender</th><th>Phone</th>
    <th>Qualification</th><th>Department</th><th>Shift</th><th>Actions</th></tr>
    {% for n in rows %}
    <tr>
    <td>{{ n['name'] }}</td><td>{{ n['age'] }}</td>
    <td>{{ n['gender'] }}</td><td>{{ n['phone'] }}</td>
    <td>{{ n['qualification'] }}</td><td>{{ n['department'] }}</td>
    <td>{{ n['shift'] }}</td>
    <td>
    <a class="edit" href="/nurses/edit/{{ n['id'] }}">Edit</a>
    <form method="POST" action="/nurses/delete/{{ n['id'] }}"
    onsubmit="return confirm('Are you sure you want to delete this nurse?')">
    <button class="delete" type="submit">Delete</button>
    </form>
    </td></tr>
    {% else %}
    <tr><td colspan="8">No nurses registered yet.</td></tr>
    {% endfor %}
    </table></div></body></html>
    """, rows=rows)


@app.route("/nurses/edit/<int:nurse_id>", methods=["GET", "POST"])
@login_required
def edit_nurse(nurse_id):
    with connect_db() as con:
        nurse = con.execute(
            "SELECT * FROM nurses WHERE id = ?", (nurse_id,)
        ).fetchone()

        if nurse is None:
            return "Nurse not found", 404

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            age = request.form.get("age", "").strip()
            gender = request.form.get("gender", "").strip()
            phone = request.form.get("phone", "").strip()
            qualification = request.form.get("qualification", "").strip()
            department = request.form.get("department", "").strip()
            shift = request.form.get("shift", "").strip()

            if name and age.isdigit() and int(age) >= 18 and gender and phone:
                con.execute("""
                    UPDATE nurses SET
                    name = ?, age = ?, gender = ?, phone = ?,
                    qualification = ?, department = ?, shift = ?
                    WHERE id = ?
                """, (name, int(age), gender, phone, qualification,
                      department, shift, nurse_id))
                return redirect("/nurses")

    return render_template_string("""
    <!doctype html>
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Edit Nurse</title>
    <style>
    body{font-family:Arial;background:#edf3f7;padding:18px}
    .card{background:white;padding:18px;border-radius:12px;max-width:600px;margin:auto}
    input,select{width:100%;padding:11px;margin:7px 0;box-sizing:border-box}
    button{background:#087f5b;color:white;padding:12px;border:0;border-radius:7px}
    </style></head><body>
    <div class="card">
    <a href="/nurses">← Back to Nurses</a>
    <h1>Edit Nurse</h1>
    <form method="POST">
    <input name="name" value="{{ nurse['name'] }}" placeholder="Nurse full name" required>
    <input name="age" type="number" min="18" value="{{ nurse['age'] }}" required>
    <select name="gender" required>
    <option value="Male" {% if nurse['gender']=='Male' %}selected{% endif %}>Male</option>
    <option value="Female" {% if nurse['gender']=='Female' %}selected{% endif %}>Female</option>
    <option value="Other" {% if nurse['gender']=='Other' %}selected{% endif %}>Other</option>
    </select>
    <input name="phone" value="{{ nurse['phone'] }}" placeholder="Phone number" required>
    <input name="qualification" value="{{ nurse['qualification'] }}" placeholder="Qualification">
    <input name="department" value="{{ nurse['department'] }}" placeholder="Department">
    <select name="shift">
    <option value="" {% if not nurse['shift'] %}selected{% endif %}>Select shift</option>
    <option value="Morning" {% if nurse['shift']=='Morning' %}selected{% endif %}>Morning</option>
    <option value="Evening" {% if nurse['shift']=='Evening' %}selected{% endif %}>Evening</option>
    <option value="Night" {% if nurse['shift']=='Night' %}selected{% endif %}>Night</option>
    </select>
    <button type="submit">Save Changes</button>
    </form></div></body></html>
    """, nurse=nurse)


@app.route("/nurses/delete/<int:nurse_id>", methods=["POST"])
@login_required
def delete_nurse(nurse_id):
    with connect_db() as con:
        con.execute("DELETE FROM nurses WHERE id = ?", (nurse_id,))
    return redirect("/nurses")




@app.route("/accounts", methods=["GET", "POST"])
@login_required
def accounts_page():
    with connect_db() as con:
        if request.method == "POST":
            kind = request.form.get("transaction_type", "")
            category = request.form.get("category", "").strip()
            description = request.form.get("description", "").strip()
            amount_text = request.form.get("amount", "").strip()
            transaction_date = request.form.get("transaction_date", "").strip()

            try:
                amount = float(amount_text)
            except (ValueError, TypeError):
                amount = 0

            if kind in ("Income", "Expense") and category and 0 < amount < 100000000000:
                con.execute("""
                    INSERT INTO accounts
                    (transaction_type, category, description, amount, transaction_date)
                    VALUES (?, ?, ?, ?, COALESCE(NULLIF(?, ''), date('now','localtime')))
                """, (kind, category, description, amount, transaction_date))
                return redirect("/accounts")

        rows = con.execute(
            "SELECT * FROM accounts ORDER BY transaction_date DESC, id DESC"
        ).fetchall()
        totals = con.execute("""
            SELECT
            COALESCE(SUM(CASE WHEN transaction_type='Income' THEN amount ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN transaction_type='Expense' THEN amount ELSE 0 END),0)
            FROM accounts
        """).fetchone()

    return render_template_string("""
    <!doctype html>
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Hospital Accounts</title>
    <style>
    body{font-family:Arial;background:#edf3f7;padding:18px}
    .card{background:white;padding:18px;border-radius:12px;margin-bottom:18px;overflow-x:auto}
    input,select,button{width:100%;padding:12px;margin:7px 0;box-sizing:border-box}
    button{background:#087f8c;color:white;border:0;border-radius:7px;cursor:pointer}
    .delete{background:#b42318}
    .edit{display:inline-block;background:#087f8c;color:white;padding:9px 12px;border-radius:6px;text-decoration:none}
    table{width:100%;border-collapse:collapse;min-width:650px}
    th,td{padding:10px;border-bottom:1px solid #ddd;text-align:left}
    </style></head><body>
    <div class="card">
    <a href="/">← Dashboard</a>
    <h1>💰 Hospital Accounts</h1>
    <h2>Record Transaction</h2>
    <form method="POST">
    <label>Transaction type</label>
    <select name="transaction_type" required>
    <option value="Income">Income</option>
    <option value="Expense">Expense</option>
    </select>
    <label>Category</label>
    <input name="category" placeholder="e.g. Salary, Medicine, Other income" required>
    <label>Description</label>
    <input name="description" placeholder="Transaction details">
    <label>Amount (BDT ৳)</label>
    <input name="amount" type="number" min="0.01" step="0.01" required placeholder="Enter amount">
    <label>Date</label>
    <input name="transaction_date" type="date">
    <button type="submit">Save Transaction</button>
    </form></div>

    <div class="card">
    <h2>Accounts Summary</h2>
    <p>Additional Income: <b>{{ "%.2f"|format(totals[0]) }} ৳</b></p>
    <p>Expenses: <b>{{ "%.2f"|format(totals[1]) }} ৳</b></p>
    <p>Additional Balance: <b>{{ "%.2f"|format(totals[0]-totals[1]) }} ৳</b></p>
    </div>

    <div class="card">
    <h2>Transactions ({{ rows|length }})</h2>
    <table>
    <tr><th>Date</th><th>Type</th><th>Category</th><th>Description</th><th>Amount</th><th>Actions</th></tr>
    {% for r in rows %}
    <tr>
    <td>{{ r['transaction_date'] }}</td>
    <td>{{ r['transaction_type'] }}</td>
    <td>{{ r['category'] }}</td>
    <td>{{ r['description'] }}</td>
    <td>{{ "%.2f"|format(r['amount']) }} ৳</td>
    <td>
    <a class="edit" href="/accounts/edit/{{ r['id'] }}">Edit</a>
    <form method="POST" action="/accounts/delete/{{ r['id'] }}"
    onsubmit="return confirm('Delete this transaction?')">
    <button class="delete" type="submit">Delete</button>
    </form>
    </td></tr>
    {% else %}
    <tr><td colspan="6">No transactions recorded yet.</td></tr>
    {% endfor %}
    </table></div></body></html>
    """, rows=rows, totals=totals)


@app.route("/accounts/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_account(item_id):
    with connect_db() as con:
        item = con.execute(
            "SELECT * FROM accounts WHERE id=?", (item_id,)
        ).fetchone()

        if item is None:
            return "Transaction not found", 404

        if request.method == "POST":
            kind = request.form.get("transaction_type", "")
            category = request.form.get("category", "").strip()
            description = request.form.get("description", "").strip()
            amount_text = request.form.get("amount", "").strip()
            transaction_date = request.form.get("transaction_date", "").strip()

            try:
                amount = float(amount_text)
            except (ValueError, TypeError):
                amount = 0

            if kind in ("Income", "Expense") and category and 0 < amount < 100000000000 and transaction_date:
                con.execute("""
                    UPDATE accounts SET transaction_type=?, category=?,
                    description=?, amount=?, transaction_date=?
                    WHERE id=?
                """, (kind, category, description, amount, transaction_date, item_id))
                return redirect("/accounts")

    return render_template_string("""
    <!doctype html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Edit Transaction</title>
    <style>
    body{font-family:Arial;background:#edf3f7;padding:18px}
    .card{background:white;padding:18px;border-radius:12px;max-width:600px;margin:auto}
    input,select,button{width:100%;padding:12px;margin:7px 0;box-sizing:border-box}
    button{background:#087f8c;color:white;border:0;border-radius:7px}
    </style></head><body>
    <div class="card">
    <a href="/accounts">← Back to Accounts</a>
    <h1>Edit Transaction</h1>
    <form method="POST">
    <label>Type</label>
    <select name="transaction_type" required>
    <option value="Income" {% if item['transaction_type']=='Income' %}selected{% endif %}>Income</option>
    <option value="Expense" {% if item['transaction_type']=='Expense' %}selected{% endif %}>Expense</option>
    </select>
    <label>Category</label>
    <input name="category" value="{{ item['category'] }}" required>
    <label>Description</label>
    <input name="description" value="{{ item['description'] }}">
    <label>Amount (BDT ৳)</label>
    <input name="amount" type="number" min="0.01" step="0.01" value="{{ item['amount'] }}" required>
    <label>Date</label>
    <input name="transaction_date" type="date" value="{{ item['transaction_date'] }}" required>
    <button type="submit">Save Changes</button>
    </form></div></body></html>
    """, item=item)


@app.route("/accounts/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_account(item_id):
    with connect_db() as con:
        con.execute("DELETE FROM accounts WHERE id=?", (item_id,))
    return redirect("/accounts")


@app.route("/pharmacy", methods=["GET", "POST"])
@login_required
def pharmacy_page():
    with connect_db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            expiry TEXT NOT NULL
        )""")
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            quantity = request.form.get("quantity", type=int)
            price = request.form.get("price", type=float)
            expiry = request.form.get("expiry", "").strip()
            if name and quantity is not None and quantity >= 0 and price is not None and price >= 0 and expiry:
                con.execute(
                    "INSERT INTO medicines (name, quantity, price, expiry) VALUES (?, ?, ?, ?)",
                    (name, quantity, price, expiry)
                )
            return redirect("/pharmacy")
        medicines = con.execute("SELECT * FROM medicines ORDER BY id DESC").fetchall()

    return render_template_string("""
    <!doctype html><html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pharmacy Management</title>
    <style>
    body{font-family:Arial;background:#edf3f7;padding:18px}
    .card{background:white;padding:18px;border-radius:12px;margin:15px auto;max-width:700px}
    input,button{box-sizing:border-box;width:100%;padding:12px;margin:7px 0}
    button{background:#087f8c;color:white;border:0;border-radius:6px}
    </style></head><body>
    <div class="card"><a href="/">← Dashboard</a>
    <h1>💊 Pharmacy Management</h1>
    <form method="post">
    <label>Medicine name</label><input name="name" maxlength="100" required>
    <label>Quantity in stock</label><input name="quantity" type="number" min="0" required>
    <label>Unit price</label><input name="price" type="number" min="0" step="0.01" required>
    <label>Expiry date</label><input name="expiry" type="date" required>
    <button type="submit">Add Medicine</button></form></div>
    <div class="card"><h2>Medicine Stock ({{ medicines|length }})</h2>
    {% for m in medicines %}
    <p><b>{{ m['name'] }}</b><br>Quantity: {{ m['quantity'] }}
    <br>Unit price: {{ "%.2f"|format(m['price']) }}
    <br>Expiry: {{ m['expiry'] }}</p>
    <a href="/pharmacy/edit/{{ m['id'] }}">Edit</a>
    <form method="post" action="/pharmacy/delete/{{ m['id'] }}" onsubmit="return confirm('Delete this medicine?')">
    <button type="submit">Delete</button></form><hr>
    {% else %}<p>No medicines added yet.</p>{% endfor %}
    </div></body></html>
    """, medicines=medicines)


@app.route("/ambulance/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_ambulance(item_id):
    with connect_db() as con:
        row = con.execute("SELECT * FROM ambulances WHERE id=?", (item_id,)).fetchone()
        if row is None:
            return "Ambulance record not found", 404
        if request.method == "POST":
            vehicle_no = request.form.get("vehicle_no", "").strip()
            driver_name = request.form.get("driver_name", "").strip()
            phone = request.form.get("phone", "").strip()
            status = request.form.get("status", "Available")
            if vehicle_no and driver_name and phone and status in ("Available", "On Trip", "Maintenance"):
                con.execute("UPDATE ambulances SET vehicle_no=?, driver_name=?, phone=?, status=? WHERE id=?",
                            (vehicle_no, driver_name, phone, status, item_id))
                return redirect("/ambulance")
        return render_template_string("""
        <h1>Edit Ambulance</h1>
        <form method="post">
        Vehicle number <input name="vehicle_no" value="{{ r['vehicle_no'] }}" required>
        Driver name <input name="driver_name" value="{{ r['driver_name'] }}" required>
        Phone <input name="phone" value="{{ r['phone'] }}" required>
        Status <select name="status">
        {% for x in ['Available','On Trip','Maintenance'] %}
        <option value="{{ x }}" {% if r['status']==x %}selected{% endif %}>{{ x }}</option>
        {% endfor %}
        </select>
        <button type="submit">Save Changes</button></form>
        <a href="/ambulance">Cancel</a>
        """, r=row)


@app.route("/ambulance/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_ambulance(item_id):
    with connect_db() as con:
        con.execute("DELETE FROM ambulances WHERE id=?", (item_id,))
    return redirect("/ambulance")


@app.route("/pharmacy/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_medicine(item_id):
    with connect_db() as con:
        row = con.execute("SELECT * FROM medicines WHERE id=?", (item_id,)).fetchone()
        if row is None:
            return "Medicine record not found", 404
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            quantity = request.form.get("quantity", type=int)
            price = request.form.get("price", type=float)
            expiry = request.form.get("expiry", "").strip()
            if name and quantity is not None and quantity >= 0 and price is not None and price >= 0 and expiry:
                con.execute("UPDATE medicines SET name=?, quantity=?, price=?, expiry=? WHERE id=?",
                            (name, quantity, price, expiry, item_id))
                return redirect("/pharmacy")
        return render_template_string("""
        <h1>Edit Medicine</h1>
        <form method="post">
        Medicine name <input name="name" value="{{ r['name'] }}" required>
        Quantity <input name="quantity" type="number" min="0" value="{{ r['quantity'] }}" required>
        Unit price <input name="price" type="number" min="0" step="0.01" value="{{ r['price'] }}" required>
        Expiry date <input name="expiry" type="date" value="{{ r['expiry'] }}" required>
        <button type="submit">Save Changes</button></form>
        <a href="/pharmacy">Cancel</a>
        """, r=row)


@app.route("/pharmacy/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_medicine(item_id):
    with connect_db() as con:
        con.execute("DELETE FROM medicines WHERE id=?", (item_id,))
    return redirect("/pharmacy")



CMS_DEFAULTS = {
    "about": ("About Hospital", "Welcome to our hospital."),
    "services": ("Services", "Hospital services information."),
    "doctors": ("Doctors", "Doctor information will be published here."),
    "departments": ("Departments", "Hospital departments information."),
    "notices": ("Notice / News", "Hospital notices and news."),
    "contact": ("Contact", "Contact us by email: efite.com.bd@gmail.com"),
}

@app.route("/<page_slug>")
def cms_public_page(page_slug):
    if page_slug not in CMS_DEFAULTS:
        from flask import abort
        abort(404)

    default_title, default_content = CMS_DEFAULTS[page_slug]
    with connect_db() as con:
        row = con.execute(
            "SELECT title, content FROM cms_pages WHERE slug=?",
            (page_slug,)
        ).fetchone()

    title = row["title"] if row else default_title
    content = row["content"] if row else default_content

    return render_template_string("""
    <!doctype html><html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }}</title>
    <style>
    body{font-family:Arial;background:#edf3f7;margin:0;padding:20px}
    main{max-width:800px;margin:auto}.card{background:white;padding:20px;border-radius:12px}
    a,button{display:inline-block;background:#087f8c;color:white;padding:10px 14px;
    border-radius:6px;text-decoration:none;border:0}
    </style></head><body><main><div class="card">
    <h1>{{ title }}</h1><div style="white-space:pre-wrap">{{ content }}</div>
    <p><a href="/">Home</a> <a href="/cms">CMS Admin</a></p>
    </div></main></body></html>
    """, title=title, content=content)

@app.route("/cms", methods=["GET", "POST"])
@login_required
def cms_admin():
    message = ""
    with connect_db() as con:
        if request.method == "POST":
            slug = request.form.get("slug", "")
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            if slug in CMS_DEFAULTS and title:
                con.execute("""
                    INSERT INTO cms_pages (slug, title, content)
                    VALUES (?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                    title=excluded.title, content=excluded.content
                """, (slug, title, content))
                message = "Page saved successfully."
            else:
                message = "Please enter a title."

        rows = con.execute(
            "SELECT slug, title, content FROM cms_pages ORDER BY slug"
        ).fetchall()

    saved = {row["slug"]: row for row in rows}
    pages = []
    for slug, (default_title, default_content) in CMS_DEFAULTS.items():
        row = saved.get(slug)
        pages.append({
            "slug": slug,
            "title": row["title"] if row else default_title,
            "content": row["content"] if row else default_content,
        })

    return render_template_string("""
    <!doctype html><html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CMS Admin</title>
    <style>
    body{font-family:Arial;background:#edf3f7;margin:0;padding:16px}
    main{max-width:800px;margin:auto}.card{background:white;padding:16px;
    border-radius:12px;margin:14px 0}input,textarea,select,button{box-sizing:border-box;
    width:100%;padding:12px;margin:7px 0}button,a{background:#087f8c;color:white;
    padding:10px 14px;border:0;border-radius:6px;text-decoration:none}
    </style></head><body><main><h1>Website CMS Admin</h1>
    <p>{{ message }}</p>
    {% for page in pages %}
    <div class="card"><h2>{{ page.title }}</h2>
    <form method="post">
    <label>Page</label><select name="slug">
    {% for item in pages %}
    <option value="{{ item.slug }}" {% if item.slug == page.slug %}selected{% endif %}>
    {{ item.title }}</option>{% endfor %}
    </select>
    <label>Title</label><input name="title" value="{{ page.title }}" required>
    <label>Content</label><textarea name="content" rows="5">{{ page.content }}</textarea>
    <button type="submit">Save Page</button>
    </form><a href="/{{ page.slug }}">View page</a></div>
    {% endfor %}
    <p><a href="/">Back to Patients</a></p></main></body></html>
    """, pages=pages, message=message)


@app.route("/front-cms")
def front_cms_home():
    pages = [
        ("About Hospital", "/about", "🏥"),
        ("Services", "/services", "🩺"),
        ("Doctors", "/doctors", "👨‍⚕️"),
        ("Departments", "/departments", "🏢"),
        ("Notice / News", "/notices", "📢"),
        ("Contact", "/contact", "📞"),
    ]
    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Hospital | Official Website</title>
      <style>
        *{box-sizing:border-box}
        body{margin:0;font-family:Arial,sans-serif;background:#eef5f8;color:#243746}
        header{background:#087f8c;color:white;padding:28px 16px;text-align:center}
        nav{background:#066873;padding:12px;text-align:center}
        nav a{color:white;text-decoration:none;display:inline-block;padding:9px}
        main{max-width:950px;margin:24px auto;padding:0 14px}
        .hero,.card{background:white;padding:22px;border-radius:12px;
          box-shadow:0 2px 8px #0001}
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:18px}
        .card a{color:#087f8c;text-decoration:none;font-weight:bold}
        footer{text-align:center;padding:24px;color:#52616b}
      </style>
    </head>
    <body>
      <header>
        <h1 style="font-size:36px; font-weight:800; text-align:center; color:#087f8c; margin:0 0 14px;">🏥 Hospital ERP</h1>
        <p>Welcome to our Hospital Official Website</p>
      </header>
      <nav>
        <a href="/front-cms">Home</a>
        {% for title, url, emoji in pages %}
        <a href="{{ url }}">{{ title }}</a>
        {% endfor %}
      </nav>
      <main>
        <section class="hero">
          <h2>Welcome to Our Hospital</h2>
          <p>Find hospital information, services, doctors, departments,
          notices and contact details using the links below.</p>
        </section>
        <section class="grid">
          {% for title, url, emoji in pages %}
          <article class="card">
            <h2>{{ emoji }} {{ title }}</h2>
            <p>View hospital {{ title|lower }} information.</p>
            <a href="{{ url }}">View {{ title }} →</a>
          </article>
          {% endfor %}
        </section>
      </main>
      <footer>Hospital ERP</footer>
    </body>
    </html>
    """, pages=pages)





@app.route("/exam-reports/<int:report_id>/edit", methods=["GET", "POST"])
@login_required
def edit_exam_report(report_id):
    from flask import abort, redirect, url_for
    from flask import render_template_string, redirect, url_for

    with connect_db() as con:
        report = con.execute(
            "SELECT * FROM exam_reports WHERE id = ?", (report_id,)
        ).fetchone()
        if report is None:
            abort(404)

        patients = con.execute(
            "SELECT id, name FROM patients ORDER BY name"
        ).fetchall()

        if request.method == "POST":
            patient_id = request.form.get("patient_id", type=int)
            exam_name = request.form.get("exam_name", "").strip()
            result = request.form.get("result", "").strip()
            remarks = request.form.get("remarks", "").strip()
            patient = con.execute(
                "SELECT id FROM patients WHERE id = ?", (patient_id,)
            ).fetchone() if patient_id else None

            if patient and exam_name and result:
                con.execute("""
                    UPDATE exam_reports
                    SET patient_id=?, exam_name=?, result=?, remarks=?
                    WHERE id=?
                """, (patient_id, exam_name, result, remarks, report_id))
                return redirect(url_for("exam_report"))

            error = "Choose a patient and enter the examination name and result."
        else:
            error = ""

    return render_template_string("""
    <!doctype html><html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Edit Exam Report</title>
    <style>
    body{font-family:Arial;max-width:700px;margin:30px auto;padding:16px}
    input,select,textarea{box-sizing:border-box;width:100%;padding:10px;margin:8px 0 16px}
    button{padding:10px 16px;cursor:pointer}
    </style></head><body>
    <h1>Edit Exam Report #{{ report['id'] }}</h1>
    <p style="color:#b00">{{ error }}</p>
    <form method="post">
    <label>Patient</label><select name="patient_id" required>
    {% for p in patients %}
    <option value="{{ p['id'] }}" {% if p['id'] == report['patient_id'] %}selected{% endif %}>
    {{ p['name'] }} (ID {{ p['id'] }})</option>
    {% endfor %}</select>
    <label>Examination name</label>
    <input name="exam_name" value="{{ report['exam_name'] }}" required>
    <label>Result</label>
    <textarea name="result" rows="4" required>{{ report['result'] }}</textarea>
    <label>Remarks</label>
    <textarea name="remarks" rows="2">{{ report['remarks'] or '' }}</textarea>
    <button type="submit">Save Changes</button>
    <a href="{{ url_for('exam_report') }}">Cancel</a>
    </form></body></html>
    """, report=report, patients=patients, error=error)


@app.route("/exam-reports/<int:report_id>/delete", methods=["POST"])
@login_required
def delete_exam_report(report_id):
    with connect_db() as con:
        con.execute("DELETE FROM exam_reports WHERE id = ?", (report_id,))
    return redirect(url_for("exam_report"))


@app.route("/exam-reports", methods=["GET", "POST"])
@app.route("/exam-report", methods=["GET", "POST"])
@login_required
def exam_report():
    message = ""
    with connect_db() as con:
        if request.method == "POST":
            patient_id = request.form.get("patient_id", type=int)
            exam_name = request.form.get("exam_name", "").strip()
            result = request.form.get("result", "").strip()
            remarks = request.form.get("remarks", "").strip()

            patient = con.execute(
                "SELECT id FROM patients WHERE id = ?", (patient_id,)
            ).fetchone() if patient_id else None

            if not patient or not exam_name or not result:
                message = "Select a patient and enter the exam name and result."
            else:
                con.execute(
                    """INSERT INTO exam_reports
                       (patient_id, exam_name, result, remarks)
                       VALUES (?, ?, ?, ?)""",
                    (patient_id, exam_name, result, remarks)
                )
                message = "Exam report saved successfully."

        patients = con.execute(
            "SELECT id, name FROM patients ORDER BY name"
        ).fetchall()

        reports = con.execute("""
            SELECT e.id, e.patient_id, p.name, e.exam_name,
                   e.result, e.remarks, e.created_at
            FROM exam_reports e
            JOIN patients p ON p.id = e.patient_id
            ORDER BY e.id DESC
        """).fetchall()

    from flask import render_template_string
    return render_template_string("""
    <!doctype html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Exam Reports</title>
    <style>
    body{font-family:Arial;max-width:1000px;margin:30px auto;padding:0 16px;background:#f4f7fb}
    .panel{background:white;padding:20px;margin-bottom:20px;border-radius:10px}
    input,select,textarea{display:block;width:100%;box-sizing:border-box;padding:10px;margin:8px 0 16px}
    button,.btn{background:#087f8c;color:white;padding:10px 16px;border:0;border-radius:5px;cursor:pointer}
    table{width:100%;border-collapse:collapse;background:white}
    th,td{text-align:left;padding:9px;border-bottom:1px solid #ddd;vertical-align:top}
    .scroll{overflow-x:auto} .message{color:#087f45}
    @media print{form,.no-print{display:none}body{background:white}}
    </style></head><body>
    <p class="no-print"><a href="/">← Dashboard</a></p>
    <section class="panel">
    <button class="no-print" onclick="window.print()">Print / Save as PDF</button>
    <h1>Exam Report Management</h1>
    <p class="message">{{ message }}</p>
    <form method="post">
    <label>Patient</label>
    <select name="patient_id" required>
    <option value="">Select patient</option>
    {% for p in patients %}
    <option value="{{ p['id'] }}">{{ p['name'] }} (ID {{ p['id'] }})</option>
    {% endfor %}
    </select>
    <label>Examination name</label><input name="exam_name" required>
    <label>Result</label><textarea name="result" rows="4" required></textarea>
    <label>Remarks</label><textarea name="remarks" rows="2"></textarea>
    <button type="submit">Save Report</button>
    </form></section>
    <section class="panel"><h2>Previous Reports</h2>
    <p class="no-print"><button onclick="window.print()">Print Reports</button></p>
    <div class="scroll"><table><thead><tr>
    <th>ID</th><th>Patient</th><th>Examination</th><th>Result</th><th>Remarks</th><th>Date</th><th>Actions</th>
    </tr></thead><tbody>
    {% for r in reports %}<tr>
    <td>{{ r['id'] }}</td><td>{{ r['name'] }} (#{{ r['patient_id'] }})</td>
    <td>{{ r['exam_name'] }}</td><td>{{ r['result'] }}</td>
    <td>{{ r['remarks'] }}</td><td>{{ r['created_at'] }}</td><td class="no-print">
    <a href="{{ url_for('edit_exam_report', report_id=r['id']) }}">Edit</a>
    <form method="post" style="display:inline"
      action="{{ url_for('delete_exam_report', report_id=r['id']) }}"
      onsubmit="return confirm('Delete this exam report permanently?')">
      <button type="submit">Delete</button>
    </form>
    </td>
    </tr>{% else %}<tr><td colspan="6">No examination reports yet.</td></tr>
    {% endfor %}</tbody></table></div></section></body></html>
    """, patients=patients, reports=reports, message=message)

@app.route("/billing", methods=["GET", "POST"])
@login_required
def billing():
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                consultation REAL NOT NULL DEFAULT 0,
                medicine REAL NOT NULL DEFAULT 0,
                tests REAL NOT NULL DEFAULT 0,
                other_charge REAL NOT NULL DEFAULT 0,
                discount REAL NOT NULL DEFAULT 0,
                paid REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        if request.method == "POST":
            try:
                patient_id = int(request.form.get("patient_id", "0"))
                consultation = max(0, float(request.form.get("consultation", 0)))
                medicine = max(0, float(request.form.get("medicine", 0)))
                tests = max(0, float(request.form.get("tests", 0)))
                other_charge = max(0, float(request.form.get("other_charge", 0)))
                discount = max(0, float(request.form.get("discount", 0)))
                paid = max(0, float(request.form.get("paid", 0)))
                patient = con.execute(
                    "SELECT id FROM patients WHERE id=?", (patient_id,)
                ).fetchone()
                total = max(0, consultation + medicine + tests + other_charge - discount)
                if not patient:
                    raise ValueError("Please select a valid patient.")
                if discount > consultation + medicine + tests + other_charge:
                    raise ValueError("Discount cannot exceed the bill amount.")
                if paid > total:
                    raise ValueError("Paid amount cannot exceed the total.")
                con.execute("""
                    INSERT INTO bills
                    (patient_id, consultation, medicine, tests, other_charge, discount, paid)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (patient_id, consultation, medicine, tests, other_charge, discount, paid))
                con.commit()
                return redirect("/billing")
            except (ValueError, TypeError):
                error = "Invalid amount or patient. Check the values and try again."
            else:
                error = ""
        else:
            error = ""
        patients = con.execute("SELECT id, name, phone FROM patients ORDER BY name").fetchall()
        bills = con.execute("""
            SELECT b.*, p.name AS patient_name,
                   MAX(0, b.consultation+b.medicine+b.tests+b.other_charge-b.discount) AS total
            FROM bills b JOIN patients p ON p.id=b.patient_id
            ORDER BY b.id DESC
        """).fetchall()

    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Hospital Billing</title>
      <style>
        body{font-family:Arial,sans-serif;background:#edf3f7;margin:0;padding:16px;color:#243746}
        main{max-width:950px;margin:auto}
        .card{background:white;padding:18px;border-radius:12px;margin:16px 0}
        input,select,button{box-sizing:border-box;width:100%;padding:11px;margin:6px 0}
        button,.btn{background:#087f8c;color:white;border:0;border-radius:6px;padding:11px;text-decoration:none;display:inline-block}
        .tablewrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:600px}
        th,td{padding:9px;border-bottom:1px solid #ddd;text-align:left}
        @media print{.no-print{display:none!important}body{background:white;padding:0}.card{box-shadow:none}}
      </style>
    </head>
    <body><main>
      <div class="no-print"><a class="btn" href="/">← Dashboard</a></div>
      <h1>🧾 Hospital Billing</h1>
      <section class="card">
        <h2>Create Invoice</h2>
        {% if error %}<p style="color:#b42318">{{ error }}</p>{% endif %}
        {% if patients %}
        <form method="post">
          <label>Patient</label>
          <select name="patient_id" required>
            <option value="">Select patient</option>
            {% for p in patients %}
            <option value="{{ p.id }}">{{ p.name }} — ID {{ p.id }} — {{ p.phone }}</option>
            {% endfor %}
          </select>
          <label>Consultation fee</label><input type="number" name="consultation" min="0" step="0.01" value="0" required>
          <label>Medicine charge</label><input type="number" name="medicine" min="0" step="0.01" value="0" required>
          <label>Test / Examination charge</label><input type="number" name="tests" min="0" step="0.01" value="0" required>
          <label>Other charge</label><input type="number" name="other_charge" min="0" step="0.01" value="0" required>
          <label>Discount</label><input type="number" name="discount" min="0" step="0.01" value="0" required>
          <label>Amount paid</label><input type="number" name="paid" min="0" step="0.01" value="0" required>

          <div id="billing-live-total" style="background:#eaf7f7;padding:14px;border-radius:8px;margin:12px 0">
            <p>Subtotal: <strong id="live-subtotal">0.00</strong></p>
            <p>Total after discount: <strong id="live-total">0.00</strong></p>
            <p>Paid: <strong id="live-paid">0.00</strong></p>
            <p>Due: <strong id="live-due">0.00</strong></p>
            <p>Status: <strong id="live-status">Unpaid</strong></p>
          </div>
          <script>
          (() => {
            const form = document.querySelector('form[method="post"]');
            if (!form) return;
            const fields = ['consultation','medicine','tests','other_charge','discount','paid'];
            const amount = name => Math.max(0, Number(form.elements[name]?.value || 0) || 0);
            function calculate() {
              const subtotal = fields.slice(0,4).reduce((sum, name) => sum + amount(name), 0);
              const total = Math.max(0, subtotal - amount('discount'));
              const paid = amount('paid');
              const due = Math.max(0, total - paid);
              document.getElementById('live-subtotal').textContent = subtotal.toFixed(2);
              document.getElementById('live-total').textContent = total.toFixed(2);
              document.getElementById('live-paid').textContent = paid.toFixed(2);
              document.getElementById('live-due').textContent = due.toFixed(2);
              document.getElementById('live-status').textContent =
                due <= 0 ? 'Paid' : (paid > 0 ? 'Partial' : 'Unpaid');
            }
            fields.forEach(name => form.elements[name]?.addEventListener('input', calculate));
            calculate();
          })();
          </script>
          <button type="submit">Save Invoice</button>
        </form>
        {% else %}
        <p>No patients found. Add a patient before creating a bill.</p>
        {% endif %}
      </section>
      <section class="card">
        <h2>Billing History</h2>
        <div class="tablewrap"><table>
          <thead><tr><th>Invoice</th><th>Patient</th><th>Date</th><th>Total</th><th>Paid</th><th>Due</th><th>Status</th></tr></thead>
          <tbody>
          {% for b in bills %}
          <tr>
            <td>#{{ b.id }}</td><td>{{ b.patient_name }}</td><td>{{ b.created_at }}</td>
            <td>{{ "%.2f"|format(b.total) }}</td>
            <td>{{ "%.2f"|format(b.paid) }}</td>
            <td>{{ "%.2f"|format(b.total-b.paid) }}</td>
            <td>{{ "Paid" if b.total-b.paid <= 0 else ("Partial" if b.paid > 0 else "Unpaid") }}</td>
          </tr>
          {% else %}
          <tr><td colspan="7">No invoices yet.</td></tr>
          {% endfor %}
          </tbody>
        </table></div>
        <button class="no-print" onclick="window.print()">Print / Save as PDF</button>
      </section>
    </main></body></html>
    """, patients=patients, bills=bills, error=error)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    from flask import render_template_string

    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS hospital_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL DEFAULT ''
            )
        """)

        if request.method == "POST":
            fields = {
                "hospital_name": request.form.get("hospital_name", "").strip(),
                "address": request.form.get("address", "").strip(),
                "phone": request.form.get("phone", "").strip(),
                "email": request.form.get("email", "").strip(),
            }
            for key, value in fields.items():
                con.execute(
                    "INSERT OR REPLACE INTO hospital_settings "
                    "(setting_key, setting_value) VALUES (?, ?)",
                    (key, value)
                )
            message = "Settings saved successfully."
        else:
            message = ""

        saved = dict(con.execute(
            "SELECT setting_key, setting_value FROM hospital_settings"
        ).fetchall())

    return render_template_string("""
    <!doctype html>
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Hospital Settings</title>
    <style>
      body{font-family:Arial,sans-serif;max-width:720px;margin:25px auto;padding:16px;background:#f4f7f8}
      .card{background:white;padding:22px;border-radius:10px}
      label{display:block;margin-top:14px;font-weight:bold}
      input,textarea{box-sizing:border-box;width:100%;padding:11px;margin-top:6px;border:1px solid #bbb;border-radius:5px}
      button,a{display:inline-block;margin-top:18px;padding:11px 16px;border:0;border-radius:5px;background:#205763;color:white;text-decoration:none;cursor:pointer}
      .message{color:green}
      @media print{.no-print{display:none!important}body{background:white}}
    </style></head><body>
    <section class="card">
      <h1>⚙️ Hospital Settings</h1>
      <p class="message">{{ message }}</p>
      <form method="post">
        <label>Hospital name</label>
        <input name="hospital_name" value="{{ saved.get('hospital_name','') }}" placeholder="Hospital name">
        <label>Address</label>
        <textarea name="address" rows="3" placeholder="Hospital address">{{ saved.get('address','') }}</textarea>
        <label>Phone</label>
        <input name="phone" value="{{ saved.get('phone','') }}" placeholder="Contact phone">
        <label>Email</label>
        <input type="email" name="email" value="{{ saved.get('email','') }}" placeholder="Contact email">
        <button type="submit" class="no-print">Save Settings</button>
        <button type="button" class="no-print" onclick="window.print()">Print / Save as PDF</button>
        <a class="no-print" href="/">Back to Home</a>
      </form>
    </section></body></html>
    """, saved=saved, message=message)




@app.route("/admin")
@login_required
def admin_dashboard():
    from flask import abort
    if str(current_user.role).strip().lower() != "admin":
        abort(403)
    return render_template_string("""
    <html>
    <head>
      <title>Admin Dashboard</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f4f6f9; }
        .panel { background: white; padding: 20px; margin: 15px 0; border-radius: 10px; }
        a { display: inline-block; padding: 10px 14px; margin: 5px 0; background: #1769aa; color: white; text-decoration: none; border-radius: 5px; }
      </style>
    </head>
    <body>
      <h1>Admin Dashboard</h1>
      <div class="panel">
        <h3>User & Admin Management</h3>
        <p>Create accounts, reset passwords, change roles, and manage account status.</p>
        <a href="/admin/users">Open User Management</a>
      </div>
      <div class="panel">
        <h3>Hospital Settings</h3>
        <p>Manage your hospital information.</p>
        <a href="/settings">Open Settings</a>
      </div>
      <p><a href="/">Back to Hospital Home</a></p>
    </body>
    </html>
    """)

@app.route("/users")
@login_required
def users_alias():
    return redirect("/admin/users")


@app.route("/admin/users", methods=["GET", "POST"])
@login_required
def admin_users():
    from flask import abort
    import sqlite3

    if str(current_user.role).strip().lower() != "admin":
        abort(403)

    message = ""
    error = ""

    with connect_db() as con:
        if request.method == "POST":
            action = request.form.get("action", "")

            if action == "add":
                username = request.form.get("username", "").strip()
                password = request.form.get("password", "")
                role = request.form.get("role", "Staff")

                if not username or len(username) > 80 or len(password) < 8:
                    error = "Enter a username (maximum 80 characters) and a password of at least 8 characters."
                elif role not in ("Admin", "Staff"):
                    error = "Invalid role selected."
                else:
                    try:
                        con.execute(
                            "INSERT INTO users (username, password_hash, role, active) VALUES (?, ?, ?, 1)",
                            (username, generate_password_hash(password), role)
                        )
                        message = "User created successfully."
                    except sqlite3.IntegrityError:
                        error = "That username already exists."

            elif action in ("reset", "role", "toggle"):
                user_id = request.form.get("user_id", type=int)
                target = con.execute(
                    "SELECT id, username, role, active FROM users WHERE id=?",
                    (user_id,)
                ).fetchone() if user_id else None

                if not target:
                    error = "User not found."
                elif action == "reset":
                    password = request.form.get("new_password", "")
                    if len(password) < 8:
                        error = "New password must be at least 8 characters."
                    else:
                        con.execute(
                            "UPDATE users SET password_hash=? WHERE id=?",
                            (generate_password_hash(password), user_id)
                        )
                        message = "Password reset successfully."

                elif action == "role":
                    new_role = request.form.get("role", "")
                    if new_role not in ("Admin", "Staff"):
                        error = "Invalid role."
                    elif target["id"] == int(current_user.get_id()) and new_role != "Admin":
                        error = "You cannot remove your own administrator role."
                    elif target["role"].lower() == "admin" and new_role != "Admin" and target["active"]:
                        count = con.execute(
                            "SELECT COUNT(*) FROM users WHERE role='Admin' COLLATE NOCASE AND active=1"
                        ).fetchone()[0]
                        if count <= 1:
                            error = "You cannot demote the last active administrator."
                        else:
                            con.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
                            message = "User role updated."
                    else:
                        con.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
                        message = "User role updated."

                elif action == "toggle":
                    if target["id"] == int(current_user.get_id()):
                        error = "You cannot deactivate your own account."
                    elif target["active"] and target["role"].lower() == "admin":
                        count = con.execute(
                            "SELECT COUNT(*) FROM users WHERE role='Admin' COLLATE NOCASE AND active=1"
                        ).fetchone()[0]
                        if count <= 1:
                            error = "You cannot deactivate the last active administrator."
                        else:
                            con.execute("UPDATE users SET active=0 WHERE id=?", (user_id,))
                            message = "User deactivated."
                    else:
                        new_active = 0 if target["active"] else 1
                        con.execute("UPDATE users SET active=? WHERE id=?", (new_active, user_id))
                        message = "User activated." if new_active else "User deactivated."
            else:
                error = "Unknown action."

        users = con.execute(
            "SELECT id, username, role, active FROM users ORDER BY id"
        ).fetchall()

    return render_template_string("""
    <!doctype html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>User Management</title>
    <style>
      body{font-family:Arial,sans-serif;max-width:1050px;margin:24px auto;padding:14px;background:#f3f6f7}
      .card{background:white;padding:18px;margin-bottom:18px;border-radius:9px;overflow-x:auto}
      input,select,button{box-sizing:border-box;padding:9px;margin:4px;max-width:100%}
      button{background:#205763;color:white;border:0;border-radius:5px;cursor:pointer}
      table{border-collapse:collapse;width:100%;min-width:680px}
      th,td{border:1px solid #ddd;padding:9px;text-align:left}
      th{background:#eaf2f3}
      .ok{color:green}.err{color:#b00020}
      form.inline{display:inline-block;margin:3px}
      @media print{.no-print{display:none!important}body{background:white}}
    </style></head><body>
    <h1>👥 User &amp; Admin Management</h1>
    <p class="ok">{{ message }}</p><p class="err">{{ error }}</p>

    <section class="card">
      <h2>Add User</h2>
      <form method="post">
        <input type="hidden" name="action" value="add">
        <label>Username <input name="username" maxlength="80" required></label>
        <label>Temporary password <input type="password" name="password" minlength="8" required></label>
        <label>Role <select name="role"><option>Staff</option><option>Admin</option></select></label>
        <button type="submit">Create User</button>
      </form>
    </section>

    <section class="card">
      <h2>Existing Users</h2>
      <table><thead><tr><th>ID</th><th>Username</th><th>Role</th><th>Status</th><th>Change Role</th><th>Reset Password</th><th>Account</th></tr></thead>
      <tbody>
      {% for u in users %}
      <tr>
        <td>{{ u['id'] }}</td><td>{{ u['username'] }}</td><td>{{ u['role'] }}</td>
        <td>{{ 'Active' if u['active'] else 'Inactive' }}</td>
        <td>
          <form class="inline" method="post">
            <input type="hidden" name="action" value="role">
            <input type="hidden" name="user_id" value="{{ u['id'] }}">
            <select name="role">
              <option value="Staff" {{ 'selected' if u['role'].lower() == 'staff' else '' }}>Staff</option>
              <option value="Admin" {{ 'selected' if u['role'].lower() == 'admin' else '' }}>Admin</option>
            </select><button>Save Role</button>
          </form>
        </td>
        <td>
          <form class="inline" method="post">
            <input type="hidden" name="action" value="reset">
            <input type="hidden" name="user_id" value="{{ u['id'] }}">
            <input type="password" name="new_password" minlength="8" placeholder="New password" required>
            <button>Reset</button>
          </form>
        </td>
        <td>
          <form class="inline" method="post" onsubmit="return confirm('Change this account status?')">
            <input type="hidden" name="action" value="toggle">
            <input type="hidden" name="user_id" value="{{ u['id'] }}">
            <button>{{ 'Deactivate' if u['active'] else 'Activate' }}</button>
          </form>
        </td>
      </tr>
      {% else %}
      <tr><td colspan="7">No users found.</td></tr>
      {% endfor %}
      </tbody></table>
      <button class="no-print" onclick="window.print()">Print / Save as PDF</button>
      <p><a href="/">Back to Home</a></p>
    </section></body></html>
    """, users=users, message=message, error=error)


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
