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
@app.route("/reactivate-account", methods=["POST"])
def reactivate_account():
    data = request.get_json(force=True)

    username = data.get("username")
    email = data.get("email")
    code = data.get("code")  # O código de reativação enviado para o e-mail
    password = data.get("password")  # A senha atual

    try:
        # Verificar se o nome de usuário e e-mail são válidos
        user = User.query.filter_by(username=username, email=email).first()

        if not user:
            return jsonify({"status": "error", "msg": "Usuário não encontrado"}), 404

        # Verificar o código de reativação
        if user.reactivation_code != code:
            return jsonify({"status": "error", "msg": "Código de reativação inválido"}), 400

        # Verificar se a senha atual está correta
        if user.password != hash_password(password):  # Supondo que a senha esteja criptografada
            return jsonify({"status": "error", "msg": "Senha incorreta"}), 401

        # Reativar a conta
        user.ativo = True
        user.desativado_em = None  # Remove a data de desativação
        user.reactivation_code = None  # Limpa o código de reativação
        db.session.commit()

        return jsonify({"status": "ok", "msg": "Conta reativada com sucesso!"})

    except Exception as e:
        # Logar o erro para depurar
        print(f"Erro ao reativar conta: {str(e)}")
        db.session.rollback()  # Em caso de erro, reverter qualquer alteração no banco
        return jsonify({"status": "error", "msg": "Erro inesperado. Tente novamente mais tarde."}), 500

# ================= API GERAR CÓDIGOS =================
@app.route("/api/generate-password-code", methods=["GET"])
def generate_password_code():
    token = generate_code("password")
    return jsonify(status="ok", token=token, expires=CODE_EXPIRATION)

@app.route("/api/generate-username-code", methods=["GET"])
def generate_username_code():
    token = generate_code("username")
    return jsonify(status="ok", token=token, expires=CODE_EXPIRATION)

@app.route("/api/generate-reactivation-code", methods=["GET"])
def generate_reactivation_code():
    # Gera o código de reativação
    token = generate_code("reactivation")
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

@app.route("/api/validate-reactivation-code", methods=["POST"])
def validate_reactivation_code():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()

    # Verifica se o código é válido
    ok, msg = validate_code(code, "reactivation")
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

    username = (data.get("username") or "").strip().lower()
    password = data.get("password")

    if not username or not password:
        return jsonify(status="error", msg="Dados inválidos"), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify(status="error", msg="Utilizador não encontrado"), 404

    if user.password != hash_password(password):
        return jsonify(status="error", msg="Password incorreta"), 401

    if not user.ativo:
        return jsonify(status="error", msg="Conta desativada. Por favor, reative a conta."), 403  # Conta desativada

    if user.apagado:
        return jsonify(status="error", msg="A conta foi apagada. Não é possível fazer login."), 403  # Conta apagada

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

# ================= API PARA DESATIVAR CONTA =================
@app.route("/deactivate-account", methods=["POST"])
def deactivate_account():
    data = request.get_json(force=True)

    user_id = data.get("id")
    username = (data.get("username") or "").strip().lower()
    password = data.get("password")

    if not user_id or not username or not password:
        return jsonify(status="error", msg="Dados inválidos"), 400

    user = User.query.filter_by(id=user_id, username=username).first()

    if not user:
        return jsonify(status="error", msg="Conta não encontrada"), 404

    if user.password != hash_password(password):  # Verificação de senha
        return jsonify(status="error", msg="Password incorreta"), 401

    # Desativa a conta
    user.ativo = False
    user.desativado_em = datetime.utcnow()  # Marca a data de desativação
    db.session.commit()

    return jsonify(status="ok", msg="Conta desativada com sucesso. Você poderá reativar sua conta em até 3 meses.")

# ================= API REATIVAR CONTA =================
@app.route("/reactivate-account", methods=["POST"])
def reactivate_account():
    data = request.get_json(force=True)

    username = data.get("username")
    email = data.get("email")
    code = data.get("code")  # O código de reativação enviado para o e-mail
    password = data.get("password")  # A senha atual

    # Verificar se o nome de usuário e e-mail são válidos
    user = User.query.filter_by(username=username, email=email).first()

    if not user:
        return jsonify({"status": "error", "msg": "Usuário não encontrado"}), 404

    # Verificar o código de reativação
    if user.reactivation_code != code:
        return jsonify({"status": "error", "msg": "Código de reativação inválido"}), 400

    # Verificar se a senha atual está correta
    if user.password != hash_password(password):  # Supondo que a senha esteja criptografada
        return jsonify({"status": "error", "msg": "Senha incorreta"}), 401

    # Reativar a conta
    user.ativo = True
    user.desativado_em = None  # Remove a data de desativação
    user.reactivation_code = None  # Limpa o código de reativação
    db.session.commit()

    return jsonify({"status": "ok", "msg": "Conta reativada com sucesso!"})

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
