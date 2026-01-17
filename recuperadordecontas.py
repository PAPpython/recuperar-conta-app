from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import uuid, os

from models import db, User

app = Flask(__name__)

app.config["SECRET_KEY"] = "recover-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///recover.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ================= HOME =================
@app.route("/")
def index():
    return render_template("index.html")

# ================= RECOVER PASSWORD =================
@app.route("/recover-password", methods=["GET", "POST"])
def recover_password():
    if request.method == "POST":
        email = request.form.get("email")

        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template(
                "message.html",
                message="Email não encontrado"
            )

        user.recovery_code = uuid.uuid4().hex
        user.recovery_expires = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()

        return render_template(
            "message.html",
            message=f"Código de recuperação: {user.recovery_code}"
        )

    return render_template("recover_password.html")

# ================= RESET PASSWORD =================
@app.route("/reset-password", methods=["POST"])
def reset_password():
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

    return render_template(
        "message.html",
        message="Password alterada com sucesso"
    )

# ================= RECOVER USERNAME =================
@app.route("/recover-username", methods=["GET", "POST"])
def recover_username():
    if request.method == "POST":
        email = request.form.get("email")

        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template("message.html", message="Email não encontrado")

        return render_template(
            "message.html",
            message=f"O teu username é: {user.username}"
        )

    return render_template("recover_username.html")

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
