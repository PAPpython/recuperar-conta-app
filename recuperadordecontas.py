from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import time
import hashlib
import hmac
import base64
import json

# ================= APP =================
app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ================= CONFIG =================
app.config["SECRET_KEY"] = "recuperar-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ================= DB =================
db = SQLAlchemy(app)

# ================= MODELO USER =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(128))

# ================= CONFIG CÓDIGOS =================
SIGN_SECRET = b"recuperacao-super-secreta"
CODE_EXPIRATION = 300  # 5 minutos

# ================= UTILS =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def generate_code(tipo):
    payload = {
        "type": tipo,
        "exp": int(time.time()) + CODE_EXPIRATION
    }

    data = json.dumps(payload).encode()
    sig = hmac.new(SIGN_SECRET, data, hashlib.sha256).digest()

    token = base64.urlsafe_b64encode(data + b"." + sig).decode()
    return token

def validate_code(token, tipo_esperado):
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        data, sig = raw.rsplit(b".", 1)

        expected = hmac.new(SIGN_SECRET, data, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return False, "Assinatura inválida"

        payload = json.loads(data.decode())

        if payload.get("type") != tipo_esperado:
            return False, "Tipo incorreto"

        if time.time() > payload.get("exp", 0):
            return False, "Código expirado"

        return True, "OK"

    except Exception:
        return False, "Código inválido"

# ================= ROTAS PÁGINAS =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/recover-password")
def recover_password():
    return render_template("recover_password.html")

@app.route("/recover-username")
def recover_username():
    return render_template("recover_username.html")

# ================= API GERAR CÓDIGOS =================
@app.route("/api/generate-password-code", methods=["GET"])
def generate_password_code():
    token = generate_code("password")
    return jsonify(status="ok", token=token, expires=CODE_EXPIRATION)

@app.route("/api/generate-username-code", methods=["GET"])
def generate_username_code():
    token = generate_code("username")
    return jsonify(status="ok", token=token, expires=CODE_EXPIRATION)

# ================= API VALIDAR CÓDIGOS =================
@app.route("/api/validate-password-code", methods=["POST"])
def validate_password_code():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()

    ok, msg = validate_code(code, "password")
    if not ok:
        return jsonify(status="error", msg=msg)

    return jsonify(status="ok")

@app.route("/api/validate-username-code", methods=["POST"])
def validate_username_code():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()

    ok, msg = validate_code(code, "username")
    if not ok:
        return jsonify(status="error", msg=msg)

    return jsonify(status="ok")

# ================= API ALTERAR PASSWORD =================
@app.route("/api/change-password", methods=["POST"])
def change_password():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    new_password = data.get("password")

    if not username or not new_password:
        return jsonify(status="error", msg="Dados inválidos")

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify(status="error", msg="Utilizador não encontrado")

    user.password = hash_password(new_password)
    db.session.commit()

    return jsonify(status="ok", msg="Password alterada com sucesso")

# ================= API OBTER USERNAME =================
@app.route("/api/get-username", methods=["POST"])
def get_username():
    data = request.get_json(silent=True) or {}
    email = data.get("email")

    if not email:
        return jsonify(status="error", msg="Email inválido")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(status="error", msg="Email não encontrado")

    return jsonify(status="ok", username=user.username)

@app.route("/check-username", methods=["POST"])
def check_username():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify(exists=False)

    existe = User.query.filter_by(username=username).first() is not None
    return jsonify(exists=existe)

@app.route("/check-email", methods=["POST"])
def check_email():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()

    if not email:
        return jsonify(exists=False)

    existe = User.query.filter_by(email=email).first() is not None
    return jsonify(exists=existe)

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
