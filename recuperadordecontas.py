from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import os, uuid

# ================= APP =================
app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config["SECRET_KEY"] = "recover-site-secret"
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

# ================= HOME =================
@app.route("/")
def home():
    return "Site de recuperação online ✅"

# ================= PEDIR RECUPERAÇÃO =================
@app.route("/recover", methods=["POST"])
def recover():
    email = request.json.get("email")

    if not email:
        return jsonify(status="error", message="Email obrigatório")

    account = Account.query.filter_by(email=email).first()
    if not account:
        return jsonify(status="error", message="Email não encontrado")

    code = uuid.uuid4().hex
    account.recovery_code = code
    account.recovery_expires = datetime.utcnow() + timedelta(minutes=10)

    db.session.commit()

    return jsonify(
        status="ok",
        message="Código gerado",
        code=code
    )

# ================= RESET PASSWORD =================
@app.route("/reset", methods=["POST"])
def reset():
    code = request.json.get("code")
    password = request.json.get("password")

    if not code or not password:
        return jsonify(status="error", message="Dados em falta")

    account = Account.query.filter_by(recovery_code=code).first()
    if not account:
        return jsonify(status="error", message="Código inválido")

    if account.recovery_expires < datetime.utcnow():
        return jsonify(status="error", message="Código expirado")

    account.password_hash = generate_password_hash(password)
    account.recovery_code = None
    account.recovery_expires = None

    db.session.commit()

    return jsonify(status="ok", message="Password alterada")

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
