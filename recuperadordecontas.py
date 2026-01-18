from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import time
import hashlib
import secrets

# ================= APP =================
app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ================= CONFIG =================
app.config["SECRET_KEY"] = "recuperar-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ================= DB =================
db = SQLAlchemy(app)

# ================= MODELO =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(128))

# ================= MEMÓRIA TEMP =================
password_codes = {}
username_codes = {}

CODE_EXPIRATION = 300  # 5 minutos

# ================= UTILS =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def generate_code():
    # 32 caracteres hex (igual ao Google)
    return secrets.token_hex(16)

# ================= ROTAS PÁGINAS =================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/recover-password")
def recover_password():
    return render_template("recover_password.html")

@app.route("/recover-username")
def recover_username():
    return render_template("recover_username.html")

# ================= API GERAR CÓDIGO PASSWORD =================
@app.route("/api/generate-password-code", methods=["GET"])
def generate_password_code():
    code = generate_code()

    password_codes[code] = {
        "expires": time.time() + CODE_EXPIRATION
    }

    print(f"[PASSWORD CODE] {code}")

    return jsonify(
        status="ok",
        code=code,
        expires=CODE_EXPIRATION
    )

# ================= API GERAR CÓDIGO USERNAME =================
@app.route("/api/generate-username-code", methods=["GET"])
def generate_username_code():
    code = generate_code()

    username_codes[code] = {
        "expires": time.time() + CODE_EXPIRATION
    }

    print(f"[USERNAME CODE] {code}")

    return jsonify(
        status="ok",
        code=code,
        expires=CODE_EXPIRATION
    )

# ================= API VALIDAR CÓDIGO PASSWORD (APP) =================
@app.route("/api/validate-password-code", methods=["POST"])
def validate_password_code():
    data = request.get_json()
    code = data.get("code")

    saved = password_codes.get(code)

    if not saved:
        return jsonify(status="error", msg="Código inválido")

    if time.time() > saved["expires"]:
        del password_codes[code]
        return jsonify(status="error", msg="Código expirado")

    return jsonify(status="ok", msg="Código válido")

# ================= API VALIDAR CÓDIGO USERNAME (APP) =================
@app.route("/api/validate-username-code", methods=["POST"])
def validate_username_code():
    data = request.get_json()
    code = data.get("code")

    saved = username_codes.get(code)

    if not saved:
        return jsonify(status="error", msg="Código inválido")

    if time.time() > saved["expires"]:
        del username_codes[code]
        return jsonify(status="error", msg="Código expirado")

    return jsonify(status="ok", msg="Código válido")

# ================= API ALTERAR PASSWORD (APP) =================
@app.route("/api/change-password", methods=["POST"])
def change_password():
    data = request.get_json()
    username = data.get("username")
    new_password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify(status="error", msg="Utilizador não encontrado")

    user.password = hash_password(new_password)
    db.session.commit()

    return jsonify(status="ok", msg="Password alterada com sucesso")

# ================= API ENVIAR USERNAME POR EMAIL (FUTURO) =================
@app.route("/api/get-username", methods=["POST"])
def get_username():
    data = request.get_json()
    email = data.get("email")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(status="error", msg="Email não encontrado")

    return jsonify(status="ok", username=user.username)

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
