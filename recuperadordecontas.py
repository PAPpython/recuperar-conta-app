from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import uuid, os, smtplib
from email.message import EmailMessage

from models import db, User

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///recover.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "recover-secret"

db.init_app(app)

# ================= EMAIL CONFIG =================
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

def send_email(to, code):
    msg = EmailMessage()
    msg["Subject"] = "Código de Recuperação"
    msg["From"] = EMAIL_USER
    msg["To"] = to
    msg.set_content(f"""
Olá,

O teu código de recuperação é:

{code}

Este código é válido por 10 minutos.
""")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(EMAIL_USER, EMAIL_PASS)
        s.send_message(msg)

# ================= API =================
@app.route("/api/recover-password", methods=["POST"])
def recover_api():
    data = request.get_json()
    step = data.get("step")
    email = data.get("email")

    user = User.query.filter_by(email=email).first()

    # ---------- STEP 1 ----------
    if step == "email":
        if not user:
            return jsonify(status="error", msg="Email não encontrado")

        code = uuid.uuid4().hex[:6].upper()
        user.recovery_code = code
        user.recovery_expires = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()

        send_email(email, code)

        return jsonify(status="ok", msg="Código enviado para o email")

    # ---------- STEP 2 ----------
    if step == "confirm":
        if not user:
            return jsonify(status="error", msg="Conta inválida")

        if user.recovery_code != data.get("code"):
            return jsonify(status="error", msg="Código incorreto")

        if user.recovery_expires < datetime.utcnow():
            return jsonify(status="error", msg="Código expirado")

        user.password_hash = generate_password_hash(data.get("password"))
        user.recovery_code = None
        user.recovery_expires = None
        db.session.commit()

        return jsonify(status="ok", msg="Password alterada com sucesso")

    return jsonify(status="error", msg="Pedido inválido")

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=10000)
