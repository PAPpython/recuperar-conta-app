from flask import Flask, render_template, request, jsonify, send_from_directory, session, url_for
import os
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
from flask import send_from_directory
from flask import request
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
import uuid
import os
import time
import hashlib
import hmac
import base64
import json
import uuid
from flask import session
from flask import redirect
import secrets
from datetime import datetime, timedelta
# ================= APP =================
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# garantir que a pasta existe (Render)
os.makedirs(os.path.join(UPLOAD_FOLDER, "fotos"), exist_ok=True)

google_login_state = {
    "logged": False,
    "exists": False,
    "id": None,
    "email": None,
    "username": None
}

# ================= SERVIR AVATARES =================
@app.route('/avatar/<filename>')
def servir_avatar(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, 'static', 'avatars')

    print("A SERVIR AVATAR:", filename)
    print("PASTA:", path)

    return send_from_directory(path, filename)
# ================= CONFIG =================
app.config["SECRET_KEY"] = "recuperar-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ================= DB =================
db = SQLAlchemy(app)

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    }
)
# ================= MODELO USER =================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(128))
    nome = db.Column(db.String(120), nullable=True)
    banner = db.Column(db.String(255), nullable=True)
    avatares_comprados = db.Column(db.Text, default="[]")
    banners_comprados = db.Column(db.Text, default="[]")
    bio = db.Column(db.String(175), nullable=True)
    role = db.Column(db.String(20), default="user")
    banido = db.Column(db.Boolean, default=False)
    suspenso_ate = db.Column(db.DateTime, nullable=True)
    warn_count = db.Column(db.Integer, default=0)
    ia_banido = db.Column(db.Boolean, default=False)
    ia_suspenso_ate = db.Column(db.DateTime, nullable=True)
    warning_count = db.Column(db.Integer, default=0)
    ia_ban_reason = db.Column(db.String(255), nullable=True)
    ultima_punicao_ia = db.Column(db.DateTime, nullable=True)
    ban_reason = db.Column(db.String(255), nullable=True)
    bloqueado = db.Column(db.Boolean, default=False)
    bloqueado_ate = db.Column(db.DateTime, nullable=True)
    apagado_por_admin = db.Column(db.Boolean, default=False)
    avisos = db.Column(db.Integer, default=0)
    email_banido = db.Column(db.Boolean, default=False)
    mostrar_publicamente = db.Column(db.Boolean, default=True)
    google_name = db.Column(db.String(120))
    google_picture = db.Column(db.String(300))
    provider = db.Column(db.String(20), default="local")
    google_token = db.Column(db.String(64), unique=True)
    is_google_pending = db.Column(db.Boolean, default=False)
    
     # 🔐 Recuperação
    email_recuperacao = db.Column(db.String(120), nullable=True)
    perguntas_recuperacao = db.Column(db.Text, nullable=True)  # JSON

    moedas = db.Column(db.Integer, default=0)

    ativo = db.Column(db.Boolean, default=True)  # Define se a conta está ativa
    desativado_em = db.Column(db.DateTime, nullable=True)  # Data de desativação
    reactivation_code = db.Column(db.String(32), nullable=True)  # Código de reativação temporário
    apagado = db.Column(db.Boolean, default=False)  # Marca se a conta foi apagada
    avatar = db.Column(db.String(50), nullable=True)  # ✅ AVATAR (ID DO AVATAR)
    ultima_recompensa_post = db.Column(db.DateTime, nullable=True)
    email_verificado = db.Column(db.Boolean, default=False)
    email_token = db.Column(db.String(128))
    email_verification_attempts = db.Column(db.Integer, default=0)
    last_verification_request = db.Column(db.DateTime, nullable=True)

class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    session_token = db.Column(
        db.String(128),
        unique=True,
        nullable=False
    )

    platform = db.Column(
        db.String(30),
        default="Desktop"
    )

    ip_address = db.Column(db.String(100))

    location = db.Column(
        db.String(100),
        default="Desconhecida"
    )

    remember_me = db.Column(
        db.Boolean,
        default=False
    )

    active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    last_seen = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class Feedback(db.Model):
    __tablename__ = "feedbacks"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    message = db.Column(db.Text)

    status = db.Column(db.String(20), default="open")  # open / closed

    admin_name = db.Column(db.String(80), nullable=True)
    admin_id = db.Column(db.Integer, nullable=True)

    rating = db.Column(db.Integer, nullable=True)  # 0-5 estrelas

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class LoginHistory(db.Model):
    __tablename__ = "login_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    ip_address = db.Column(db.String(100))

    location = db.Column(
        db.String(100),
        default="Desconhecida"
    )

    platform = db.Column(
        db.String(30),
        default="Desktop"
    )

    success = db.Column(
        db.Boolean,
        default=True
    )

    login_time = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
    
class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.String, primary_key=True)
    autor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    texto = db.Column(db.Text)

    imagem = db.Column(db.String)

    original_post_id = db.Column(
        db.String,
        db.ForeignKey("posts.id")
    )

    data = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.String, primary_key=True)

    post_id = db.Column(
        db.String,
        db.ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False
    )

    autor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    texto = db.Column(db.Text, nullable=False)

    # 🔥 FALTAVA ISTO
    imagem = db.Column(db.String)

    parent_id = db.Column(
        db.String,
        db.ForeignKey("comments.id")
    )

    data = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Like(db.Model):
    __tablename__ = "likes"

    id = db.Column(db.String, primary_key=True)
    post_id = db.Column(db.String, db.ForeignKey("posts.id", ondelete="CASCADE"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))


