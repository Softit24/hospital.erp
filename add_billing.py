from pathlib import Path

p = Path("app.py")
s = p.read_text()

if '@app.route("/billing"' in s:
    print("Billing route already exists. No changes made.")
    raise SystemExit

marker = '\nif __name__ == "__main__":'
if marker not in s:
    print("ERROR: App startup marker not found. No changes made.")
    raise SystemExit

route = r'''

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
'''

p.write_text(s.replace(marker, route + marker, 1))
print("SUCCESS: Billing route added.")
