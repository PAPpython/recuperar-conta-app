from flask import Flask, request, jsonify, render_template
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
DATABASE_URL = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    "sqlite:///fallback.db"
)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
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
    if not EMAIL_REMETENTE or not EMAIL_SENHA:
        print("EMAIL_USER ou EMAIL_PASS não definidos")
        return

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

# ================= PÁGINAS (GET) =================
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/recover-username", methods=["GET"])
def recover_username_page():
    return render_template("recover_username.html")

@app.route("/recover-password", methods=["GET"])
def recover_password_page():
    return render_template("recover_password.html")

# ================= AÇÕES (POST) =================
@app.route("/recover/username", methods=["POST"])
def recover_username():
    email = request.form.get("email")

    if not email:
        return render_template("message.html", status="error", text="Email é obrigatório")

    user = User.query.filter_by(email=email).first()
    if not user:
        return render_template("message.html", status="error", text="Email não encontrado")

    enviar_email(
        email,
        "Recuperação de Utilizador",
        f"O seu nome de utilizador é: {user.username}"
    )

    return render_template(
        "message.html",
        status="ok",
        text="O nome de utilizador foi enviado para o teu email"
    )

@app.route("/recover/password/request", methods=["POST"])
def request_code():
    email = request.form.get("email")

    if not email:
        return render_template("message.html", status="error", text="Email é obrigatório")

    user = User.query.filter_by(email=email).first()
    if not user:
        return render_template("message.html", status="error", text="Email não encontrado")

    RecoveryCode.query.filter_by(email=email).delete()

    code = gerar_codigo()
    db.session.add(RecoveryCode(email=email, code=code))
    db.session.commit()

    enviar_email(
        email,
        "Código de Recuperação",
        f"O seu código de recuperação é: {code}"
    )

    return render_template(
        "message.html",
        status="ok",
        text="Código enviado para o email"
    )

@app.route("/recover/password/confirm", methods=["POST"])
def confirm_password():
    email = request.form.get("email")
    code = request.form.get("code")
    new_password = request.form.get("new_password")

    if not all([email, code, new_password]):
        return render_template("message.html", status="error", text="Dados incompletos")

    rec = RecoveryCode.query.filter_by(email=email, code=code).first()
    if not rec:
        return render_template("message.html", status="error", text="Código inválido")

    user = User.query.filter_by(email=email).first()
    if not user:
        return render_template("message.html", status="error", text="Utilizador não encontrado")

    user.password = hash_password(new_password)
    db.session.delete(rec)
    db.session.commit()

    return render_template(
        "message.html",
        status="ok",
        text="Password alterada com sucesso"
    )

# ================= INIT DB =================
with app.app_context():
    db.create_all()

# ================= START =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
