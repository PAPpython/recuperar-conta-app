from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
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

     # 🔐 Recuperação
    email_recuperacao = db.Column(db.String(120), nullable=True)
    perguntas_recuperacao = db.Column(db.Text, nullable=True)  # JSON

    ativo = db.Column(db.Boolean, default=True)  # Define se a conta está ativa
    desativado_em = db.Column(db.DateTime, nullable=True)  # Data de desativação
    reactivation_code = db.Column(db.String(32), nullable=True)  # Código de reativação temporário
    apagado = db.Column(db.Boolean, default=False)  # Marca se a conta foi apagada
# ================= CRIAR TABELAS =================
with app.app_context():
    db.create_all()
# ================= CONFIG CÓDIGOS =================
SIGN_SECRET = b"recuperacao-super-secreta"
CODE_EXPIRATION = 300  # 5 minutos

# ================= UTILS =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def generate_code(tipo):
    # 16 caracteres hex (compatível com o app)
    return os.urandom(16).hex()

def validate_code(token, tipo_esperado):
    if (
        not token
        or len(token) != 32
        or not all(c in "0123456789abcdef" for c in token.lower())
    ):
        return False, "Código inválido"

    return True, "OK"

def hash_resposta(resposta: str) -> str:
    return hashlib.sha256(resposta.strip().lower().encode()).hexdigest()

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
    data = request.get_json(force=True)

    email = (data.get("email") or "").strip().lower()
    new_password = data.get("password")

    if not email or not new_password:
        return jsonify(status="error", msg="Dados inválidos")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(status="error", msg="Email não encontrado")

    user.password = hash_password(new_password)
    db.session.commit()

    return jsonify(status="ok", msg="Password alterada com sucesso")
# ================= API OBTER USERNAME =================
@app.route("/api/get-username-by-email", methods=["POST"])
def get_username_by_email():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(status="error", msg="Email não encontrado")

    return jsonify(
        status="ok",
        username=user.username
    )
# ================= CHECK USERNAME =================
@app.route("/check-username", methods=["POST"])
def check_username():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify(exists=False)

    return jsonify(
        exists=User.query.filter_by(username=username).first() is not None
    )
# ================= CHECK EMAIL =================
@app.route("/check-email", methods=["POST"])
def check_email():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()

    if not email:
        return jsonify(exists=False)

    return jsonify(
        exists=User.query.filter_by(email=email).first() is not None
    )
    
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)

    username = (data.get("username") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not username or not email or not password:
        return jsonify(status="error", msg="Dados inválidos"), 400

    if User.query.filter_by(username=username).first():
        return jsonify(status="error", msg="Username já existe"), 409

    if User.query.filter_by(email=email).first():
        return jsonify(status="error", msg="Email já existe"), 409

    user = User(
        username=username,
        email=email,
        password=hash_password(password)
    )

    db.session.add(user)
    db.session.commit()

    return jsonify(status="ok")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)

    identificador = (data.get("username") or "").strip().lower()
    password = data.get("password")

    if not identificador or not password:
        return jsonify(status="error", msg="Dados inválidos"), 400

    user = (
        User.query.filter_by(username=identificador).first()
        or User.query.filter_by(email=identificador).first()
        or User.query.filter_by(email_recuperacao=identificador).first()
    )

    if not user:
        return jsonify(status="error", msg="Utilizador não encontrado"), 404

    if user.password != hash_password(password):
        return jsonify(status="error", msg="Password inválida"), 401

    if user.apagado:
        return jsonify(
            status="error",
            msg="Essa conta foi apagada. Não é possível fazer login."
        ), 403

    return jsonify(
        status="ok",
        id=user.id,
        username=user.username,
        email=user.email
    )

# ================= API PARA DELETAR CONTA =================
@app.route("/delete-account", methods=["POST"])
def delete_account():
    data = request.get_json(force=True)

    user_id = data.get("id")
    username = (data.get("username") or "").strip().lower()

    if not user_id or not username:
        return jsonify(status="error", msg="Dados inválidos"), 400

    user = User.query.filter_by(id=user_id, username=username).first()

    if not user:
        return jsonify(status="error", msg="Conta já não existe"), 404

    # Marcar a conta como apagada
    user.apagado = True
    db.session.commit()

    return jsonify(status="ok", msg="Conta apagada com sucesso")

# ================= GUARDAR DADOS DE RECUPERAÇÃO =================
@app.route("/api/save-recovery-data", methods=["POST"])
def save_recovery_data():
    data = request.get_json(force=True)

    email = (data.get("email") or "").strip().lower()
    email_rec = (data.get("email_recuperacao") or "").strip().lower()
    perguntas = data.get("perguntas", [])

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(status="error", msg="Utilizador não encontrado"), 404

    # 🔒 EVITAR EMAIL DE RECUPERAÇÃO DUPLICADO
    if email_rec:
        existe = User.query.filter(
            User.email_recuperacao == email_rec,
            User.email != email
        ).first()

        if existe:
            return jsonify(
                status="error",
                msg="Este email de recuperação já está a ser usado noutra conta"
            ), 409

    # 🔢 Limite de perguntas
    if len(perguntas) > 5:
        return jsonify(status="error", msg="Máximo de 5 perguntas"), 400

    # Guardar email de recuperação
    user.email_recuperacao = email_rec if email_rec else None

    perguntas_guardar = []

    for p in perguntas:
        pergunta = (p.get("pergunta") or "").strip()
        resposta = (p.get("resposta") or "").strip()

        if pergunta and resposta:
            perguntas_guardar.append({
                "pergunta": pergunta,
                "hash": hash_resposta(resposta)
            })

    user.perguntas_recuperacao = (
        json.dumps(perguntas_guardar) if perguntas_guardar else None
    )

    db.session.commit()

    return jsonify(status="ok")

# ================= OBTER PERGUNTAS DE RECUPERAÇÃO =================
@app.route("/api/get-recovery-questions", methods=["POST"])
def get_recovery_questions():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()

    user = (
        User.query.filter_by(email=email).first()
        or User.query.filter_by(email_recuperacao=email).first()
    )

    if not user or not user.perguntas_recuperacao:
        return jsonify(status="error", msg="Sem perguntas de recuperação"), 404

    perguntas = json.loads(user.perguntas_recuperacao)

    return jsonify(
        status="ok",
        email_principal=user.email,
        perguntas=[p["pergunta"] for p in perguntas]
    )
# ================= VALIDAR RESPOSTAS =================
@app.route("/api/validate-recovery-answers", methods=["POST"])
def validate_recovery_answers():
    data = request.get_json(force=True)

    email = (data.get("email") or "").strip().lower()
    respostas = data.get("respostas", [])

    user = (
        User.query.filter_by(email=email).first()
        or User.query.filter_by(email_recuperacao=email).first()
    )

    if not user or not user.perguntas_recuperacao:
        return jsonify(status="error", msg="Utilizador inválido"), 404

    perguntas_guardadas = json.loads(user.perguntas_recuperacao)

    if len(respostas) != len(perguntas_guardadas):
        return jsonify(status="error", msg="Número de respostas inválido"), 400

    for i, resposta in enumerate(respostas):
        if hash_resposta(resposta) != perguntas_guardadas[i]["hash"]:
            return jsonify(status="error", msg="Resposta incorreta"), 401

    return jsonify(
        status="ok",
        email_principal=user.email
    )
# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
