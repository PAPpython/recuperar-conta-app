from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import uuid, os, smtplib
from email.message import EmailMessage

from models import db, User

app = Flask(__name__)

app.config["SECRET_KEY"] = "recover-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///recover.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ================= EMAIL CONFIG =================
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

def send_email(to, code):
    msg = EmailMessage()
    msg["Subject"] = "Código de Recuperação"
    msg["From"] = EMAIL_USER
    msg["To"] = to
    msg.set_content(f"O teu código de recuperação é:\n\n{code}\n\nVálido por 10 minutos.")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

# ================= HOME =================
@app.route("/")
def index():
    return render_template("index.html")

# ================= STEP 1 =================
@app.route("/recover-password", methods=["GET", "POST"])
def recover_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if not user:
            return render_template("message.html", message="Email não encontrado")

        code = uuid.uuid4().hex[:6].upper()
        user.recovery_code = code
        user.recovery_expires = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()

        send_email(user.email, code)

        return redirect(url_for("reset_password"))

    return render_template("recover_password.html")

# ================= STEP 2 =================
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        code = request.form.get("code")
        password = request.form.get("password")

        user = User.query.filter_by(recovery_code=code).first()

        if not user:
            return render_template("message.html", message="Código inválido")

        if user.recovery_expires < datetime.utcnow():
            return render_template("message.html", message="Código expirado")

        user.password_hash = generate_password_hash(password)
        user.recovery_code = None
        user.recovery_expires = None
        db.session.commit()

        return render_template("message.html", message="Password alterada com sucesso")

    return render_template("reset_password.html")

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
