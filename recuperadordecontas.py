from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from models import db, User, RecoveryCode
import random
import string
import hashlib

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# 🔥 CRIA AS TABELAS SEMPRE (Render + local)
with app.app_context():
    db.create_all()

# ---------------- UTIL ----------------
def gerar_codigo():
    return "".join(random.choices(string.digits, k=6))

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ---------------- PÁGINAS ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/recover-password")
def recover_password_page():
    return render_template("recover_password.html")

@app.route("/recover-username")
def recover_username_page():
    return render_template("recover_username.html")

# ---------------- API ----------------
@app.route("/api/recover-password", methods=["POST"])
def recover_password_api():
    data = request.json
    step = data.get("step")

    if step == "email":
        email = data.get("email")
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"status": "error", "msg": "Email não encontrado"}), 404

        RecoveryCode.query.filter_by(email=email).delete()
        code = gerar_codigo()
        db.session.add(RecoveryCode(email=email, code=code))
        db.session.commit()

        # Aqui entraria envio de email real
        print("CÓDIGO:", code)

        return jsonify({"status": "ok", "msg": "Código enviado para o email"})

    if step == "confirm":
        email = data.get("email")
        code = data.get("code")
        password = data.get("password")

        rec = RecoveryCode.query.filter_by(email=email, code=code).first()
        if not rec:
            return jsonify({"status": "error", "msg": "Código inválido"}), 400

        user = User.query.filter_by(email=email).first()
        user.password = hash_password(password)

        db.session.delete(rec)
        db.session.commit()

        return jsonify({"status": "ok", "msg": "Password alterada com sucesso"})

    return jsonify({"status": "error"}), 400

@app.route("/api/recover-username", methods=["POST"])
def recover_username_api():
    email = request.json.get("email")
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"status": "error", "msg": "Email não encontrado"}), 404

    return jsonify({
        "status": "ok",
        "msg": f"O teu nome de utilizador é: {user.username}"
    })
