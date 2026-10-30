from pathlib import Path

p = Path("app.py")
s = p.read_text()

if 'id="billing-live-total"' in s:
    print("Automatic calculation already exists. No changes made.")
    raise SystemExit

marker = '          <button type="submit">Save Invoice</button>'
if marker not in s:
    print("ERROR: Billing form marker not found. No changes made.")
    raise SystemExit

addition = '''
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
'''
p.write_text(s.replace(marker, addition + marker, 1))
print("SUCCESS: Live billing calculation added.")
