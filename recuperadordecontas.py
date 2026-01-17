from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os, random, string, hashlib

app = Flask(__name__)

# 🔗 DATABASE (Render usa DATABASE_URL automaticamente)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///local.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ⬇️ IMPORT MODELS DEPOIS DO db
from models import User, RecoveryCode

# =========================
# HOME
# =========================
@app.route("/")
def index():
    return render_template("index.html")

# =========================
# RECOVER USERNAME
# =========================
@app.route("/recover-username", methods=["GET", "POST"])
def recover_username():
    if request.method == "POST":
        email = request.form.get("email")

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"status": "error", "msg": "Email não encontrado"})

        # Aqui normalmente enviavas email
        return jsonify({
            "status": "ok",
            "msg": f"O nome de utilizador foi enviado para o email ({user.username})"
        })

    return render_template("recover_username.html")

# =========================
# RECOVER PASSWORD
# =========================
@app.route("/recover-password", methods=["GET", "POST"])
def recover_password():

    if request.method == "POST":
        step = request.form.get("step")
        email = request.form.get("email")

        # 🔹 PASSO 1 — ENVIAR CÓDIGO
        if step == "email":
            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({"status": "error", "msg": "Email não encontrado"})

            code = "".join(random.choices(string.digits, k=6))

            RecoveryCode.query.filter_by(email=email).delete()
            db.session.add(RecoveryCode(email=email, code=code))
            db.session.commit()

            print("CÓDIGO GERADO:", code)  # DEBUG (Render logs)

            return jsonify({"status": "ok", "msg": "Código enviado para o email"})

        # 🔹 PASSO 2 — CONFIRMAR CÓDIGO
        if step == "confirm":
            code = request.form.get("code")
            password = request.form.get("password")

            rec = RecoveryCode.query.filter_by(email=email, code=code).first()
            if not rec:
                return jsonify({"status": "error", "msg": "Código inválido"})

            user = User.query.filter_by(email=email).first()
            user.password = hashlib.sha256(password.encode()).hexdigest()

            db.session.delete(rec)
            db.session.commit()

            return jsonify({"status": "ok", "msg": "Password alterada com sucesso"})

    return render_template("recover_password.html")


if __name__ == "__main__":
    app.run(debug=True)
