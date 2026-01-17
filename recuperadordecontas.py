from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random
import string
import hashlib
import os
import smtplib
from email.mime.text import MIMEText

# ================= APP =================
app = Flask(__name__)
CORS(app)

# ================= DATABASE =================
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "SQLALCHEMY_DATABASE_URI"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELS =================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

class RecoveryCode(db.Model):
    __tablename__ = "recovery_codes"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(6), nullable=False)

# ================= EMAIL =================
EMAIL_REMETENTE = os.environ.get("EMAIL_USER")
EMAIL_SENHA = os.environ.get("EMAIL_PASS")

def enviar_email(dest, assunto, texto):
    msg = MIMEText(texto)
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = dest
    msg["Subject"] = assunto

    smtp = smtplib.SMTP("smtp.gmail.com", 587)
    smtp.starttls()
    smtp.login(EMAIL_REMETENTE, EMAIL_SENHA)
    smtp.send_message(msg)
    smtp.quit()

# ================= UTILS =================
def gerar_codigo():
    return "".join(random.choices(string.digits, k=6))

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ================= ROUTES =================
@app.route("/")
def status():
    return jsonify({
        "service": "Recuperador de Contas Online",
        "status": "ok"
    })

# -------- RECUPERAR USERNAME --------
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

    return jsonify({"msg": "Utilizador enviado para o email"})

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
        f"O seu código de recuperação é: {code}"
    )

    return jsonify({"msg": "Código enviado para o email"})

# -------- CONFIRMAR NOVA PASSWORD --------
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

# ================= INIT DB =================
with app.app_context():
    db.create_all()

# ================= START =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
