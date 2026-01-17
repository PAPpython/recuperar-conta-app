from flask import Flask, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import uuid, os

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config["SECRET_KEY"] = "recover-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "recover.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODEL =================
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    recovery_code = db.Column(db.String(64))
    recovery_expires = db.Column(db.DateTime)

# ================= HTML =================
HTML = """
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>Recuperar Conta</title>
<style>
body {
  background:#020617;
  color:white;
  font-family:Arial;
  display:flex;
  justify-content:center;
  align-items:center;
  height:100vh;
}
.box {
  background:#020617;
  border:1px solid #334155;
  padding:40px;
  border-radius:14px;
  width:420px;
}
h1 { color:#22c55e; text-align:center; }
input, button {
  width:100%;
  padding:12px;
  margin-top:10px;
  border-radius:8px;
  border:none;
}
button {
  background:#38bdf8;
  font-weight:bold;
  cursor:pointer;
}
.code {
  margin-top:15px;
  padding:10px;
  border:1px dashed #38bdf8;
  word-break:break-all;
}
.error { color:#f87171; }
.ok { color:#22c55e; }
</style>
</head>
<body>

<div class="box">
<h1>Recuperar Conta</h1>

<form method="post">
  <input name="email" placeholder="Email" required>
  <button name="action" value="recover">Gerar código</button>
</form>

<form method="post">
  <input name="code" placeholder="Código">
  <input name="password" placeholder="Nova password" type="password">
  <button name="action" value="reset">Alterar password</button>
</form>

{% if msg %}
<p class="{{ cls }}">{{ msg }}</p>
{% endif %}

{% if code %}
<div class="code">Código: {{ code }}</div>
{% endif %}

</div>
</body>
</html>
"""

# ================= ROUTE =================
@app.route("/", methods=["GET", "POST"])
def home():
    msg = code = cls = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "recover":
            email = request.form.get("email")
            acc = Account.query.filter_by(email=email).first()

            if not acc:
                msg = "Email não encontrado"
                cls = "error"
            else:
                acc.recovery_code = uuid.uuid4().hex
                acc.recovery_expires = datetime.utcnow() + timedelta(minutes=10)
                db.session.commit()

                code = acc.recovery_code
                msg = "Código gerado com sucesso"
                cls = "ok"

        elif action == "reset":
            code_input = request.form.get("code")
            password = request.form.get("password")

            acc = Account.query.filter_by(recovery_code=code_input).first()

            if not acc:
                msg = "Código inválido"
                cls = "error"
            elif acc.recovery_expires < datetime.utcnow():
                msg = "Código expirado"
                cls = "error"
            else:
                acc.password_hash = generate_password_hash(password)
                acc.recovery_code = None
                acc.recovery_expires = None
                db.session.commit()

                msg = "Password alterada com sucesso"
                cls = "ok"

    return render_template_string(HTML, msg=msg, code=code, cls=cls)

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
