from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random
import string
import hashlib
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

# ================= DATABASE =================
DATABASE_URL = os.environ.get("DATABASE_URL")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELS =================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)

class RecoveryCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    code = db.Column(db.String)

# ================= EMAIL =================
EMAIL_REMETENTE = os.environ.get("EMAIL_USER")
EMAIL_SENHA = os.environ.get("EMAIL_PASS")

def enviar_email(dest, assunto, texto):
    msg = MIMEText(texto)
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = dest
    msg["Subject"] = assunto

    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.starttls()
    s.login(EMAIL_REMETENTE, EMAIL_SENHA)
    s.send_message(msg)
    s.quit()

# ================= UTILS =================
def gerar_codigo():
    return "".join(random.choices(string.digits, k=6))

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ================= ROUTES =================
@app.route("/")
def status():
    return jsonify({
        "service": "Recuperador de Contas Online",
        "status": "ok"
    })

# -------- RECUPERAR UTILIZADOR --------
@app.route("/recover/username", methods=["POST"])
def recover_username():
    email = request.json.get("email")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Email não encontrado"}), 404

    enviar_email(
        email,
        "Recuperação de Utilizador",
        f"O seu nome de utilizador é: {user.username}"
    )

    return jsonify({"msg": "Utilizador enviado"})


# -------- PEDIR CÓDIGO --------
@app.route("/recover/password/request", methods=["POST"])
def request_code():
    email = request.json.get("email")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Email não encontrado"}), 404

    RecoveryCode.query.filter_by(email=email).delete()

    code = gerar_codigo()
    db.session.add(RecoveryCode(email=email, code=code))
    db.session.commit()

    enviar_email(
        email,
        "Código de Recuperação",
        f"O seu código é: {code}"
    )

    return jsonify({"msg": "Código enviado"})


# -------- CONFIRMAR PASSWORD --------
@app.route("/recover/password/confirm", methods=["POST"])
def confirm_password():
    email = request.json.get("email")
    code = request.json.get("code")
    new_password = request.json.get("new_password")

    rec = RecoveryCode.query.filter_by(email=email, code=code).first()
    if not rec:
        return jsonify({"error": "Código inválido"}), 400

    user = User.query.filter_by(email=email).first()
    user.password = hash_password(new_password)

    db.session.delete(rec)
    db.session.commit()

    return jsonify({"msg": "Password alterada com sucesso"})

# ================= START =================
if __name__ == "__main__":
    app.run()
