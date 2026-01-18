from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import time
import hashlib
import secrets

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config["SECRET_KEY"] = "recuperar-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELOS =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(128))

class RecoveryCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(20))  # password | username
    expires = db.Column(db.Integer)

CODE_EXPIRATION = 300

# ================= UTILS =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def generate_code():
    return secrets.token_hex(16)

# ================= ROTAS =================
@app.route("/")
def index():
    return "Servidor ativo"

# ================= GERAR CÓDIGOS =================
@app.route("/api/generate-password-code", methods=["GET"])
def generate_password_code():
    code = generate_code()
    expires = int(time.time() + CODE_EXPIRATION)

    db.session.add(RecoveryCode(code=code, type="password", expires=expires))
    db.session.commit()

    return jsonify(status="ok", code=code, expires=CODE_EXPIRATION)

@app.route("/api/generate-username-code", methods=["GET"])
def generate_username_code():
    code = generate_code()
    expires = int(time.time() + CODE_EXPIRATION)

    db.session.add(RecoveryCode(code=code, type="username", expires=expires))
    db.session.commit()

    return jsonify(status="ok", code=code, expires=CODE_EXPIRATION)

# ================= VALIDAR PASSWORD =================
@app.route("/api/validate-password-code", methods=["POST"])
def validate_password_code():
    try:
        data = request.get_json(force=True)
        code = data.get("code")

        rec = RecoveryCode.query.filter_by(code=code, type="password").first()

        if not rec:
            return jsonify(status="error", msg="Código inválido")

        if time.time() > rec.expires:
            db.session.delete(rec)
            db.session.commit()
            return jsonify(status="error", msg="Código expirado")

        return jsonify(status="ok", msg="Código válido")

    except Exception as e:
        print("ERRO:", e)
        return jsonify(status="error", msg="Erro interno"), 500

# ================= VALIDAR USERNAME =================
@app.route("/api/validate-username-code", methods=["POST"])
def validate_username_code():
    try:
        data = request.get_json(force=True)
        code = data.get("code")

        rec = RecoveryCode.query.filter_by(code=code, type="username").first()

        if not rec:
            return jsonify(status="error", msg="Código inválido")

        if time.time() > rec.expires:
            db.session.delete(rec)
            db.session.commit()
            return jsonify(status="error", msg="Código expirado")

        return jsonify(status="ok", msg="Código válido")

    except Exception as e:
        print("ERRO:", e)
        return jsonify(status="error", msg="Erro interno"), 500

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