class CommentLike(db.Model):
    __tablename__ = "comment_likes"

    id = db.Column(db.String, primary_key=True)
    comment_id = db.Column(db.String, db.ForeignKey("comments.id", ondelete="CASCADE"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

class Follow(db.Model):
    __tablename__ = "follows"

    id = db.Column(db.String, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    followed_id = db.Column(db.Integer, db.ForeignKey("users.id"))

class Block(db.Model):
    __tablename__ = "blocks"

    id = db.Column(db.String, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    blocked_id = db.Column(db.Integer, db.ForeignKey("users.id"))

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    tipo = db.Column(db.String)
    origem_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_id = db.Column(db.String, db.ForeignKey("posts.id"))
    comment_id = db.Column(db.String, db.ForeignKey("comments.id"))
    lida = db.Column(db.Boolean, default=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.String, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    to_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    texto = db.Column(db.Text)
    lida = db.Column(db.Boolean, default=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

class Share(db.Model):
    __tablename__ = "shares"

    id = db.Column(db.String, primary_key=True)
    post_id = db.Column(db.String, db.ForeignKey("posts.id"))
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    to_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))


class ReportPost(db.Model):
    __tablename__ = "reports_posts"

    id = db.Column(db.String, primary_key=True)
    post_id = db.Column(db.String, db.ForeignKey("posts.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    motivo = db.Column(db.Text)


class ReportUser(db.Model):
    __tablename__ = "reports_users"

    id = db.Column(db.String, primary_key=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    motivo = db.Column(db.Text)

class GoogleLogin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120))
    username = db.Column(db.String(80))
    logged = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime)
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

def existe_bloqueio(a, b):
    return db.session.query(Block.id).filter(
        db.or_(
            db.and_(Block.blocker_id == a, Block.blocked_id == b),
            db.and_(Block.blocker_id == b, Block.blocked_id == a)
        )
    ).first() is not None

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

def admin_required(user_id):
    user = User.query.get(user_id)
    if not user or user.role != "admin":
        return False, jsonify(error="Sem permissão"), 403
    return True, user

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
    
# ================= REGISTRAR =================
@app.route("/register", methods=["POST"])
def register():

    data = request.get_json(force=True)

    username = (data.get("username") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not username or not email or not password:
        return jsonify(
            status="error",
            msg="Dados inválidos"
        ), 400

    # 🚫 EMAIL PERMANENTEMENTE BANIDO
    if User.query.filter_by(email=email, email_banido=True).first():
        return jsonify(
            status="error",
            msg="Este email foi permanentemente banido"
        ), 403

    # 🚫 USERNAME JÁ EXISTE
    if User.query.filter_by(username=username).first():
        return jsonify(
            status="error",
            msg="Username já existe"
        ), 409

    # 🚫 EMAIL JÁ EXISTE
    if User.query.filter_by(email=email).first():
        return jsonify(
            status="error",
            msg="Email já existe"
        ), 409

    # 🔑 TOKEN DE VERIFICAÇÃO
    token = secrets.token_urlsafe(64)

    # ✅ CRIAR CONTA
    user = User(
        username=username,
        email=email,
        password=hash_password(password),

        avatar="default",
        banner="bannerdefault",

        avatares_comprados=json.dumps([]),
        banners_comprados=json.dumps([]),
        moedas=0
    )

    db.session.add(user)
    db.session.commit()

    # ✅ SEMPRE RESPONDE SUCESSO
    return jsonify(
        status="ok",
        msg="Conta criada com sucesso."
    )
# ================= LOGIN =================
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

    if not user.email_verificado:
        return jsonify({
            "status": "error",
            "msg": "Email não verificado, verifique para poder avançar para AERON"
        }), 403

    if user.password != hash_password(password):
        return jsonify(status="error", msg="Password inválida"), 401

    if user.apagado:
        return jsonify(
            status="error",
            msg="Essa conta foi apagada. Não é possível fazer login."
        ), 403

    if user.banido:
        return jsonify(
            status="error",
            msg="Conta banida"
        ), 403

    remember_me = data.get("remember_me", False)
    platform = data.get("platform", "Desktop")

    ip = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr
    )

    token = secrets.token_hex(64)

    sessao = UserSession(
        user_id=user.id,
        session_token=token,
        platform=platform,
        ip_address=ip,
        location="Desconhecida",
        remember_me=remember_me,
        active=True
    )

    db.session.add(sessao)

    historico = LoginHistory(
        user_id=user.id,
        ip_address=ip,
        location="Desconhecida",
        platform=platform,
        success=True
    )

    db.session.add(historico)

    db.session.commit()
        
    return jsonify(
    status="ok",
    id=user.id,
    username=user.username,
    email=user.email,
    avatar=user.avatar,
    banner=user.banner,
    moedas=user.moedas,

    session_token=sessao.session_token,  # <- ok agora

    role=user.role,

    avatares_comprados=json.loads(user.avatares_comprados or "[]"),
    banners_comprados=json.loads(user.banners_comprados or "[]")
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

#================= GUARDAR DADOS DE RECUPERAÇÃO =================
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

#================= OBTER PERGUNTAS DE RECUPERAÇÃO =================
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
#================= VALIDAR RESPOSTAS =================
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

#================= CHECK EMAIL DE RECUPERAÇÃO =================
@app.route("/api/check-recovery-email", methods=["POST"])
def check_recovery_email():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify(status="error", msg="Email vazio"), 400

    user = User.query.filter(
        db.func.lower(User.email_recuperacao) == email
    ).first()

    if not user:
        return jsonify(status="error", msg="Email de recuperação inválido"), 404

    return jsonify(
        status="ok",
        email_principal=user.email
    )

#================= POSTS LIST =================
@app.route("/posts", methods=["GET"])
def listar_posts():
    user_id = request.args.get("user_id", type=int)

    posts = Post.query.order_by(Post.data.desc()).all()
    res = []

    for p in posts:
        autor = User.query.get(p.autor_id)
        real_id = p.original_post_id or p.id

        res.append({
            "id": p.id,

            "texto": p.texto,

            "imagem": p.imagem,  # 🔥 FALTAVA ISTO

            "data": p.data.strftime("%d/%m/%Y %H:%M"),

            "likes": Like.query.filter_by(post_id=real_id).count(),

            "comentarios": Comment.query.filter_by(post_id=real_id).count(),

            "autor": {
                "id": autor.id,
                "username": autor.username,
                "avatar": autor.avatar
            }
        })

    return jsonify(res)
#================= CREATE POST =================
@app.route("/posts", methods=["POST"])
def criar_post():

    # ==========================================
    # JSON OU FORM-DATA
    # ==========================================

    if request.form:
        data = request.form
    else:
        data = request.get_json(force=True)

    user = User.query.get(data["autor_id"])

    if not user:
        return jsonify(error="User não encontrado"), 404

    # ==========================================
    # 🔒 UTILIZADOR BLOQUEADO
    # ==========================================

    if user.bloqueado:
        return jsonify(
            error="Conta bloqueada"
        ), 403

    # ==========================================
    # IMAGEM
    # ==========================================

    imagem = data.get("imagem")

    # upload real
    if "imagem" in request.files:

        file = request.files["imagem"]

        if file.filename != "":

            nome = f"{uuid.uuid4()}.png"

            pasta = os.path.join(
                "static",
                "posts"
            )

            os.makedirs(
                pasta,
                exist_ok=True
            )

            caminho = os.path.join(
                pasta,
                nome
            )

            file.save(caminho)

            imagem = f"/static/posts/{nome}"

    # ==========================================
    # CRIAR POST
    # ==========================================

    post = Post(
        id=str(uuid.uuid4()),
        autor_id=data["autor_id"],
        texto=data.get("texto"),
        imagem=imagem,
        original_post_id=data.get("original_post_id")
    )

    db.session.add(post)

    # ==========================================
    # 🎁 MISSÃO DIÁRIA
    # ==========================================

    from datetime import datetime

    hoje = datetime.utcnow().date()

    if user.ultima_recompensa_post:
        ultimo = user.ultima_recompensa_post.date()
    else:
        ultimo = None

    if ultimo != hoje:

        user.moedas += 500

        user.ultima_recompensa_post = datetime.utcnow()

        print(
            "🎁 Recompensa diária atribuída: +500 moedas"
        )

    db.session.commit()

    # ==========================================
    # RETORNO COMPLETO
    # ==========================================

    return jsonify({

        "status": "ok",

        "id": post.id,  # ✅ ID POST

        "texto": post.texto,

        "imagem": post.imagem,

        "moedas": user.moedas,

        "autor": {

            "id": user.id,

            "username": user.username,

            "avatar": user.avatar

        }

    })
#================= DELETE POST =================
@app.route("/posts/<post_id>", methods=["DELETE"])
def apagar_post(post_id):
    data = request.get_json(force=True)
    user_id = data.get("user_id")

    if not user_id:
        return jsonify(error="Utilizador inválido"), 400

    post = Post.query.get(post_id)
    if not post:
        return jsonify(error="Post não encontrado"), 404

    # 🔒 Apenas o autor pode apagar
    if post.autor_id != user_id:
        return jsonify(error="Sem permissão"), 403

    # ID real (caso seja repost)
    real_id = post.original_post_id or post.id

    # 🧹 Apagar reposts
    Post.query.filter_by(
        original_post_id=real_id
    ).delete(synchronize_session=False)

    # 🧹 Apagar likes do post original
    Like.query.filter_by(
        post_id=real_id
    ).delete(synchronize_session=False)

    # 🧹 Apagar comentários do post original
    Comment.query.filter_by(
        post_id=real_id
    ).delete(synchronize_session=False)

    # 🧹 Apagar notificações associadas
    Notification.query.filter(
        db.or_(
            Notification.post_id == real_id,
            Notification.post_id == post_id
        )
    ).delete(synchronize_session=False)

    # 🗑 Apagar o próprio post
    db.session.delete(post)
    db.session.commit()

    return jsonify(status="ok")


#================= LIKE =================
@app.route("/posts/<post_id>/like", methods=["POST"])
def like(post_id):
    data = request.get_json(force=True)
    user_id = data["user_id"]

    post = Post.query.get(post_id)
    if not post:
        return jsonify(error="Post não encontrado"), 404

    # 🚫 BLOQUEIO
    if existe_bloqueio(user_id, post.autor_id):
        return jsonify(error="Utilizador bloqueado"), 403

    real_id = post.original_post_id or post.id

    existente = Like.query.filter_by(
        post_id=real_id,
        user_id=user_id
    ).first()

    # ❌ DESCURTIR
    if existente:
        db.session.delete(existente)

        # 🧹 remover notificação de like
        Notification.query.filter_by(
            tipo="like",
            origem_id=user_id,
            post_id=real_id
        ).delete(synchronize_session=False)

        db.session.commit()
        return jsonify(liked=False)

    # ❤️ CURTIR
    like = Like(
        id=str(uuid.uuid4()),
        post_id=real_id,
        user_id=user_id
    )
    db.session.add(like)

    # 🔔 NOTIFICAÇÃO (se não for o próprio autor)
    if post.autor_id != user_id:
        db.session.add(Notification(
            id=str(uuid.uuid4()),
            user_id=post.autor_id,
            tipo="like",
            origem_id=user_id,
            post_id=real_id
        ))

    db.session.commit()
    return jsonify(liked=True)

#================= COMPARTILHAR =================
@app.route("/posts/<post_id>/share", methods=["POST"])
def share_post(post_id):
    data = request.get_json(force=True)

    from_user = data["from_user_id"]
    to_user = data["to_user_id"]

    # 🔒 VER UTILIZADOR
    user = User.query.get(from_user)

    if not user:
        return jsonify(error="User não encontrado"), 404

    # 🚫 UTILIZADOR BLOQUEADO/SUSPENSO
    if user.bloqueado:
        return jsonify(
            error="Estás bloqueado e não podes partilhar posts"
        ), 403

    post = Post.query.get(post_id)

    if not post:
        return jsonify(error="Post não encontrado"), 404

    # 🚫 BLOQUEIO entre quem envia e autor do post
    if existe_bloqueio(from_user, post.autor_id):
        return jsonify(error="Utilizador bloqueado"), 403

    # 🚫 BLOQUEIO entre quem envia e quem recebe
    if existe_bloqueio(from_user, to_user):
        return jsonify(error="Utilizador bloqueado"), 403

    share = Share(
        id=str(uuid.uuid4()),
        post_id=post_id,
        from_user_id=from_user,
        to_user_id=to_user
    )

    db.session.add(share)
    db.session.commit()

    return jsonify(status="ok")
    
# ================= recebidos =================
@app.route("/shares/<int:user_id>", methods=["GET"])
def inbox(user_id):
    shares = Share.query.filter_by(to_user_id=user_id).all()
    res = []

    for s in shares:
        post = Post.query.get(s.post_id)
        if not post:
            continue

        autor = User.query.get(post.autor_id)
        sender = User.query.get(s.from_user_id)

        # 🚫 BLOQUEIO: tu ↔ quem enviou
        if existe_bloqueio(user_id, sender.id):
            continue

        # 🚫 BLOQUEIO: tu ↔ autor do post
        if existe_bloqueio(user_id, autor.id):
            continue

        res.append({
            "post_id": post.id,
            "texto": post.texto,
            "imagem": post.imagem,
            "enviado_por": sender.username,
            "autor": {
                "username": autor.username,
                "avatar": autor.avatar,
                "banner": autor.banner
            }
        })

    return jsonify(res)
    
# ================= comentário =================
@app.route("/posts/<post_id>/comment", methods=["POST"])
def comentar(post_id):

    # ==========================================
    # JSON OU FORM-DATA
    # ==========================================

    if request.form:
        data = request.form
    else:
        data = request.get_json(force=True)

    user_id = data.get("user_id")

    texto = (
        data.get("texto") or ""
    ).strip()

    parent_id = data.get("parent_id")

    # ==========================================
    # USER
    # ==========================================

    autor = User.query.get(user_id)

    if not autor:
        return jsonify(
            error="User não encontrado"
        ), 404

    # ==========================================
    # 🔒 BLOQUEADO
    # ==========================================

    if autor.bloqueado:
        return jsonify(
            error="Conta bloqueada"
        ), 403

    # ==========================================
    # POST
    # ==========================================

    post = Post.query.get(post_id)

    if not post:
        return jsonify(
            error="Post não encontrado"
        ), 404

    # 🚫 BLOQUEIO COM AUTOR DO POST
    if existe_bloqueio(
        user_id,
        post.autor_id
    ):
        return jsonify(
            error="Não podes comentar neste post"
        ), 403

    # ==========================================
    # IMAGEM
    # ==========================================

    imagem = data.get("imagem")

    if "imagem" in request.files:

        file = request.files["imagem"]

        if file.filename != "":

            nome = f"{uuid.uuid4()}.png"

            pasta = os.path.join(
                "static",
                "comments"
            )

            os.makedirs(
                pasta,
                exist_ok=True
            )

            caminho = os.path.join(
                pasta,
                nome
            )

            file.save(caminho)

            imagem = f"/static/comments/{nome}"

    # ==========================================
    # RESPOSTA A COMENTÁRIO
    # ==========================================

    parent_comment = None

    if parent_id:

        parent_comment = Comment.query.get(
            parent_id
        )

        if not parent_comment:
            return jsonify(
                error="Comentário pai não existe"
            ), 404

        if parent_comment.post_id != post_id:
            return jsonify(
                error="Comentário inválido"
            ), 400

        # 🚫 BLOQUEIO
        if existe_bloqueio(
            user_id,
            parent_comment.autor_id
        ):
            return jsonify(
                error="Não podes responder"
            ), 403

    # ==========================================
    # CRIAR COMENTÁRIO
    # ==========================================

    comment = Comment(
        id=str(uuid.uuid4()),
        post_id=post_id,
        autor_id=user_id,
        texto=texto,
        imagem=imagem,
        parent_id=parent_id
    )

    db.session.add(comment)

    db.session.commit()

    # ==========================================
    # RETORNO COMPLETO
    # ==========================================

    return jsonify({

        "status": "ok",

        "comment": {

            "id": comment.id,  # ✅ ID COMENTÁRIO

            "post_id": comment.post_id,

            "texto": comment.texto,

            "imagem": comment.imagem,

            "parent_id": comment.parent_id,

            "autor": {

                "id": autor.id,

                "username": autor.username,

                "avatar": autor.avatar

            }

        }

    })
#================= CURTIR COMENTÁRIO =================
@app.route("/comments/<comment_id>/like", methods=["POST"])
def like_comment(comment_id):
    data = request.get_json(force=True)
    user_id = data["user_id"]

    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify(error="Comentário não encontrado"), 404

    # 🚫 BLOQUEIO
    if existe_bloqueio(user_id, comment.autor_id):
        return jsonify(error="Não podes curtir este comentário"), 403

    existente = CommentLike.query.filter_by(
        comment_id=comment_id,
        user_id=user_id
    ).first()

    if existente:
        db.session.delete(existente)
        db.session.commit()
        return jsonify(liked=False)

    like = CommentLike(
        id=str(uuid.uuid4()),
        comment_id=comment_id,
        user_id=user_id
    )
    db.session.add(like)

    # 🔔 NOTIFICAÇÃO (apenas se não houver bloqueio)
    if comment.autor_id != user_id:
        db.session.add(Notification(
            id=str(uuid.uuid4()),
            user_id=comment.autor_id,
            tipo="like_comment",
            origem_id=user_id,
            comment_id=comment_id
        ))

    db.session.commit()
    return jsonify(liked=True)

#================= DENUNCIAR POST =================
@app.route("/posts/<post_id>/report", methods=["POST"])
def report_post(post_id):
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    motivo = (data.get("motivo") or "").strip()

    if not user_id:
        return jsonify(error="Utilizador inválido"), 400

    if not motivo:
        return jsonify(error="Motivo obrigatório"), 400

    post = Post.query.get(post_id)
    if not post:
        return jsonify(error="Post não encontrado"), 404

    # ❌ Não pode denunciar o próprio post
    if post.autor_id == user_id:
        return jsonify(error="Não podes denunciar o teu próprio post"), 403

    # 🚫 BLOQUEIO (em qualquer sentido)
    if existe_bloqueio(user_id, post.autor_id):
        return jsonify(error="Não podes denunciar este post"), 403

    # 🔁 Evitar denúncia duplicada
    existente = ReportPost.query.filter_by(
        post_id=post_id,
        user_id=user_id
    ).first()

    if existente:
        return jsonify(error="Post já denunciado por ti"), 409

    report = ReportPost(
        id=str(uuid.uuid4()),
        post_id=post_id,
        user_id=user_id,
        motivo=motivo
    )

    db.session.add(report)
    db.session.commit()

    return jsonify(status="ok")

#================= DENUNCIAR UTILIZADOR =================
@app.route("/users/<user_id>/report", methods=["POST"])
def report_user(user_id):
    data = request.get_json(force=True)
    reporter_id = data["user_id"]

    # Verificar se utilizador existe
    user = User.query.get(user_id)
    if not user:
        return jsonify(error="Utilizador não encontrado"), 404

    # 🚫 BLOQUEIO (em qualquer sentido)
    if existe_bloqueio(reporter_id, user_id):
        return jsonify(error="Não podes denunciar este utilizador"), 403

    report = ReportUser(
        id=str(uuid.uuid4()),
        reported_user_id=user_id,
        reporter_id=reporter_id,
        motivo=data.get("motivo")
    )

    db.session.add(report)
    db.session.commit()

    return jsonify(status="ok")

#================= SEGUIR / DEIXAR DE SEGUIR =================
@app.route("/users/<user_id>/follow", methods=["POST"])
def follow_user(user_id):
    data = request.get_json(force=True)
    follower_id = data["user_id"]

    # ❌ Não pode seguir a si próprio
    if str(follower_id) == str(user_id):
        return jsonify(error="Não podes seguir a ti próprio"), 400

    # 🚫 BLOQUEIO (em qualquer sentido)
    if existe_bloqueio(follower_id, user_id):
        return jsonify(error="Não podes seguir este utilizador"), 403

    existente = Follow.query.filter_by(
        follower_id=follower_id,
        followed_id=user_id
    ).first()

    # 🔁 Deixar de seguir
    if existente:
        db.session.delete(existente)
        db.session.commit()
        return jsonify(following=False)

    # ➕ Seguir
    db.session.add(Follow(
        id=str(uuid.uuid4()),
        follower_id=follower_id,
        followed_id=user_id
    ))

    # 🔔 Notificação
    db.session.add(Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        tipo="follow",
        origem_id=follower_id
    ))

    db.session.commit()
    return jsonify(following=True)


#================= BLOQUEAR UTILIZADOR =================
@app.route("/users/<user_id>/block", methods=["POST"])
def block_user(user_id):
    data = request.get_json(force=True)
    blocker_id = data["user_id"]

    # ❌ Não pode bloquear a si próprio
    if str(blocker_id) == str(user_id):
        return jsonify(error="Não podes bloquear a ti próprio"), 400

    # 🔎 Já existe bloqueio?
    existente = Block.query.filter_by(
        blocker_id=blocker_id,
        blocked_id=user_id
    ).first()

    if existente:
        return jsonify(status="already_blocked")

    # 🚫 Criar bloqueio
    block = Block(
        id=str(uuid.uuid4()),
        blocker_id=blocker_id,
        blocked_id=user_id
    )
    db.session.add(block)

    # 🧹 REMOVER FOLLOWS (mantido)
    Follow.query.filter(
        db.or_(
            db.and_(Follow.follower_id == blocker_id, Follow.followed_id == user_id),
            db.and_(Follow.follower_id == user_id, Follow.followed_id == blocker_id)
        )
    ).delete(synchronize_session=False)

    # 🧹 REMOVER NOTIFICAÇÕES ENTRE AMBOS
    Notification.query.filter(
        db.or_(
            db.and_(Notification.user_id == blocker_id, Notification.origem_id == user_id),
            db.and_(Notification.user_id == user_id, Notification.origem_id == blocker_id)
        )
    ).delete(synchronize_session=False)

    # 🧹 REMOVER LIKES ENTRE AMBOS
    Like.query.filter(
        db.or_(
            db.and_(Like.user_id == blocker_id, Like.post_id.in_(
                db.session.query(Post.id).filter(Post.autor_id == user_id)
            )),
            db.and_(Like.user_id == user_id, Like.post_id.in_(
                db.session.query(Post.id).filter(Post.autor_id == blocker_id)
            ))
        )
    ).delete(synchronize_session=False)

    # 🧹 REMOVER COMENTÁRIOS ENTRE AMBOS
    Comment.query.filter(
        db.or_(
            db.and_(Comment.autor_id == blocker_id, Comment.post_id.in_(
                db.session.query(Post.id).filter(Post.autor_id == user_id)
            )),
            db.and_(Comment.autor_id == user_id, Comment.post_id.in_(
                db.session.query(Post.id).filter(Post.autor_id == blocker_id)
            ))
        )
    ).delete(synchronize_session=False)

    # 🧹 REMOVER MENSAGENS ENTRE AMBOS
    Message.query.filter(
        db.or_(
            db.and_(Message.from_user_id == blocker_id, Message.to_user_id == user_id),
            db.and_(Message.from_user_id == user_id, Message.to_user_id == blocker_id)
        )
    ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify(status="ok")

# ================= DESBLOQUEAR =================
@app.route("/users/<int:user_id>/unblock", methods=["POST"])
def unblock_user(user_id):
    data = request.get_json(force=True)
    blocker_id = data["user_id"]

    # 🔎 Verificar se o bloqueio existe
    bloqueio = Block.query.filter_by(
        blocker_id=blocker_id,
        blocked_id=user_id
    ).first()

    if not bloqueio:
        return jsonify(status="not_blocked")

    # 🧱 Remover bloqueio
    db.session.delete(bloqueio)
    db.session.commit()

    return jsonify(status="ok")


#================= EDITAR POST =================
@app.route("/posts/<post_id>", methods=["PUT"])
def editar_post(post_id):
    data = request.get_json(force=True)

    post = Post.query.get(post_id)
    if not post or post.autor_id != data["user_id"]:
        return jsonify(error="Sem permissão"), 403

    post.texto = data.get("texto", post.texto)
    post.imagem = data.get("imagem", post.imagem)

    db.session.commit()
    return jsonify(status="ok")

#================= LISTAR COMENTÁRIOS (COM RESPOSTAS) =================
@app.route("/posts/<post_id>/comments", methods=["GET"])
def listar_comentarios(post_id):

    viewer_id = request.args.get("viewer_id", type=int)

    comments = Comment.query.filter_by(
        post_id=post_id
    ).order_by(Comment.data).all()

    res = []

    for c in comments:

        if viewer_id and existe_bloqueio(
            viewer_id,
            c.autor_id
        ):
            continue

        autor = User.query.get(c.autor_id)

        imagem_url = None

        if c.imagem:
            imagem_url = request.host_url[:-1] + c.imagem

        res.append({

            # 🔥 ID COMENTÁRIO
            "id": c.id,

            "texto": c.texto,

            # 🔥 IMAGEM
            "imagem": imagem_url,

            "data": c.data.strftime("%d/%m/%Y %H:%M"),

            "likes": CommentLike.query.filter_by(
                comment_id=c.id
            ).count(),

            "autor": {
                "id": autor.id,
                "username": autor.username,
                "avatar": autor.avatar
            }

        })

    return jsonify(res)
#================= LISTAR NOTIFICAÇÕES =================
@app.route("/notifications/<int:user_id>", methods=["GET"])
def listar_notificacoes(user_id):
    notifs = Notification.query.filter_by(
        user_id=user_id
    ).order_by(Notification.data.desc()).all()

    res = []
    for n in notifs:
        origem = User.query.get(n.origem_id)

        # 🔒 IGNORAR NOTIFICAÇÕES DE UTILIZADORES BLOQUEADOS
        if origem and existe_bloqueio(user_id, origem.id):
            continue

        res.append({
            "id": n.id,
            "tipo": n.tipo,
            "origem": origem.username if origem else None,
            "post_id": n.post_id,
            "comment_id": n.comment_id,
            "lida": n.lida,
            "data": n.data.strftime("%d/%m/%Y %H:%M")
        })

    return jsonify(res)

#================= MARCAR NOTIFICAÇÃO COMO LIDA =================
@app.route("/notifications/<notif_id>/read", methods=["POST"])
def marcar_notificacao_lida(notif_id):
    data = request.get_json(force=True)
    user_id = data.get("user_id")

    notif = Notification.query.get(notif_id)
    if not notif:
        return jsonify(error="Notificação não encontrada"), 404

    # 🔒 Garantir que a notificação pertence ao utilizador
    if notif.user_id != user_id:
        return jsonify(error="Sem permissão"), 403

    notif.lida = True
    db.session.commit()
    return jsonify(status="ok")

#================= PERFIL COMPLETO =================
@app.route("/users/<int:user_id>/profile", methods=["GET"])
def perfil_completo(user_id):
    viewer_id = request.args.get("viewer_id", type=int)

    user = User.query.get(user_id)
    if not user or user.apagado:
        return jsonify(error="Utilizador não encontrado"), 404

    # 🔒 BLOQUEIO TOTAL (não vê perfil)
    if viewer_id and existe_bloqueio(viewer_id, user_id):
        return jsonify(error="Perfil indisponível"), 403

    seguidores = Follow.query.filter_by(followed_id=user_id).count()
    seguindo = Follow.query.filter_by(follower_id=user_id).count()

    segue = False
    if viewer_id:
        segue = Follow.query.filter_by(
            follower_id=viewer_id,
            followed_id=user_id
        ).first() is not None
        
        return jsonify({
            "id": user.id,
            "nome": user.nome,
            "username": user.username,
            "avatar": user.avatar,
            "banner": user.banner,
            "bio": user.bio,
            "seguidores": seguidores,
            "seguindo": seguindo,
            "seguindo_este_user": segue
        })
#================= POSTS DO PERFIL =================
@app.route("/users/<int:user_id>/posts", methods=["GET"])
def posts_perfil(user_id):
    viewer_id = request.args.get("viewer_id", type=int)

    # 🔒 BLOQUEIO TOTAL
    if viewer_id and existe_bloqueio(viewer_id, user_id):
        return jsonify(error="Conteúdo indisponível"), 403

    posts = Post.query.filter_by(
        autor_id=user_id
    ).order_by(Post.data.desc()).all()

    res = []
    for p in posts:
        res.append({
            "id": p.id,
            "texto": p.texto,
            "imagem": p.imagem,
            "data": p.data.strftime("%d/%m/%Y %H:%M"),
            "likes": Like.query.filter_by(post_id=p.id).count(),
            "comentarios": Comment.query.filter_by(post_id=p.id).count(),
            "pode_editar": viewer_id == user_id,
            "pode_apagar": viewer_id == user_id
        })

    return jsonify(res)

#================= ENVIAR MENSAGEM =================
@app.route("/messages/send", methods=["POST"])
def enviar_mensagem():

    data = request.get_json(force=True)

    from_user = data["from_user_id"]
    to_user = data["to_user_id"]
    texto = (data.get("texto") or "").strip()

    if not texto:
        return jsonify(error="Mensagem vazia"), 400

    # 🔒 VER UTILIZADOR
    user = User.query.get(from_user)

    if not user:
        return jsonify(error="User não encontrado"), 404

    # 🚫 UTILIZADOR BLOQUEADO/SUSPENSO
    if user.bloqueado:
        return jsonify(
            error="Estás bloqueado e não podes enviar mensagens"
        ), 403

    # 🔒 BLOQUEIO TOTAL ENTRE USERS
    if existe_bloqueio(from_user, to_user):
        return jsonify(
            error="Não é possível enviar mensagem a este utilizador"
        ), 403

    msg = Message(
        id=str(uuid.uuid4()),
        from_user_id=from_user,
        to_user_id=to_user,
        texto=texto
    )

    db.session.add(msg)

    # 🔔 NOTIFICAÇÃO
    db.session.add(Notification(
        id=str(uuid.uuid4()),
        user_id=to_user,
        tipo="message",
        origem_id=from_user
    ))

    db.session.commit()

    return jsonify(status="ok")
    
#================= CONVERSA =================
@app.route("/messages/<int:user1>/<int:user2>", methods=["GET"])
def conversa(user1, user2):
    msgs = Message.query.filter(
        db.or_(
            db.and_(Message.from_user_id == user1, Message.to_user_id == user2),
            db.and_(Message.from_user_id == user2, Message.to_user_id == user1)
        )
    ).order_by(Message.data).all()

    res = []
    for m in msgs:
        res.append({
            "id": m.id,
            "from": m.from_user_id,
            "to": m.to_user_id,
            "texto": m.texto,
            "data": m.data.strftime("%d/%m/%Y %H:%M"),
            "lida": m.lida
        })

    return jsonify(res)

#================= MENSAGENS NÃO LIDAS =================
@app.route("/messages/unread/<int:user_id>", methods=["GET"])
def mensagens_nao_lidas(user_id):

    # Buscar mensagens não lidas
    msgs = Message.query.filter_by(
        to_user_id=user_id,
        lida=False
    ).all()

    total = 0
    for m in msgs:
        # 🔒 ignora mensagens de utilizadores bloqueados
        if not existe_bloqueio(user_id, m.from_user_id):
            total += 1

    return jsonify(total=total)

#================= MARCAR COMO LIDAS =================
@app.route("/messages/read/<int:user_id>/<int:from_user>", methods=["POST"])
def marcar_lidas(user_id, from_user):

    # 🔒 BLOQUEIO → não mexe nas mensagens
    if existe_bloqueio(user_id, from_user):
        return jsonify(status="bloqueado")

    Message.query.filter_by(
        to_user_id=user_id,
        from_user_id=from_user,
        lida=False
    ).update({"lida": True})

    db.session.commit()
    return jsonify(status="ok")

# ================= OBTER PERFIL =================
@app.route("/users/<int:user_id>", methods=["GET"])
def obter_user(user_id):

    user = User.query.get(user_id)

    if not user or user.apagado:
        return jsonify(error="Utilizador não encontrado"), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "apelido": user.nome,
        "avatar": user.avatar,
        "banner": user.banner,
        "moedas": user.moedas,
        "bio": user.bio
    })
# ================= ATUALIZAR PERFIL =================
@app.route("/users/update", methods=["POST"])
def atualizar_perfil():
    data = request.get_json(force=True)

    user_id = data.get("id")
    username = (data.get("username") or "").strip().lower()
    apelido = data.get("apelido")
    avatar = data.get("avatar")
    banner = data.get("banner")
    bio = data.get("bio", "")

    user = User.query.get(user_id)
    
    if not user:
        return jsonify(error="Utilizador não encontrado"), 404

    print("USER:", user_id, "MOEDAS:", user.moedas)
    if not user or user.apagado:
        return jsonify(error="Utilizador não encontrado"), 404

    bio = data.get("bio", "")
    
    if bio is not None:
        user.bio = bio[:175]

    # 🔒 garantir username único
    existente = User.query.filter(
        User.username == username,
        User.id != user_id
    ).first()

    if existente:
        return jsonify(error="Username já em uso"), 409

    user.username = username
    user.nome = apelido

    if avatar:
        user.avatar = avatar

    if banner:
        user.banner = banner

    db.session.commit()
    return jsonify(status="ok")

# ================= LOJA DE AVATARES =================

AVATARES_LOJA = [
    "1000135268",
    "1000135269",
    "1000135270",
    "1000135271",
    "1000135272",
    "1000135273",
    "1000135274",
    "1000135275",
    "1000135276",
    "1000135277", 
    "1000135278",
    "1000135279",
    "1000135280",
    "1000135281",
    "1000135282",
    "1000135283",
    "1000135284",
    "1000135285",
    "1000135286",
    "1000135287",
    "1000135288",
    "1000135289",
    "1000135290"
]

PRECO_AVATAR = 250  # moedas por avatar

# ================= BANNERS LOJA =================
BANNERS_LOJA = [
    "1000135250",
    "1000135255",
    "1000135291",
    "1000135292"
]

PRECO_BANNER = 500

@app.route("/avatars/loja", methods=["GET"])
def listar_loja_avatares():
    return jsonify({
        "avatares": AVATARES_LOJA,
        "preco": PRECO_AVATAR
    })

@app.route("/banners/loja", methods=["GET"])
def listar_loja_banners():
    return jsonify({
        "banners": BANNERS_LOJA,
        "preco": PRECO_BANNER
    })


@app.route("/avatars/comprar", methods=["POST"])
def comprar_avatar():
    data = request.get_json(force=True)

    user_id = data.get("user_id")
    avatar_id = data.get("avatar")

    if not user_id or not avatar_id:
        return jsonify(error="Dados inválidos"), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="Utilizador não encontrado"), 404

    # 🔥 buscar comprados
    comprados = json.loads(user.avatares_comprados or "[]")

    # ✅ já comprou → só equipa
    if avatar_id in comprados:
        user.avatar = avatar_id
        db.session.commit()

        return jsonify(
            status="equipado",
            novo_avatar=user.avatar,
            moedas_restantes=user.moedas
        )

    # 💰 PREÇO DINÂMICO
    if len(comprados) == 0:
        preco = 250
    else:
        preco = 500

    # ❌ dinheiro insuficiente
    if user.moedas < preco:
        return jsonify(error="Moedas insuficientes"), 403

    # 💸 descontar moedas
    user.moedas -= preco

    # 🧠 guardar compra
    comprados.append(avatar_id)
    user.avatares_comprados = json.dumps(comprados)

    # 🖼️ equipar automaticamente
    user.avatar = avatar_id

    db.session.commit()

    return jsonify(
        status="comprado",
        novo_avatar=user.avatar,
        moedas_restantes=user.moedas
    )


@app.route("/banners/comprar", methods=["POST"])
def comprar_banner():
    data = request.get_json(force=True)

    user_id = data.get("user_id")
    banner_id = data.get("banner")

    if not user_id or not banner_id:
        return jsonify(error="Dados inválidos"), 400

    if banner_id not in BANNERS_LOJA:
        return jsonify(error="Banner inválido"), 400

    user = User.query.get(user_id)
    if not user or user.apagado:
        return jsonify(error="Utilizador não encontrado"), 404

    # 📦 Lista de banners comprados
    import json
    comprados = json.loads(user.banners_comprados or "[]")

    # ===============================
    # ✅ JÁ COMPROU → só equipa
    # ===============================
    if banner_id in comprados:
        user.banner = banner_id
        db.session.commit()

        return jsonify(
            status="equipado",
            novo_banner=user.banner,
            moedas_restantes=user.moedas
        )

    # ===============================
    # 💰 PREÇO DINÂMICO
    # ===============================
    if len(comprados) == 0:
        preco = 250
    else:
        preco = 500

    print("PREÇO:", preco)
    print("MOEDAS:", user.moedas)

    # ===============================
    # ❌ MOEDAS INSUFICIENTES
    # ===============================
    if int(user.moedas) < int(preco):
        return jsonify(error="Moedas insuficientes"), 403

    # ===============================
    # 💸 DESCONTAR + GUARDAR
    # ===============================
    user.moedas -= preco
    comprados.append(banner_id)

    user.banners_comprados = json.dumps(comprados)

    # 🎯 EQUIPAR AUTOMATICAMENTE
    user.banner = banner_id

    db.session.commit()

    return jsonify(
        status="comprado",
        novo_banner=user.banner,
        moedas_restantes=user.moedas
    )
# ================= ATUALIZAR MOEDAS =================
@app.route("/users/moedas", methods=["POST"])
def atualizar_moedas():

    data = request.get_json(force=True)

    user_id = data.get("user_id")
    moedas = data.get("moedas")

    if user_id is None or moedas is None:
        return jsonify(error="Dados inválidos"), 400

    user = User.query.get(user_id)

    if not user or user.apagado:
        return jsonify(error="Utilizador não encontrado"), 404

    print("ATUALIZAR MOEDAS:", user_id, "->", moedas)

    user.moedas = int(moedas)
    db.session.commit()

    return jsonify(
        status="ok",
        moedas=user.moedas
    )

@app.route("/users/add-moedas", methods=["POST"])
def adicionar_moedas():
    data = request.get_json()

    user_id = data.get("user_id")
    moedas = data.get("moedas", 0)

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    user.moedas += int(moedas)

    db.session.commit()

    return jsonify({
        "status": "ok",
        "moedas": user.moedas
    })

@app.route('/banner/<filename>')
def servir_banner(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, 'static', 'banners')

    print("A SERVIR BANNER:", filename)

    for ext in [".png", ".jpg", ".jpeg"]:
        file = filename + ext
        full_path = os.path.join(path, file)

        if os.path.exists(full_path):
            return send_from_directory(path, file)

    return "Banner não encontrado", 404

# =========================================================
# ADMIN
# =========================================================

@app.route("/admin/promote", methods=["POST"])
def promote_user():

    data = request.get_json(force=True)

    admin_id = session.get("user_id")
    target = data.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    # 🔥 FORÇAR INT SEMPRE
    try:
        user_id = int(target)
    except:
        return jsonify(error="ID inválido"), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    user.role = "admin"
    db.session.commit()

    return jsonify(status="ok", msg=f"{user.username} agora é admin")
    

# =========================================================
# REMOVER ADMIN
# =========================================================

@app.route("/admin/demote", methods=["POST"])
def demote_user():

    data = request.get_json(force=True)

    admin_id = session.get("user_id")
    target_id = data.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(target_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    # impedir remover a si próprio
    if user.id == admin_id:
        return jsonify(
            error="Não podes remover o teu próprio admin"
        ), 403

    user.role = "user"

    db.session.commit()

    return jsonify(status="ok")


# =========================================================
# LOGS ADMIN
# =========================================================

class AdminLog(db.Model):

    __tablename__ = "admin_logs"

    id = db.Column(db.String, primary_key=True)

    admin_id = db.Column(db.Integer)
    alvo_id = db.Column(db.Integer)

    acao = db.Column(db.String(100))
    motivo = db.Column(db.String(255))

    data = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# SISTEMA IA
# =========================================================

IA_SUSPENSOES = {
    1: timedelta(hours=3),
    2: timedelta(hours=12),
    3: timedelta(days=1),
    4: timedelta(days=3),
    5: timedelta(days=7),
}

def verificar_ban_ia(user):

    # 🔴 BANIMENTO PERMANENTE
    if user.ia_banido:
        return {
            "status": "banido",
            "remaining": None
        }

    # 🟡 SUSPENSÃO TEMPORÁRIA
    if user.ia_suspenso_ate:

        remaining = (user.ia_suspenso_ate - datetime.utcnow()).total_seconds()

        if remaining > 0:
            return {
                "status": "suspenso",
                "remaining": int(remaining)
            }

        # auto unlock
        user.ia_suspenso_ate = None
        db.session.commit()

    # 🟢 LIBERADO
    return {
        "status": "ativo",
        "remaining": 0
    }
# =========================================================
# ADMIN APAGAR POST
# =========================================================

@app.route("/admin/posts/<post_id>", methods=["DELETE"])
def admin_delete_post(post_id):

    data = request.get_json(force=True)

    admin_id = session.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    post = Post.query.get(post_id)

    if not post:
        return jsonify(error="Post não encontrado"), 404

    # apagar likes
    Like.query.filter_by(
        post_id=post.id
    ).delete()

    # apagar comentários
    Comment.query.filter_by(
        post_id=post.id
    ).delete()

    # apagar notificações
    Notification.query.filter_by(
        post_id=post.id
    ).delete()

    db.session.delete(post)

    db.session.commit()

    return jsonify(status="ok")


# =========================================================
# ADMIN APAGAR COMENTÁRIO
# =========================================================

@app.route("/admin/comments/<comment_id>", methods=["DELETE"])
def admin_delete_comment(comment_id):

    data = request.get_json(force=True)

    admin_id = session.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    comment = Comment.query.get(comment_id)

    if not comment:
        return jsonify(error="Comentário não encontrado"), 404

    # apagar likes comentário
    CommentLike.query.filter_by(
        comment_id=comment.id
    ).delete()

    db.session.delete(comment)

    db.session.commit()

    return jsonify(status="ok")


# =========================================================
# BANIR USER
# =========================================================

@app.route("/admin/ban/<int:user_id>", methods=["POST"])
def admin_ban_user(user_id):

    data = request.get_json(force=True)

    admin_id = session.get("user_id")
    motivo = data.get(
        "motivo",
        "Violação das regras"
    )

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    if user.role == "admin":
        return jsonify(
            error="Não podes banir outro admin"
        ), 403

    # =========================================
    # BANIMENTO
    # =========================================

    user.banido = True
    user.email_banido = True
    user.ban_reason = motivo

    # =========================================
    # APAGAR POSTS
    # =========================================

    posts = Post.query.filter_by(
        autor_id=user.id
    ).all()

    for p in posts:

        Like.query.filter_by(
            post_id=p.id
        ).delete()

        Comment.query.filter_by(
            post_id=p.id
        ).delete()

        Notification.query.filter_by(
            post_id=p.id
        ).delete()

        db.session.delete(p)

    # =========================================
    # APAGAR COMENTÁRIOS
    # =========================================

    Comment.query.filter_by(
        autor_id=user.id
    ).delete()

    # =========================================
    # APAGAR LIKES
    # =========================================

    Like.query.filter_by(
        user_id=user.id
    ).delete()

    CommentLike.query.filter_by(
        user_id=user.id
    ).delete()

    # =========================================
    # APAGAR MENSAGENS
    # =========================================

    Message.query.filter(
        db.or_(
            Message.from_user_id == user.id,
            Message.to_user_id == user.id
        )
    ).delete()

    # =========================================
    # APAGAR FOLLOWS
    # =========================================

    Follow.query.filter(
        db.or_(
            Follow.follower_id == user.id,
            Follow.followed_id == user.id
        )
    ).delete()

    # =========================================
    # APAGAR NOTIFICAÇÕES
    # =========================================

    Notification.query.filter(
        db.or_(
            Notification.user_id == user.id,
            Notification.origem_id == user.id
        )
    ).delete()

    db.session.commit()

    return jsonify(status="ok")


# =========================================================
# DESBANIR USER
# =========================================================

@app.route("/admin/unban/<int:user_id>", methods=["POST"])
def admin_unban_user(user_id):

    data = request.get_json(force=True)

    admin_id = session.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    user.banido = False
    user.email_banido = False
    user.ban_reason = None

    db.session.commit()

    return jsonify(status="ok")


# =========================================================
# BLOQUEAR USER
# =========================================================

@app.route("/admin/block/<int:user_id>", methods=["POST"])
def admin_block_user(user_id):

    data = request.get_json(force=True)

    admin_id = session.get("user_id")

    dias = int(data.get("dias", 7))

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    user.bloqueado = True
    user.bloqueado_ate = (
        datetime.utcnow() + timedelta(days=dias)
    )

    db.session.commit()

    return jsonify(status="ok")


# =========================================================
# DESBLOQUEAR USER
# =========================================================

@app.route("/admin/unblock/<int:user_id>", methods=["POST"])
def admin_unblock_user(user_id):

    data = request.get_json(force=True)

    admin_id = session.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    user.bloqueado = False
    user.bloqueado_ate = None

    db.session.commit()

    return jsonify(status="ok")


# =========================================================
# SUSPENDER IA
# =========================================================

@app.route("/admin/suspend-ia/<int:user_id>", methods=["POST"])
def suspend_ia(user_id):

    data = request.get_json(force=True)

    admin_id = session.get("user_id")
    tempo = data.get("horas")  # vem tipo "3 horas"

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    # 🔥 CONVERSOR DO TEU COMBOBOX
    def converter_tempo(txt):

        if not txt:
            return 0

        txt = txt.lower().strip()

        if "permanente" in txt:
            return -1

        if "semana" in txt:
            return int(txt.split()[0]) * 24 * 7

        if "dia" in txt:
            return int(txt.split()[0]) * 24

        if "hora" in txt:
            return int(txt.split()[0])

        return 0

    horas = converter_tempo(tempo)

    # ⛔ validação
    if horas == 0:
        return jsonify(error="Tempo inválido"), 400

    # ♾ permanente
    if horas == -1:
        user.ia_banido = True
        user.ia_suspenso_ate = None

        db.session.commit()

        return jsonify(status="banido")

    # ⏳ suspensão normal
    user.ia_banido = False
    user.ia_suspenso_ate = datetime.utcnow() + timedelta(hours=horas)

    db.session.commit()

    return jsonify(
        status="suspenso",
        horas=horas,
        remaining=horas * 3600
    )
# =========================================================
# DESSUSPENDER IA
# =========================================================

@app.route("/admin/unsuspend-ia/<int:user_id>", methods=["POST"])
def admin_unsuspend_ia(user_id):

    data = request.get_json(force=True)

    admin_id = session.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    user.ia_suspenso_ate = None

    db.session.commit()

    return jsonify(status="ok")


# =========================================================
# BANIR IA PERMANENTE
# =========================================================
@app.route("/admin/ban-ia/<int:user_id>", methods=["POST"])
def ban_ia(user_id):

    data = request.get_json(force=True)
    admin_id = session.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    # 🔴 BAN PERMANENTE
    user.ia_banido = True
    user.ia_suspenso_ate = None

    db.session.commit()

    return jsonify(status="banido")

# =========================================================
# DESBANIR IA
# =========================================================

@app.route("/admin/unban-ia/<int:user_id>", methods=["POST"])
def admin_unban_ia(user_id):

    data = request.get_json(force=True)

    admin_id = session.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    user.ia_banido = False
    user.warning_count = 0
    user.ia_ban_reason = None

    db.session.commit()

    return jsonify(status="ok")

@app.route("/admin/add-moedas", methods=["POST"])
def admin_add_moedas():

    data = request.get_json(force=True)

    admin_id = session.get("user_id")
    user_id = data.get("user_id")
    moedas = int(data.get("moedas", 0))

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    user.moedas += moedas

    db.session.commit()

    return jsonify(
        status="ok",
        moedas=user.moedas
    )

@app.route("/admin/toggle-public", methods=["POST"])
def toggle_public_admin():

    data = request.get_json(force=True)

    admin_id = session.get("user_id")
    visible = bool(data.get("visible"))

    user = User.query.get(admin_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user.mostrar_publicamente = visible

    db.session.commit()

    return jsonify(
        status="ok",
        visible=user.mostrar_publicamente
    )

@app.route("/users/list", methods=["GET"])
def listar_users():

    users = User.query.filter_by(
        apagado=False
    ).all()

    res = []

    for u in users:

        res.append({
            "id": u.id,
            "username": u.username,
            "avatar": u.avatar,
            "role": u.role
        })

    return jsonify(res)

@app.route("/admin/admins", methods=["GET"])
def listar_admins_admin():

    requester_id = request.args.get("user_id", type=int)

    # só admins podem ver tudo
    if not is_admin(requester_id):
        return jsonify(error="Sem permissão"), 403

    admins = User.query.filter_by(role="admin").all()

    res = []

    for u in admins:
        res.append({
            "id": u.id,
            "username": u.username,
            "nome": u.nome,
            "avatar": u.avatar,
            "banner": u.banner,
            "bio": u.bio,
            "mostrar_publicamente": u.mostrar_publicamente
        })

    return jsonify(res)

@app.route("/admins", methods=["GET"])
def listar_admins_publico():

    admins = User.query.filter_by(
        role="admin",
        mostrar_publicamente=True
    ).all()

    res = []

    for u in admins:
        res.append({
            "id": u.id,
            "username": u.username,
            "nome": u.nome,
            "avatar": u.avatar,
            "banner": u.banner,
            "bio": u.bio
        })

    return jsonify(res)

def is_admin(user_id=None):

    if user_id is None:
        user_id = session.get("user_id")

    if not user_id:
        return False

    try:
        user_id = int(user_id)
    except:
        return False

    user = User.query.get(user_id)

    if not user:
        return False

    # 👑 OWNER FIXO POR ID
    if user.id == 1:
        return True

    return user.role == "admin"
                
@app.route("/admin/delete-user/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):

    data = request.get_json(force=True)
    admin_id = session.get("user_id")

    # 🔒 só admin
    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    # 🚫 impedir apagar outro admin (opcional)
    if user.role == "admin":
        return jsonify(error="Não podes apagar outro admin"), 403

    # ===============================
    # 🧹 LIMPEZA COMPLETA (igual ao ban)
    # ===============================

    Post.query.filter_by(autor_id=user.id).delete()

    Comment.query.filter_by(autor_id=user.id).delete()

    Like.query.filter_by(user_id=user.id).delete()

    CommentLike.query.filter_by(user_id=user.id).delete()

    Message.query.filter(
        db.or_(
            Message.from_user_id == user.id,
            Message.to_user_id == user.id
        )
    ).delete()

    Follow.query.filter(
        db.or_(
            Follow.follower_id == user.id,
            Follow.followed_id == user.id
        )
    ).delete()

    Notification.query.filter(
        db.or_(
            Notification.user_id == user.id,
            Notification.origem_id == user.id
        )
    ).delete()

    # 🗑 apagar user
    db.session.delete(user)
    db.session.commit()

    return jsonify(status="ok")

@app.route("/admin/avisar-user", methods=["POST"])
def avisar_user():

    data = request.get_json(force=True)

    admin_id = session.get("user_id")
    user_id = data.get("user_id")
    motivo = (data.get("motivo") or "").strip()

    # 🔒 valida admin
    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    if not motivo:
        return jsonify(error="Motivo obrigatório"), 400

    # ===============================
    # 📌 incrementar contador de avisos
    # ===============================
    user.avisos += 1

    # ===============================
    # 🔔 criar notificação
    # ===============================
    db.session.add(Notification(
        id=str(uuid.uuid4()),
        user_id=user.id,
        tipo="admin_warning",
        origem_id=admin_id,
        post_id=None,
        comment_id=None
    ))

    db.session.commit()

    return jsonify(
        status="ok",
        msg="Aviso enviado"
    )

@app.route("/ia/status/<int:user_id>", methods=["GET"])
def ia_status(user_id):

    user = User.query.get(user_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    if user.ia_banido:
        return jsonify(status="banido")

    if user.ia_suspenso_ate:
        remaining = (user.ia_suspenso_ate - datetime.utcnow()).total_seconds()

        if remaining > 0:
            return jsonify(
                status="suspenso",
                remaining=int(remaining)
            )

    return jsonify(status="ativo")

@app.route("/comments/<comment_id>", methods=["DELETE"])
def apagar_comentario(comment_id):

    data = request.get_json(force=True)

    user_id = data.get("user_id")

    if not user_id:
        return jsonify(error="User inválido"), 400

    comment = Comment.query.get(comment_id)

    if not comment:
        return jsonify(error="Comentário não encontrado"), 404

    # 🔒 Apenas autor ou admin
    if comment.autor_id != user_id and not is_admin(user_id):
        return jsonify(error="Sem permissão"), 403

    # apagar likes
    CommentLike.query.filter_by(
        comment_id=comment.id
    ).delete()

    # apagar notificações
    Notification.query.filter_by(
        comment_id=comment.id
    ).delete()

    db.session.delete(comment)

    db.session.commit()

    return jsonify(status="ok")

@app.route("/login/google")
def login_google():
    redirect_uri = url_for("google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)
    
@app.route("/auth/google/callback")
def google_callback():

    google.authorize_access_token()

    resp = google.get("https://openidconnect.googleapis.com/v1/userinfo")
    info = resp.json()

    email = info["email"]
    google_name = info.get("name")
    google_picture = info.get("picture")

    user = User.query.filter_by(email=email).first()

    # 🔥 TOKEN ÚNICO PARA TKINTER
    global google_login_state
    
    google_login_state = {
        "logged": True,
        "exists": (
            user is not None
            and user.username is not None
        ),
        "id": (
            user.id
            if user and user.username
            else None
        ),
        "email": email,
        "username": (
            user.username
            if user else None
        ),
        "picture": google_picture,
        "google_name": google_name
    }

    return f"""
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>Login concluído</title>

<style>
body {{
    margin:0;
    height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    font-family:Arial;
    background:linear-gradient(135deg,#7dd3fc,#2563eb,#000);
    color:white;
}}

.card {{
    background:rgba(255,255,255,0.08);
    padding:40px;
    border-radius:20px;
    text-align:center;
}}

.btn {{
    padding:12px 22px;
    border:none;
    border-radius:12px;
    background:linear-gradient(90deg,#38bdf8,#1d4ed8);
    color:white;
    font-weight:bold;
    cursor:pointer;
}}
</style>
</head>

<body>

<div class="card">
    <h1>Login concluído</h1>
    <p>Enviar dados para o AERON?</p>

    <button class="btn">
    Já podes voltar ao AERON
</button>

</body>
</html>
"""
    
@app.route("/google-login/status")
def google_login_status():
    global google_login_state
    return jsonify(google_login_state)

@app.route("/register-google", methods=["POST"])
def register_google():

    data = request.get_json(force=True)

    username = (data.get("username") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not username or not email or not password:
        return jsonify(
            status="error",
            msg="Dados inválidos"
        ), 400

    banido_email = User.query.filter_by(
        email=email,
        email_banido=True
    ).first()

    if banido_email:
        return jsonify(
            status="error",
            msg="Este email foi permanentemente banido"
        ), 403

    if User.query.filter_by(username=username).first():
        return jsonify(
            status="error",
            msg="Username já existe"
        ), 409

    if User.query.filter_by(email=email).first():
        return jsonify(
            status="error",
            msg="Email já existe"
        ), 409

    user = User(
        username=username,
        email=email,
        password=hash_password(password),

        provider="google",

        google_name=data.get("google_name"),
        google_picture=data.get("google_picture"),

        avatar="default",
        banner="bannerdefault",

        avatares_comprados=json.dumps([]),
        banners_comprados=json.dumps([]),

        moedas=0
    )
    
    db.session.add(user)
    db.session.commit()
    
    google_login_state["exists"] = True
    google_login_state["id"] = user.id
    google_login_state["username"] = username
    
    return jsonify(
        status="ok",
        id=user.id
    )

@app.route("/sessions/<int:user_id>")
def get_sessions(user_id):

    sessoes = UserSession.query.filter_by(
        user_id=user_id,
        active=True
    ).all()

    resultado = []

    for s in sessoes:

        resultado.append({
            "id": s.id,
            "platform": s.platform,
            "ip": s.ip_address,
            "location": s.location,
            "remember_me": s.remember_me,
            "created_at": str(s.created_at)
        })

    return jsonify(resultado)

@app.route(
    "/terminate-session/<int:session_id>",
    methods=["POST"]
)
def terminate_session_web(session_id):

    user_id = session.get("security_user")

    if not user_id:
        return redirect("/security-login")

    sessao = UserSession.query.get(session_id)

    if not sessao:
        return redirect("/security-sessions")

    if sessao.user_id != user_id:
        return redirect("/security-sessions")

    sessao.active = False
    sessao.terminated_at = datetime.utcnow()

    db.session.commit()

    return redirect("/security-sessions")
    
@app.route("/auto-login", methods=["POST"])
def auto_login():

    data = request.get_json(force=True)

    token = data.get("session_token")

    sessao = UserSession.query.filter_by(
        session_token=token,
        active=True
    ).first()

    if not sessao:
        return jsonify(
            status="error"
        ), 401

    user = User.query.get(sessao.user_id)

    if not user:
        return jsonify(
            status="error"
        ), 404

    return jsonify(
        status="ok",
        id=user.id,
        username=user.username,
        avatar=user.avatar,
        role=user.role
    )

@app.route("/security-login", methods=["GET", "POST"])
def security_login():

    # 🔹 Apenas mostra a página no GET (sem erros)
    if request.method == "GET":
        return render_template("security_login.html")

    data = request.form

    username = (data.get("username") or "").strip().lower()
    password = data.get("password")

    # 🔴 validação básica
    if not username or not password:
        return render_template(
            "security_login.html",
            erro="Preencha todos os campos"
        )

    # 🔍 procurar utilizador
    user = User.query.filter_by(username=username).first()

    if not user:
        return render_template(
            "security_login.html",
            erro="Utilizador não encontrado"
        )

    # 🔒 password
    if user.password != hash_password(password):
        return render_template(
            "security_login.html",
            erro="Password inválida"
        )

    # 🚫 conta banida
    if user.banido:
        return render_template(
            "security_login.html",
            erro="Conta banida"
        )

    # 🗑 conta apagada
    if user.apagado:
        return render_template(
            "security_login.html",
            erro="Conta apagada"
        )

    # ✅ login OK
    session["security_user"] = user.id

    return redirect("/security-sessions")
    
@app.route("/security-sessions")
def security_sessions():

    user_id = session.get("security_user")

    if not user_id:
        return redirect("/security-login")

    user = User.query.get(user_id)

    if not user:
        session.clear()
        return redirect("/security-login")

    sessoes = UserSession.query.filter_by(
        user_id=user_id
    ).order_by(
        UserSession.created_at.desc()
    ).all()

    lista_sessoes = []

    for s in sessoes:

        lista_sessoes.append({
            "id": s.id,
            "platform": s.platform,
            "ip": s.ip_address,
            "location": s.location,
            "remember_me": s.remember_me,
            "active": s.active,
            "created_at": s.created_at.strftime(
                "%d/%m/%Y %H:%M:%S"
            ) if s.created_at else "-"
        })

    return render_template(
        "security_sessions.html",
        user=user,
        sessoes=lista_sessoes
    )

@app.route("/check-session", methods=["POST"])
def check_session():

    data = request.get_json(force=True)
    token = data.get("session_token")

    if not token:
        return jsonify(active=False), 400

    sessao = UserSession.query.filter_by(
        session_token=token
    ).first()

    # ❌ sessão não existe
    if not sessao:
        return jsonify(active=False), 404

    # ❌ sessão existe mas está terminada
    if not sessao.active:
        return jsonify(active=False)

    # ✅ sessão válida
    return jsonify(active=True)

@app.route("/verify-email/<token>")
def verify_email(token):

    user = User.query.filter_by(email_token=token).first()

    # ❌ token não existe ou já foi apagado
    if not user:
        return render_template("email_invalid.html")

    # ❌ já foi verificado antes (segurança extra)
    if user.email_verificado:
        return render_template("email_invalid.html")

    # ✔️ primeira verificação válida
    user.email_verificado = True
    user.email_token = None

    db.session.commit()

    return render_template("email_verified.html")
    
@app.route("/send-verification", methods=["POST"])
def send_verification():
    data = request.get_json(force=True)
    email = data.get("email")

    if not email:
        return jsonify({"status": "error", "msg": "Email obrigatório"}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"status": "ok"}), 200

    # se já verificado não faz nada
    if user.email_verificado:
        return jsonify({"status": "ok"}), 200

    now = datetime.utcnow()

    # verifica cooldown de 30 segundos
    if user.last_verification_request:
        diff = now - user.last_verification_request
        if diff < timedelta(seconds=30):
            return jsonify({
                "status": "error",
                "msg": "Aguarda 30 segundos antes de reenviar"
            }), 429

    # limite de tentativas
    if user.email_verification_attempts >= 5:
        return jsonify({
            "status": "error",
            "msg": "Limite de tentativas atingido"
        }), 429

    # atualizar estado
    user.email_verification_attempts += 1
    user.last_verification_request = now

    token = secrets.token_hex(32)
    user.email_token = token

    db.session.commit()

    return jsonify({
        "status": "ok",
        "token": token,
        "username": user.username
    })
    
@app.route("/check-email", methods=["POST"])
def check_email_exists():
    data = request.json
    email = data.get("email")

    user = User.query.filter_by(email=email).first()

    return jsonify({
        "exists": user is not None
    })

@app.route("/get-user", methods=["POST"])
def get_user():
    data = request.get_json(force=True)
    email = data.get("email")

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"status": "error"}), 404

    return jsonify({
        "status": "ok",
        "username": user.username,
        "email": user.email
    })

@app.route("/confirm-data/<int:user_id>")
def confirm_data(user_id):

    user = User.query.get(user_id)

    if not user:
        return "Utilizador não encontrado", 404

    user.dados_confirmados = True
    db.session.commit()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Confirmação AERON</title>
    </head>

    <body style="
        margin:0;
        background:linear-gradient(135deg,#0f172a,#111827);
        font-family:Arial;
        color:white;
        display:flex;
        justify-content:center;
        align-items:center;
        height:100vh;
    ">

        <div style="
            width:520px;
            background:#111827;
            border:1px solid #1f2937;
            border-radius:18px;
            padding:35px;
            text-align:center;
            box-shadow:0 0 40px rgba(0,0,0,0.6);
        ">

            <!-- LOGO -->
            <img src="https://recuperar-conta-app-uza0.onrender.com/static/LOGO/AERON.png"
                 style="width:140px;margin-bottom:20px;">

            <div style="font-size:60px;">✅</div>

            <h1 style="margin-top:10px;">
                Dados confirmados
            </h1>

            <p style="color:#9ca3af;line-height:1.6;">
                A tua conta foi validada com sucesso.<br>
                Nenhuma ação adicional é necessária.
            </p>

            <div style="
                margin-top:25px;
                padding:15px;
                background:#0b1220;
                border-radius:12px;
                border:1px solid #1f2937;
            ">
                <p style="margin:0;color:#22c55e;">
                    ✔ Conta ativa e verificada
                </p>
            </div>

            <a href="javascript:window.close()" style="
                display:inline-block;
                margin-top:25px;
                padding:12px 22px;
                background:#2563eb;
                color:white;
                text-decoration:none;
                border-radius:10px;
                font-weight:bold;
            ">
                Fechar
            </a>

        </div>

    </body>
    </html>
    """


@app.route("/feedback/<int:user_id>")
def feedback_page(user_id):

    user = User.query.get(user_id)

    if not user:
        return "Utilizador não encontrado", 404

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Feedback AERON</title>
</head>

<body style="margin:0;background:linear-gradient(135deg,#0f172a,#0b1220);font-family:Arial;color:white;display:flex;justify-content:center;align-items:center;min-height:100vh;">

    <div style="width:650px;background:#111827;border:1px solid #1f2937;border-radius:18px;padding:30px;box-shadow:0 0 40px rgba(0,0,0,0.6);">

        <div style="text-align:center;margin-bottom:10px;">
            <img src="https://recuperar-conta-app-uza0.onrender.com/static/LOGO/AERON.png" style="width:140px;">
        </div>

        <h1>⚠ Reportar problema nos dados</h1>

        <p style="color:#9ca3af;margin-bottom:25px;">
            Conta: <b>{user.username}</b> • {user.email}
        </p>

        <form method="POST" action="/feedback-submit">

            <input type="hidden" name="user_id" value="{user_id}">

            <textarea name="message" required
                style="width:100%;height:140px;background:#0b1220;border:1px solid #1f2937;color:white;border-radius:12px;padding:12px;outline:none;resize:none;"
                placeholder="Descreve o problema..."></textarea>

            <br><br>

            <button type="submit"
                style="width:100%;padding:14px;background:#ef4444;border:none;color:white;font-weight:bold;border-radius:12px;cursor:pointer;font-size:15px;">
                Enviar feedback
            </button>

        </form>

        <div style="margin-top:20px;padding:15px;background:#0b1220;border-radius:12px;border:1px solid #1f2937;">
            <p style="margin:0;color:#facc15;font-size:13px;">
                ⚠ A equipa AERON irá analisar o teu pedido manualmente.
            </p>
        </div>

    </div>

</body>
</html>
"""

@app.route("/feedback-submit", methods=["POST"])
def submit_feedback():

    user_id = request.form.get("user_id")
    message = request.form.get("message")

    user = User.query.get(user_id)

    if not user:
        return "Utilizador inválido", 404

    fb = Feedback(
        user_id=user_id,
        message=message,
        status="open"
    )

    db.session.add(fb)
    db.session.commit()

    return "Feedback enviado com sucesso!"

@app.route("/admin/feedback/<int:feedback_id>")
def open_feedback(feedback_id):

    fb = Feedback.query.get(feedback_id)

    if not fb:
        return "Feedback não encontrado", 404

    user = User.query.get(fb.user_id)

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Feedback</title>
</head>

<body style="margin:0;background:#0f172a;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;min-height:100vh;">

<div style="width:700px;background:#111827;padding:25px;border-radius:16px;border:1px solid #1f2937;">

    <h2>📩 Feedback</h2>

    <p><b>Utilizador:</b> {user.username}</p>
    <p><b>Email:</b> {user.email}</p>
    <p><b>Mensagem:</b> {fb.message}</p>
    <p><b>Status:</b> {fb.status}</p>

    <hr style="margin:20px 0;border:1px solid #1f2937;">

    <form method="POST" action="/admin/resolve/{fb.id}">

        <input type="text" name="admin_name" placeholder="Nome do admin" required
            style="width:100%;padding:10px;margin-bottom:10px;border-radius:8px;border:none;">

        <input type="number" name="rating" min="0" max="5" placeholder="Rating (0-5)" required
            style="width:100%;padding:10px;margin-bottom:10px;border-radius:8px;border:none;">

        <button type="submit"
            style="width:100%;padding:12px;background:#22c55e;color:black;font-weight:bold;border-radius:10px;border:none;">
            Resolver feedback
        </button>

    </form>

</div>

</body>
</html>
"""

@app.route("/admin/resolve/<int:feedback_id>", methods=["POST"])
def resolve_feedback(feedback_id):

    fb = Feedback.query.get(feedback_id)

    if not fb:
        return "Feedback não encontrado", 404

    fb.status = "closed"
    fb.admin_name = request.form.get("admin_name")
    fb.rating = int(request.form.get("rating"))

    db.session.commit()

    return "Feedback resolvido com sucesso!"

@app.route("/admin/user/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):

    user = User.query.get(user_id)

    if not user:
        return "User not found", 404

    if request.method == "POST":

        user.email = request.form.get("email")
        user.email_recuperacao = request.form.get("email_recuperacao")
        user.password = request.form.get("password")  # ideal: hash depois
        user.perguntas_recuperacao = request.form.get("perguntas")

        db.session.commit()

        return "Utilizador atualizado com sucesso!"

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Editar Utilizador</title>
</head>

<body style="margin:0;background:#0f172a;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;min-height:100vh;">

<div style="width:600px;background:#111827;padding:20px;border-radius:12px;">

<h2>Editar utilizador</h2>

<form method="POST">

    <input name="email" value="{user.email}" style="width:100%;padding:10px;margin:5px 0;">
    <input name="email_recuperacao" value="{user.email_recuperacao}" style="width:100%;padding:10px;margin:5px 0;">
    <input name="password" placeholder="Nova password" style="width:100%;padding:10px;margin:5px 0;">

    <textarea name="perguntas" style="width:100%;height:120px;">
{user.perguntas_recuperacao}
    </textarea>

    <button type="submit" style="width:100%;padding:12px;background:#22c55e;">
        Atualizar
    </button>

</form>

</div>

</body>
</html>
"""

@app.route("/admin/feedbacks")
def admin_feedbacks():

    open_fb = Feedback.query.filter_by(status="open").order_by(Feedback.id.desc()).all()
    closed_fb = Feedback.query.filter_by(status="closed").order_by(Feedback.id.desc()).all()

    def card(f, color):
        return f"""
        <div style="background:#0b1220;padding:12px;border-radius:12px;margin-bottom:10px;border:1px solid #1f2937;">
            <p><b>User ID:</b> {f.user_id}</p>
            <p>{f.message}</p>

            <a href="/admin/feedback/{f.id}"
               style="display:inline-block;margin-top:10px;padding:8px 12px;background:{color};color:white;border-radius:8px;text-decoration:none;">
               Abrir
            </a>
        </div>
        """

    open_html = "".join(card(f, "#facc15") for f in open_fb)
    closed_html = "".join(card(f, "#22c55e") for f in closed_fb)

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Admin Panel</title>
</head>

<body style="margin:0;font-family:Arial;background:#0f172a;color:white;">

    <div style="text-align:center;padding:20px;">
        <h1>📊 Painel Admin</h1>
    </div>

    <div style="display:flex;gap:20px;padding:20px;">

        <div style="flex:1;">
            <h2>🟡 Pendentes</h2>
            {open_html if open_html else "<p>Sem feedbacks</p>"}
        </div>

        <div style="flex:1;">
            <h2>🟢 Resolvidos</h2>
            {closed_html if closed_html else "<p>Sem feedbacks</p>"}
        </div>

    </div>

</body>
</html>
"""

def stars(n):
    if not n:
        return "☆☆☆☆☆"
    return "★" * n + "☆" * (5 - n)
#================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
