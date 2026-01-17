from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import random
import time
import hashlib

# ================= APP =================
app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ================= CONFIG =================
app.config["SECRET_KEY"] = "recuperar-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ================= DB =================
db = SQLAlchemy(app)

# ================= MODELO =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(128))

# ================= MEMÓRIA TEMP =================
recovery_codes = {}

# ================= UTILS =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ================= ROTAS PÁGINAS =================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/recover-password")
def recover_password():
    return render_template("recover_password.html")

# ================= API RECUPERAR PASSWORD =================
@app.route("/api/recover-password", methods=["POST"])
def api_recover_password():
    data = request.get_json()
    step = data.get("step")
    email = data.get("email")

    # PASSO 1 — ENVIAR CÓDIGO
    if step == "email":
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify(status="error", msg="Email não encontrado")

        code = str(random.randint(100000, 999999))
        recovery_codes[email] = {
            "code": code,
            "expires": time.time() + 300
        }

        # DEBUG (Render Logs)
        print(f"CÓDIGO PARA {email}: {code}")

        return jsonify(status="ok", msg="Código enviado para o email")

    # PASSO 2 — CONFIRMAR CÓDIGO
    if step == "confirm":
        code = data.get("code")
        password = data.get("password")

        saved = recovery_codes.get(email)
        if not saved:
            return jsonify(status="error", msg="Código inválido")

        if time.time() > saved["expires"]:
            return jsonify(status="error", msg="Código expirado")

        if code != saved["code"]:
            return jsonify(status="error", msg="Código incorreto")

        user = User.query.filter_by(email=email).first()
        user.password = hash_password(password)
        db.session.commit()

        del recovery_codes[email]

        return jsonify(status="ok", msg="Password alterada com sucesso")

    return jsonify(status="error", msg="Pedido inválido")

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
