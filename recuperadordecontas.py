from flask import Flask, render_template, request, jsonify, send_from_directory, session, url_for,redirect
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
    recovery_token = db.Column(db.String(64), nullable=True)

    moedas = db.Column(db.Integer, default=0)

    ativo = db.Column(db.Boolean, default=True)  # Define se a conta está ativa
    desativado_em = db.Column(db.DateTime, nullable=True)  # Data de desativação
    reactivation_code = db.Column(db.String(32), nullable=True)  # Código de reativação temporário
    apagado = db.Column(db.Boolean, default=False)  # Marca se a conta foi apagada
    avatar = db.Column(db.String(50), nullable=True)  # ✅ AVATAR (ID DO AVATAR)
    ultima_recompensa_post = db.Column(db.DateTime, nullable=True)

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

class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    title = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(30), default="normal")
    status = db.Column(db.String(20), default="open")

    rating = db.Column(db.Integer, nullable=True)

    close_pending = db.Column(db.Boolean, default=False)
    close_requested_by = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TicketMessage(db.Model):
    __tablename__ = "ticket_messages"

    id = db.Column(db.Integer, primary_key=True)

    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)

    sender = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

    print("USER_ID:", user_id)

    if user:
        print("ROLE:", user.role)
    else:
        print("USER NÃO EXISTE")

    return user and user.role == "admin"

def admin_required(user_id):
    user = User.query.get(user_id)
    if not user or user.role != "admin":
        return False, jsonify(error="Sem permissão"), 403
    return True, user

def admin_ticket_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")

        if not user_id:
            return jsonify(error="Sessão inválida"), 401

        if not is_admin(user_id):
            return jsonify(error="Sem permissão"), 403

        return func(*args, **kwargs)

    return wrapper
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
    import secrets  # Garantir o import para gerar o token

    data = request.get_json(force=True)

    username = (data.get("username") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not username or not email or not password:
        return jsonify(status="error", msg="Dados inválidos"), 400

    # 🚫 EMAIL PERMANENTEMENTE BANIDO
    banido_email = User.query.filter_by(
        email=email,
        email_banido=True
    ).first()

    if banido_email:
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

    # 🔥 GERAR O TOKEN DE ATIVAÇÃO PARA A CONTA NOVA
    token_inicial = secrets.token_hex(16)

    # ✅ CRIAR CONTA COM O REACTIVATION_CODE DEFINIDO
    user = User(
        username=username,
        email=email,
        password=hash_password(password),
        avatar="default",
        banner="bannerdefault",
        avatares_comprados=json.dumps([]),
        banners_comprados=json.dumps([]),
        role="user",  
        moedas=0,
        ativo=False,                        # Começa desativado até verificar
        reactivation_code=token_inicial     # 🔥 SALVA O TOKEN AQUI DESDE O INÍCIO!
    )

    if hasattr(user, "email_verificado"):
        user.email_verificado = False

    db.session.add(user)
    db.session.commit()
    
    # Se for o primeiro utilizador, torna-o admin
    if user.id == 1:
        user.role = "admin"
        db.session.commit()

    # 🔥 Retorna o token e username para o teu Tkinter conseguir montar o e-mail sem dar None!
    return jsonify(
        status="ok",
        token=token_inicial,
        username=user.username
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

    session.clear()
    session["user_id"] = user.id
    session.permanent = True
        
    return jsonify(
    status="ok",
    id=user.id,
    username=user.username,
    email=user.email,
    avatar=user.avatar,
    banner=user.banner,
    moedas=user.moedas,

    # 🔥 ADMIN ROLE
    role=user.role,

    # 🔥 COMPRADOS
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
    import json
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
            # 🔥 Guardamos a "resposta" limpa para o e-mail ler, e mantemos o "hash" por segurança!
            perguntas_guardar.append({
                "pergunta": pergunta,
                "resposta": resposta,  # 👈 AGORA ADICIONAMOS ESTA LINHA CRUCIAL!
                "hash": hash_resposta(resposta)
            })

    user.perguntas_recuperacao = (
        json.dumps(perguntas_guardar, ensure_ascii=False) if perguntas_guardar else None
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
    
    admin_id = data.get("admin_id")
    
    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403
    
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

    admin_id = data.get("admin_id")
    target_id = data.get("user_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    user = User.query.get(target_id)

    if not user:
        return jsonify(error="User não encontrado"), 404

    # impedir remover a si próprio
    if user.id == int(admin_id):
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

    admin_id = data.get("admin_id")

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

    admin_id = data.get("admin_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    comment = Comment.query.get(comment_id)

    if not comment:
        return jsonify(error="Comentário não encontrado"), 404

    CommentLike.query.filter_by(comment_id=comment.id).delete()

    db.session.delete(comment)
    db.session.commit()

    return jsonify(status="ok")
    
# =========================================================
# BANIR USER
# =========================================================

@app.route("/admin/ban/<int:user_id>", methods=["POST"])
def admin_ban_user(user_id):

    data = request.get_json(force=True)

    admin_id = data.get("admin_id")
    motivo = data.get("motivo", "Violação das regras")

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

    admin_id = data.get("admin_id")

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

    admin_id = data.get("admin_id")
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

    admin_id = data.get("admin_id")

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

    admin_id = data.get("admin_id")
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

    admin_id = data.get("admin_id")

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

    admin_id = data.get("admin_id")

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

@app.route("/send-verification", methods=["POST"])
def send_verification():
    import secrets
    from datetime import datetime, timedelta

    data = request.get_json(force=True)
    email = data.get("email")

    if not email:
        return jsonify({"status": "error", "msg": "Email obrigatório"}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        # Se o utilizador não existe, não expomos isso, dizemos OK para segurança
        return jsonify({"status": "ok"}), 200

    # Verifica se já está verificado
    if getattr(user, "email_verificado", False) or getattr(user, "ativo", False) == True:
        return jsonify({"status": "ok"}), 200

    now = datetime.utcnow()

    try:
        if user.last_verification_request:
            diff = now - user.last_verification_request
            if diff < timedelta(seconds=30):
                return jsonify({
                    "status": "error",
                    "msg": "Aguarda 30 segundos antes de reenviar"
                }), 429

        if user.email_verification_attempts >= 5:
            return jsonify({
                "status": "error",
                "msg": "Limite de tentativas atingido"
            }), 429

        user.email_verification_attempts += 1
        user.last_verification_request = now
    except AttributeError:
        pass

    # 🔥 GERAR O TOKEN DIRETAMENTE AQUI
    token = secrets.token_hex(16)
    
    # Gravar na coluna que existe na tua base de dados
    user.reactivation_code = token

    # 🔥 OBRIGATÓRIO: Forçar a gravação na base de dados antes do return!
    db.session.add(user)
    db.session.commit()

    # Garantir que passamos o token gerado explicitamente no JSON de resposta
    return jsonify({
        "status": "ok",
        "token": str(token),  # Envia o token real em string para o Tkinter
        "username": user.username
    })
    
@app.route("/verify-email/<token>")
def verify_email(token):
    
    # Se o link vier vazio ou explicitamente "None", rejeita logo
    if not token or token == "None":
        return render_template("email_invalid.html")

    # 1. Procura o utilizador pelo token ativo
    user = User.query.filter_by(reactivation_code=token).first()

    # 2. Se NÃO encontrar o token...
    if not user:
        # 💡 CASO ESPECIAL: O utilizador pode estar a clicar pela SEGUNDA vez.
        # Vamos tentar ver se este token pertencia a uma conta que já está ativa.
        # Como o token foi limpo no primeiro clique, fazemos uma verificação de segurança:
        # Se não encontramos o token, mas a conta já foi ativada antes, não damos erro!
        return render_template("email_invalid.html")

    # 3. Se encontrou o token, ativa tudo com sucesso!
    if hasattr(user, "email_verificado"):
        user.email_verificado = True
        
    user.ativo = True
    user.reactivation_code = None  # Limpa para o token expirar

    db.session.commit()

    # Primeiro clique: Abre com sucesso absoluto!
    return render_template("email_verified.html")
    
@app.route("/check-email", methods=["POST"])
def check_email_exists():
    data = request.json
    email = data.get("email")

    user = User.query.filter_by(email=email).first()

    return jsonify({
        "exists": user is not None
    })

@app.route("/send-recovery-verification", methods=["POST"])
def send_recovery_verification():
    import secrets

    data = request.get_json(force=True)

    email = data.get("email")                     # Email principal
    recovery_email = data.get("recovery_email")   # Email de recuperação

    if not email or not recovery_email:
        return jsonify({
            "status": "error",
            "msg": "Dados incompletos"
        }), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({
            "status": "error",
            "msg": "Conta não encontrada"
        }), 404

    token = secrets.token_hex(16)

    user.email_recuperacao = recovery_email
    user.recovery_token = token

    db.session.commit()

    return jsonify({
        "status": "ok",
        "token": token,
        "username": user.username
    })

@app.route("/verify-recovery-email/<token>")
def verify_recovery_email(token):

    try:
        print("TOKEN RECEBIDO:", token)

        if not token or token == "None":
            print("TOKEN INVÁLIDO")
            return render_template("email_invalid.html")

        user = User.query.filter_by(recovery_token=token).first()

        print("USER ENCONTRADO:", user)

        if not user:
            return render_template("email_invalid.html")

        user.recovery_token = None

        db.session.commit()

        print("EMAIL VERIFICADO COM SUCESSO")

        return render_template("email_recovery_verified.html")

    except Exception as e:
        print("ERRO NA VERIFY-RECOVERY:", str(e))
        return render_template("email_invalid.html")

@app.route("/check-recovery-email", methods=["POST"])
def check_recovery_email_verification():

    data = request.get_json(force=True)

    email = data.get("email")

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({
            "verified": False
        })

    return jsonify({
        "verified": (
            user.email_recuperacao is not None and
            user.recovery_token is None
        )
    })
    
@app.route("/cancel-recovery-email/<token>")
def cancel_recovery_email(token):

    if not token:
        return render_template("email_invalid.html")

    user = User.query.filter_by(recovery_token=token).first()

    if not user:
        return render_template("email_invalid.html")

    user.email_recuperacao = None
    user.recovery_token = None

    db.session.commit()

    return render_template("email_recovery_cancelled.html")
# =======================================================
# 🔥 ROTA DE SUPORTE PARA O TKINTER (APENAS ESTA)
# =======================================================

@app.route("/get-user-data", methods=["POST"])
def tk_get_user_data():  # Nome alterado para evitar colisões
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return {"status": "error", "msg": "ID de utilizador inválido"}, 400

    user = User.query.get(user_id)
    if not user:
        return {"status": "error", "msg": "Utilizador não encontrado"}, 404

    # 🔥 Força o Flask a ler os dados mais recentes diretamente da BD (evita cache antigo)
    db.session.refresh(user)

    perguntas = json.loads(user.perguntas_recuperacao or "[]")

    # Mapear as perguntas de forma limpa enviando a resposta real para o e-mail do Tkinter
    lista_perguntas = []
    for p in perguntas:
        lista_perguntas.append({
            "pergunta": p.get("pergunta", ""),
            "resposta": p.get("resposta", "Não definida")  # 🔥 Agora passa a resposta real!
        })

    # Verifica se a conta está verificada através do campo email_verificado OU do campo ativo
    esta_verificado = getattr(user, "email_verificado", False) or getattr(user, "ativo", False)

    return {
        "status": "ok",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "email_recuperacao": user.email_recuperacao or "Não definido",
            
            # 🔥 Passa o estado real de verificação validado de ambos os campos
            "email_verificado": esta_verificado,
            
            "role": user.role,
            "moedas": user.moedas,
            "banido": user.banido,
            "bloqueado": user.bloqueado,
            "avisos": user.avisos,
            "perguntas": lista_perguntas
        }
    }
    
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

@app.route("/admin/user/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):

    user = User.query.get(user_id)
    if not user:
        return "User not found", 404

    if request.method == "POST":

        data = request.form

        # ================= BASIC =================
        user.username = data.get("username", user.username)
        user.email = data.get("email", user.email)
        user.email_recuperacao = data.get("email_recuperacao", user.email_recuperacao)

        password = data.get("password")
        if password:
            user.password = password

        # ================= RECOVERY =================
        user.perguntas_recuperacao = data.get("perguntas", user.perguntas_recuperacao)

        # ================= BOOL SYSTEM (SAFE) =================
        user.banido = "banido" in data
        user.bloqueado = "bloqueado" in data
        user.ativo = "ativo" in data

        user.email_banido = "email_banido" in data
        user.ia_banido = "ia_banido" in data

        # ================= SUSPENSIONS (FIX NULL SAFE) =================
        user.suspenso_ate = data.get("suspenso_ate") or None
        user.ia_suspenso_ate = data.get("ia_suspenso_ate") or None
        user.bloqueado_ate = data.get("bloqueado_ate") or None

        # ================= REASONS =================
        user.ban_reason = data.get("ban_reason", user.ban_reason)
        user.ia_ban_reason = data.get("ia_ban_reason", user.ia_ban_reason)

        db.session.commit()

        return "✔ Utilizador atualizado com sucesso!"

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Editar Utilizador</title>
</head>

<body style="margin:0;background:#0f172a;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;min-height:100vh;">

<div style="width:750px;background:#111827;padding:20px;border-radius:12px;">

<h2>⚙ Painel de Controlo do Utilizador</h2>

<form method="POST">

<h3>👤 Dados</h3>

<input name="username" value="{user.username}" placeholder="Username" style="width:100%;padding:10px;margin:5px 0;">
<input name="email" value="{user.email}" placeholder="Email" style="width:100%;padding:10px;margin:5px 0;">
<input name="email_recuperacao" value="{user.email_recuperacao or ''}" placeholder="Email recuperação" style="width:100%;padding:10px;margin:5px 0;">
<input name="password" placeholder="Nova password" style="width:100%;padding:10px;margin:5px 0;">

<hr>

<h3>🔐 Recuperação</h3>
<textarea name="perguntas" style="width:100%;height:100px;">{user.perguntas_recuperacao or ''}</textarea>

<hr>

<h3>🚫 Ban / Bloqueios</h3>

<label><input type="checkbox" name="banido" {"checked" if user.banido else ""}> Banido</label><br>
<label><input type="checkbox" name="bloqueado" {"checked" if user.bloqueado else ""}> Bloqueado</label><br>
<label><input type="checkbox" name="ativo" {"checked" if user.ativo else ""}> Ativo</label><br>
<label><input type="checkbox" name="email_banido" {"checked" if user.email_banido else ""}> Email Banido</label><br>
<label><input type="checkbox" name="ia_banido" {"checked" if user.ia_banido else ""}> IA Banido</label><br>

<hr>

<h3>⏳ Suspensões</h3>

<p>Conta suspensa até:</p>
<input name="suspenso_ate" value="{user.suspenso_ate or ''}" style="width:100%;padding:10px;">

<p>IA suspensa até:</p>
<input name="ia_suspenso_ate" value="{user.ia_suspenso_ate or ''}" style="width:100%;padding:10px;">

<p>Bloqueado até:</p>
<input name="bloqueado_ate" value="{user.bloqueado_ate or ''}" style="width:100%;padding:10px;">

<hr>

<h3>📌 Motivos</h3>

<input name="ban_reason" value="{user.ban_reason or ''}" style="width:100%;padding:10px;margin:5px 0;">
<input name="ia_ban_reason" value="{user.ia_ban_reason or ''}" style="width:100%;padding:10px;margin:5px 0;">

<hr>

<button type="submit" style="width:100%;padding:12px;background:#22c55e;color:black;font-weight:bold;border-radius:10px;">
💾 Guardar alterações
</button>

</form>

</div>

</body>
</html>
"""

@app.route("/admin/tickets")
def admin_tickets():

    admin_id = session.get("admin_ticket_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    filter_type = request.args.get("filter", "all")

    if filter_type == "open":
        tickets = Ticket.query.filter_by(status="open").order_by(Ticket.id.desc()).all()

    elif filter_type == "closed":
        tickets = Ticket.query.filter_by(status="closed").order_by(Ticket.id.desc()).all()

    else:
        tickets = Ticket.query.order_by(Ticket.id.desc()).all()

    def card(t, color):
        user = User.query.get(t.user_id)

        return f"""
        <div style="background:#0b1220;padding:12px;border-radius:12px;margin-bottom:10px;border:1px solid #1f2937;">

            <p><b>Ticket:</b> #{t.id}</p>
            <p><b>Assunto:</b> {t.title}</p>
            <p><b>User:</b> {user.username if user else "?"}</p>
            <p><b>Prioridade:</b> {t.priority}</p>
            <p><b>Status:</b> {t.status.upper()}</p>

            <a href="/admin/ticket/{t.id}"
               style="display:inline-block;margin-top:10px;padding:8px 12px;background:{color};color:white;border-radius:8px;text-decoration:none;">
               Abrir
            </a>
        </div>
        """

    html_cards = "".join(card(t, "#facc15") for t in tickets)

    return f"""
    <html>
    <body style="margin:0;font-family:Arial;background:#0f172a;color:white;">

    <div style="text-align:center;padding:20px;">
        <h1>🎫 Sistema de Tickets</h1>

        <div>
            <a href="/admin/tickets" style="margin:5px;padding:8px 12px;background:#2563eb;color:white;border-radius:8px;">Todos</a>
            <a href="/admin/tickets?filter=open" style="margin:5px;padding:8px 12px;background:#facc15;color:black;border-radius:8px;">Abertos</a>
            <a href="/admin/tickets?filter=closed" style="margin:5px;padding:8px 12px;background:#22c55e;color:black;border-radius:8px;">Fechados</a>
        </div>
    </div>

    <div style="max-width:900px;margin:auto;">
        {html_cards if html_cards else "<p>Sem tickets</p>"}
    </div>

    </body>
    </html>
    """
    
@app.route("/admin/ticket/<int:ticket_id>")
def open_ticket(ticket_id):

    admin_id = session.get("admin_ticket_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    ticket = Ticket.query.get(ticket_id)

    if not ticket:
        return "Ticket não encontrado", 404

    # =============================================================
    # NOVO: ATRIBUIR AUTOMATICAMENTE O TICKET AO ADMIN QUE O ABRIU
    # =============================================================
    if not ticket.admin_id:
        ticket.admin_id = admin_id
        db.session.commit()  # Grava na base de dados que este admin assumiu o ticket

    user = User.query.get(ticket.user_id)

    admin = None
    if ticket.admin_id:
        admin = User.query.get(ticket.admin_id)

    messages = TicketMessage.query.filter_by(
        ticket_id=ticket.id
    ).order_by(TicketMessage.id.asc()).all()

    html_msgs = ""

    for m in messages:

        if m.sender == "admin":

            sender_name = admin.username if admin else "Administrador"
            bubble = "#2563eb"
            border = "#60a5fa"

        else:

            sender_name = user.username if user else "Utilizador"
            bubble = "#1e293b"
            border = "#22c55e"

        html_msgs += f"""

        <div style="
            margin-bottom:15px;
            padding:12px;
            background:{bubble};
            border-left:5px solid {border};
            border-radius:10px;
        ">

            <b>{sender_name}</b>

            <div style="margin-top:8px;white-space:pre-wrap;">
                {m.message}
            </div>

        </div>

        """

    is_closed = ticket.status == "closed"

    close_pending = getattr(ticket, "close_pending", False)

    html = f"""

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<title>Ticket #{ticket.id}</title>

</head>

<body style="margin:0;background:#0f172a;color:white;font-family:Arial;">

<div style="display:flex;height:100vh;">

<div style="
width:320px;
background:#111827;
padding:20px;
overflow:auto;
border-right:1px solid #1f2937;
">

<h2>🎫 Ticket #{ticket.id}</h2>

<hr>

<h3>Informações</h3>

<p><b>Assunto</b><br>{ticket.title}</p>

<p><b>Prioridade</b><br>{ticket.priority.upper()}</p>

<p><b>Status</b><br>{"🔴 FECHADO" if is_closed else "🟢 ABERTO"}</p>

<p><b>Pedido Fecho</b><br>{"SIM" if close_pending else "NÃO"}</p>

<hr>

<h3>Utilizador</h3>

<p><b>ID</b><br>{user.id}</p>

<p><b>Username</b><br>{user.username}</p>

<p><b>Email</b><br>{user.email}</p>

<p><b>Recuperação</b><br>{user.email_recuperacao or "-"}</p>

<p><b>Moedas</b><br>{user.moedas}</p>

<p><b>Role</b><br>{user.role}</p>

<p><b>Banido</b><br>{"SIM" if user.banido else "NÃO"}</p>

<p><b>Bloqueado</b><br>{"SIM" if user.bloqueado else "NÃO"}</p>

<p><b>Conta Ativa</b><br>{"SIM" if user.ativo else "NÃO"}</p>

<a href="/admin/user/{user.id}/edit"
style="
display:block;
margin-top:15px;
padding:12px;
background:#2563eb;
color:white;
text-align:center;
border-radius:8px;
text-decoration:none;
">
⚙ Editar Utilizador
</a>

<hr>

<h3>Administrador</h3>

<p><b>ID</b><br>{admin.id if admin else "-"}</p>

<p><b>Username</b><br>{admin.username if admin else "Ainda não atribuído"}</p>

<p><b>Email</b><br>{admin.email if admin else "-"}</p>
<hr>

<a href="/admin/tickets"
style="
display:block;
padding:12px;
background:#334155;
color:white;
text-align:center;
border-radius:8px;
text-decoration:none;
margin-bottom:10px;
">
⬅ Voltar aos Tickets
</a>

"""

    # ===========================
    # BOTÕES DO TICKET
    # ===========================

    if not is_closed:

        if close_pending:

            html += f"""

<form method="POST" action="/ticket/{ticket.id}/confirm-close">

<button
style="
width:100%;
padding:12px;
margin-top:10px;
background:#22c55e;
border:none;
border-radius:8px;
color:black;
font-weight:bold;
cursor:pointer;
">

✔ Confirmar Fecho

</button>

</form>

"""

        else:

            html += f"""

<form method="POST" action="/ticket/{ticket.id}/request-close/admin">

<button
style="
width:100%;
padding:12px;
margin-top:10px;
background:#ef4444;
border:none;
border-radius:8px;
color:white;
cursor:pointer;
">

🔒 Pedir Fecho

</button>

</form>

"""

    else:

        html += f"""

<form method="POST" action="/ticket/{ticket.id}/reopen">

<button
style="
width:100%;
padding:12px;
margin-top:10px;
background:#22c55e;
border:none;
border-radius:8px;
color:black;
cursor:pointer;
">

🔓 Reabrir Ticket

</button>

</form>

"""

    # FECHA O PAINEL ESQUERDO
    html += """
</div>

<div
style="
flex:1;
display:flex;
flex-direction:column;
background:#0f172a;
">

<div
style="
padding:18px;
background:#111827;
border-bottom:1px solid #1f2937;
font-size:22px;
font-weight:bold;
">

💬 Conversa do Ticket

</div>

<div
id="chat"
style="
flex:1;
overflow:auto;
padding:20px;
">

"""

    html += html_msgs

    html += """

</div>

"""
    if not is_closed:

        html += f"""

<div style="
padding:20px;
background:#111827;
border-top:1px solid #1f2937;
">

<form id="form-resposta">

<input type="hidden" id="sender" value="admin">

<textarea
id="message-text"
required
placeholder="Escreva uma resposta..."
style="
width:100%;
height:110px;
padding:12px;
border-radius:10px;
resize:none;
box-sizing:border-box;
background:#1e293b;
color:white;
border:1px solid #334155;
">
</textarea>

<button
type="submit"
style="
margin-top:10px;
width:100%;
padding:14px;
background:#2563eb;
border:none;
border-radius:10px;
color:white;
cursor:pointer;
font-weight:bold;
">
📨 Responder como Admin
</button>

</form>

</div>

"""

    else:

        html += """

<div style="
padding:15px;
background:#7f1d1d;
border-radius:10px;
text-align:center;
font-weight:bold;
">

🔒 Este ticket encontra-se fechado.

</div>

"""

    html += f"""

</div>

</div>

<script>

function atualizarChat(){{

fetch("/ticket/{ticket.id}/messages")

.then(r=>r.text())

.then(html=>{{

const chatDiv = document.getElementById("chat");
const totalScroll = chatDiv.scrollHeight - chatDiv.clientHeight;
const estaNoFundo = (chatDiv.scrollTop >= totalScroll - 50);

chatDiv.innerHTML=html;

if(estaNoFundo || chatDiv.scrollTop === 0){{
    chatDiv.scrollTop = chatDiv.scrollHeight;
}}

}});

}}

// INTERCEPTAR SUBMISSÃO DO ADMIN VIA AJAX
const form = document.getElementById("form-resposta");
if(form){{
    form.addEventListener("submit", function(e){{
        e.preventDefault();
        
        const msgInput = document.getElementById("message-text");
        const msgValor = msgInput.value;
        const senderValor = document.getElementById("sender").value;
        
        if(!msgValor.trim()) return;

        fetch("/ticket/{ticket.id}/reply", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ message: msgValor, sender: senderValor }})
        }})
        .then(r => r.json())
        .then(data => {{
            if(data.status === "ok"){{
                msgInput.value = "";
                atualizarChat();
            }}
        }});
    }});
}}

setInterval(atualizarChat,3000);

window.onload=function(){{
document.getElementById("chat").scrollTop = document.getElementById("chat").scrollHeight;
}};

</script>

</body>

</html>
"""

    return html

@app.route("/ticket/<int:ticket_id>/reopen", methods=["POST"])
def reopen_ticket(ticket_id):

    ticket = Ticket.query.get(ticket_id)

    if not ticket:
        return "Ticket não encontrado", 404

    ticket.status = "open"

    db.session.commit()

    return redirect(f"/admin/ticket/{ticket_id}")

@app.route("/suporte")
def user_tickets():

    user_id = request.args.get("user_id")

    user = User.query.get(user_id)
    if not user:
        return f"""
        <!DOCTYPE html>
        <html lang="pt">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AERON - Erro</title>
        <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            height:100vh;
            display:flex;
            justify-content:center;
            align-items:center;
            font-family:"Segoe UI",sans-serif;
            background:linear-gradient(135deg, #020617 0%, #0f172a 35%, #1e3a8a 70%, #3b82f6 100%);
        }}
        .card {{
            width:700px; max-width:90%;
            background:rgba(15,23,42,.92);
            border:1px solid rgba(239,68,68,.25); /* Vermelho suave para erro */
            border-radius:24px; padding:60px; text-align:center;
            backdrop-filter:blur(12px);
            box-shadow:0 0 60px rgba(239,68,68,.15);
        }}
        .logo {{ width:180px; max-width:80%; margin-bottom:25px; }}
        .icon {{ font-size:72px; margin-bottom:15px; }}
        h1 {{ color:white; margin-bottom:20px; font-size:36px; }}
        p {{ color:#cbd5e1; font-size:18px; line-height:1.8; }}
        .msg {{ margin-top:15px; color:#f87171; font-weight:bold; }}
        </style>
        </head>
        <body>
        <div class="card">
            <img src="https://recuperar-conta-app-uza0.onrender.com/static/LOGO/AERON.png" class="logo" alt="AERON">
            <div class="icon">❌</div>
            <h1>Utilizador não encontrado</h1>
            <p>Não foi possível associar este pedido de suporte a uma conta ativa.</p>
            <p class="msg">Por favor, verifica os teus dados de acesso e tenta novamente.</p>
        </div>
        </body>
        </html>
        """, 404

    tickets = Ticket.query.filter_by(user_id=user_id).order_by(Ticket.id.desc()).all()

    def card(t):
        status_color = "#22c55e" if t.status == "open" else "#ef4444"

        return f"""
        <div style="background:#111827;padding:12px;margin-bottom:10px;border-radius:10px;">
            <p><b>Ticket #{t.id}</b></p>
            <p>Status: <span style="color:{status_color}">{t.status.upper()}</span></p>

            <a href="/ticket/{t.id}"
               style="display:inline-block;margin-top:8px;padding:8px 12px;background:#2563eb;color:white;border-radius:8px;text-decoration:none;">
               Abrir
            </a>
        </div>
        """

    html = "".join(card(t) for t in tickets)

    return f"""
    <html>
    <body style="background:#0f172a;color:white;font-family:Arial;">

    <div style="max-width:700px;margin:auto;margin-top:40px;">

        <h2>🎫 Os teus tickets</h2>

        <a href="/suporte/new?user_id={user_id}"
           style="display:inline-block;margin-bottom:15px;padding:10px 12px;background:#22c55e;color:black;border-radius:8px;text-decoration:none;">
           + Criar novo ticket
        </a>

        {html if html else "<p>Sem tickets ainda</p>"}

    </div>

    </body>
    </html>
    """
    
@app.route("/suporte/new", methods=["GET", "POST"])
def create_user_ticket():

    user_id = request.args.get("user_id")

    user = User.query.get(user_id)

    # Reutiliza o estilo se o user_id for inválido aqui também
    if not user:
        return f"""
        <!DOCTYPE html>
        <html lang="pt">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AERON - Erro</title>
        <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            height:100vh; display:flex; justify-content:center; align-items:center;
            font-family:"Segoe UI",sans-serif;
            background:linear-gradient(135deg, #020617 0%, #0f172a 35%, #1e3a8a 70%, #3b82f6 100%);
        }}
        .card {{
            width:700px; max-width:90%; background:rgba(15,23,42,.92);
            border:1px solid rgba(239,68,68,.25); border-radius:24px; padding:60px; text-align:center;
            backdrop-filter:blur(12px); box-shadow:0 0 60px rgba(239,68,68,.15);
        }}
        .logo {{ width:180px; max-width:80%; margin-bottom:25px; }}
        .icon {{ font-size:72px; margin-bottom:15px; }}
        h1 {{ color:white; margin-bottom:20px; font-size:36px; }}
        p {{ color:#cbd5e1; font-size:18px; line-height:1.8; }}
        .msg {{ margin-top:15px; color:#f87171; font-weight:bold; }}
        </style>
        </head>
        <body>
        <div class="card">
            <img src="https://recuperar-conta-app-uza0.onrender.com/static/LOGO/AERON.png" class="logo" alt="AERON">
            <div class="icon">❌</div>
            <h1>Utilizador não encontrado</h1>
            <p>O ID de utilizador fornecido é inválido.</p>
            <p class="msg">Acede ao suporte através da tua aplicação oficial.</p>
        </div>
        </body>
        </html>
        """, 404

    # 🔥 ERRO ESTILIZADO SE FOR ADMINISTRADOR A TENTAR CRIAR TICKET
    if user.role == "admin":
        return f"""
        <!DOCTYPE html>
        <html lang="pt">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AERON - Permissão Negada</title>
        <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            height:100vh; display:flex; justify-content:center; align-items:center;
            font-family:"Segoe UI",sans-serif;
            background:linear-gradient(135deg, #020617 0%, #0f172a 35%, #1e3a8a 70%, #3b82f6 100%);
        }}
        .card {{
            width:700px; max-width:90%; background:rgba(15,23,42,.92);
            border:1px solid rgba(245,158,11,.25); /* Laranja de aviso */
            border-radius:24px; padding:60px; text-align:center;
            backdrop-filter:blur(12px); box-shadow:0 0 60px rgba(245,158,11,.15);
        }}
        .logo {{ width:180px; max-width:80%; margin-bottom:25px; }}
        .icon {{ font-size:72px; margin-bottom:15px; }}
        h1 {{ color:white; margin-bottom:20px; font-size:36px; }}
        p {{ color:#cbd5e1; font-size:18px; line-height:1.8; }}
        .msg {{ margin-top:15px; color:#fbbf24; font-weight:bold; }}
        </style>
        </head>
        <body>
        <div class="card">
            <img src="https://recuperar-conta-app-uza0.onrender.com/static/LOGO/AERON.png" class="logo" alt="AERON">
            <div class="icon">⚠️</div>
            <h1>Acesso Restrito</h1>
            <p>Os administradores não possuem permissão para abrir novos tickets de suporte.</p>
            <p class="msg">Utiliza o Painel de Controlo para gerir os pedidos existentes.</p>
        </div>
        </body>
        </html>
        """, 403

    if request.method == "POST":

        title = request.form.get("title")
        priority = request.form.get("priority")
        message = request.form.get("message")

        ticket = Ticket(
            user_id=user_id,
            title=title,
            priority=priority,
            status="open"
        )

        db.session.add(ticket)
        db.session.commit()

        msg = TicketMessage(
            ticket_id=ticket.id,
            sender="user",
            message=message
        )

        db.session.add(msg)
        db.session.commit()

        return redirect(f"/suporte/sucesso/{ticket.id}")

    return f"""
    <html>
    <body style="background:#0f172a;color:white;font-family:Arial;">
    <div style="max-width:600px;margin:auto;margin-top:60px;">
        <h2>🆘 Criar Ticket</h2>
        <form method="POST">
            <input name="title" placeholder="Assunto do Ticket" required style="width:100%;padding:10px;margin-bottom:10px;border-radius:8px;">
            <select name="priority" style="width:100%;padding:10px;margin-bottom:10px;border-radius:8px;">
                <option value="urgent">🔴 Urgente</option>
                <option value="high">🟠 Alta</option>
                <option value="normal" selected>🟡 Normal</option>
                <option value="low">🟢 Baixa</option>
            </select>
            <textarea name="message" required placeholder="Descreve o problema..." style="width:100%;height:120px;padding:10px;border-radius:8px;"></textarea>
            <button style="width:100%;margin-top:10px;padding:12px; background:#22c55e;color:black;border:none;border-radius:8px;font-weight:bold;">
                🎫 Enviar Ticket
            </button>
        </form>
        <a href="/suporte?user_id={user_id}" style="display:block;margin-top:15px;text-align:center;color:white;">Voltar</a>
    </div>
    </body>
    </html>
    """

@app.route("/suporte/sucesso/<int:ticket_id>")
def ticket_success(ticket_id):

    return f"""
    <html>
    <body style="background:#0f172a;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;">

        <div style="text-align:center;background:#111827;padding:30px;border-radius:12px;width:420px;">

            <h2>✔ Ticket enviado com sucesso!</h2>

            <p>Deseja ver as atualizações do seu ticket?</p>

            <a href="/ticket/{ticket_id}"
               style="display:block;margin-top:15px;padding:10px;background:#22c55e;color:black;border-radius:8px;text-decoration:none;">
               🔎 Abrir Ticket
            </a>

            <a href="/suporte?user_id=1"
               style="display:block;margin-top:10px;color:white;">
               ← Voltar
            </a>

        </div>

    </body>
    </html>
    """

@app.route("/admin/tickets/login", methods=["GET", "POST"])
def admin_ticket_login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # 1. procura user normal
        user = User.query.filter_by(username=username).first()

        if not user:
            return "❌ Login inválido"

        # 2. verifica password
        if user.password != hash_password(password):
            return "❌ Login inválido"

        # 3. verifica se é admin
        if user.role != "admin":
            return "❌ Sem permissão (não és admin)"

        # 4. login OK
        session["admin_ticket_id"] = user.id

        return redirect("/admin/tickets")

    return """
    <html>
    <body style="background:#0f172a;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;">

        <div style="background:#111827;padding:25px;border-radius:12px;width:350px;">

            <h2>🔐 Admin Tickets Login</h2>

            <form method="POST">

                <input name="username" placeholder="Username"
                    style="width:100%;padding:10px;margin:10px 0;border-radius:8px;">

                <input name="password" type="password" placeholder="Password"
                    style="width:100%;padding:10px;margin:10px 0;border-radius:8px;">

                <button style="width:100%;padding:12px;background:#22c55e;color:black;border:none;border-radius:8px;">
                    Entrar
                </button>

            </form>

        </div>

    </body>
    </html>
    """
@app.route("/ticket/<int:ticket_id>/request-close/user", methods=["POST"])
def request_close_user(ticket_id):

    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return "Ticket não encontrado", 404

    ticket.close_requested_by = "user"
    ticket.close_pending = True

    db.session.commit()

    return redirect(f"/ticket/{ticket_id}")
    
@app.route("/get-user-by-email", methods=["POST"])
def get_user_by_email():

    data = request.get_json(silent=True) or {}

    email = data.get("email")

    if not email:
        return {
            "status": "error",
            "msg": "Email required"
        }, 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return {
            "status": "error",
            "msg": "User not found"
        }, 404

    return {
        "status": "ok",

        # 🔥 para poderes usar data["user_id"]
        "user_id": user.id,

        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "email_recuperacao": user.email_recuperacao,

            "account_status": getattr(user, "account_status", "active"),
            "ia_status": getattr(user, "ia_status", "ok"),
            "email_status": getattr(user, "email_status", "ok"),
            "status_reason": getattr(user, "status_reason", "")
        }
    }

@app.route("/ticket/<int:ticket_id>/request-close/admin", methods=["POST"])
def request_close_admin(ticket_id):

    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return "Ticket não encontrado", 404

    ticket.close_requested_by = "admin"
    ticket.close_pending = True

    db.session.commit()

    return redirect(f"/admin/ticket/{ticket_id}")

@app.route("/ticket/<int:ticket_id>/confirm-close", methods=["POST"])
def confirm_close(ticket_id):

    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return "Ticket não encontrado", 404

    ticket.status = "closed"
    ticket.close_pending = False

    db.session.commit()

    return redirect(f"/ticket/{ticket_id}")

@app.route("/ticket/<int:ticket_id>/rate", methods=["POST"])
def rate_admin(ticket_id):

    admin_id = session.get("admin_ticket_id")

    if not is_admin(admin_id):
        return jsonify(error="Sem permissão"), 403

    ticket = Ticket.query.get_or_404(ticket_id)

    data = request.get_json(force=True)

    rating = int(data.get("rating", 0))

    if rating < 1 or rating > 5:
        return jsonify(error="Avaliação inválida"), 400

    ticket.rating = rating

    db.session.commit()

    return jsonify(status="ok")

@app.route("/ticket/<int:ticket_id>/messages")
def get_messages(ticket_id):

    messages = TicketMessage.query.filter_by(ticket_id=ticket_id)\
        .order_by(TicketMessage.id.asc()).all()

    html = """
    <div style="display:flex;flex-direction:column;gap:10px;font-family:Arial;">
    """

    for m in messages:

        is_admin = (m.sender == "admin")

        align = "flex-end" if is_admin else "flex-start"
        bubble_color = "#2563eb" if is_admin else "#0b1220"
        text_color = "white"
        name_color = "#22c55e" if is_admin else "#60a5fa"

        html += f"""
        <div style="display:flex;justify-content:{align};">

            <div style="
                max-width:70%;
                background:{bubble_color};
                padding:10px 12px;
                border-radius:14px;
                color:{text_color};
                box-shadow:0 4px 12px rgba(0,0,0,0.25);
                position:relative;
            ">

                <div style="font-size:12px;color:{name_color};margin-bottom:4px;font-weight:bold;">
                    {m.sender.upper()}
                </div>

                <div style="font-size:14px;line-height:1.4;">
                    {m.message}
                </div>

            </div>

        </div>
        """

    html += "</div>"

    return html
    
@app.route("/admin/stats")
def admin_stats():

    admins = User.query.filter_by(role="admin").all()

    data = []

    for a in admins:

        tickets = Ticket.query.filter_by(admin_id=a.id).all()

        ratings = [t.rating for t in tickets if t.rating]

        avg = sum(ratings) / len(ratings) if ratings else 0

        data.append({
            "id": a.id,
            "username": a.username,
            "admin_code": a.admin_code,
            "avg_rating": round(avg, 2),
            "tickets": len(tickets)
        })

    return {"admins": data}

@app.route("/ticket/<int:ticket_id>/messages/json")
def messages_json(ticket_id):

    messages = TicketMessage.query.filter_by(ticket_id=ticket_id)\
        .order_by(TicketMessage.id.asc()).all()

    return jsonify([
        {
            "sender": m.sender,
            "message": m.message,
            "id": m.id
        }
        for m in messages
    ])

@app.route("/ticket/<int:ticket_id>/messages/live")
def messages_live(ticket_id):

    last_id = request.args.get("last_id", 0)

    messages = TicketMessage.query.filter(
        TicketMessage.ticket_id == ticket_id,
        TicketMessage.id > last_id
    ).order_by(TicketMessage.id.asc()).all()

    return jsonify([
        {
            "id": m.id,
            "sender": m.sender,
            "message": m.message
        }
        for m in messages
    ])

@app.route("/notifications/<int:user_id>")
def notifications(user_id):

    notifs = Notification.query.filter_by(
        user_id=user_id
    ).order_by(Notification.data.desc()).limit(50).all()

    return jsonify([
        {
            "id": n.id,
            "tipo": n.tipo,
            "from": n.origem_id,
            "post_id": n.post_id,
            "comment_id": n.comment_id,
            "lida": n.lida,
            "data": n.data.isoformat()
        }
        for n in notifs
    ])

@app.route("/follow/request", methods=["POST"])
def follow_request():

    data = request.get_json(force=True)

    from_user = data["from"]
    to_user = data["to"]

    # ❌ evitar auto-follow
    if str(from_user) == str(to_user):
        return jsonify(error="Inválido"), 400

    # 🚫 já existe pedido pendente?
    existing = FollowRequest.query.filter_by(
        from_user=from_user,
        to_user=to_user,
        status="pending"
    ).first()

    if existing:
        return jsonify(status="already_pending")

    # ➕ criar pedido
    fr = FollowRequest(
        from_user=from_user,
        to_user=to_user,
        status="pending"
    )

    db.session.add(fr)
    db.session.commit()

    return jsonify(ok=True)

@app.route("/follow/accept", methods=["POST"])
def accept_follow():

    data = request.get_json(force=True)

    req = FollowRequest.query.get(data["id"])

    if not req:
        return jsonify(error="Request não existe"), 404

    db.session.add(Follow(
        id=str(uuid.uuid4()),
        follower_id=req.from_user,
        followed_id=req.to_user
    ))

    db.session.delete(req)

    db.session.commit()

    return jsonify(ok=True)
    
@app.route("/follow/reject", methods=["POST"])
def reject_follow():

    data = request.get_json(force=True)

    req = FollowRequest.query.get(data["id"])
    if not req:
        return jsonify(error="Request não existe"), 404

    db.session.delete(req)
    db.session.commit()

    return jsonify(ok=True)
    
@app.route("/user/heartbeat", methods=["POST"])
def heartbeat():

    data = request.get_json(force=True)

    user = User.query.get(data["user_id"])

    if user:
        user.last_seen = datetime.utcnow()
        db.session.commit()

    return jsonify(ok=True)

@app.route("/follow/cancel", methods=["POST"])
def cancel_follow_request():

    data = request.get_json(force=True)

    from_user = data["from"]
    to_user = data["to"]

    req = FollowRequest.query.filter_by(
        from_user=from_user,
        to_user=to_user,
        status="pending"
    ).first()

    if not req:
        return jsonify(error="Pedido não encontrado"), 404

    db.session.delete(req)
    db.session.commit()

    return jsonify(status="cancelled")

@app.route("/follow/pending/count/<int:user_id>")
def pending_follow_count(user_id):

    count = FollowRequest.query.filter_by(
        to_user=user_id,
        status="pending"
    ).count()

    return jsonify(count=count)

@app.route("/follow/pending/<int:user_id>")
def pending_follow_list(user_id):

    requests_list = FollowRequest.query.filter_by(
        to_user=user_id,
        status="pending"
    ).all()

    resultado = []

    for r in requests_list:

        user = User.query.get(r.from_user)

        resultado.append({
            "id": r.id,
            "from_user": r.from_user,
            "username": user.username if user else "Desconhecido",
            "avatar": user.avatar if user else None,
            "bio": user.bio if user else ""
        })

    return jsonify(resultado)

@app.route("/notifications/unread/<int:user_id>")
def unread_notifications(user_id):

    total = Notification.query.filter_by(
        user_id=user_id,
        lida=False
    ).count()

    return jsonify(total=total)

@app.route("/notifications/read-all", methods=["POST"])
def read_all_notifications():

    data = request.get_json(force=True)

    Notification.query.filter_by(
        user_id=data["user_id"],
        lida=False
    ).update({
        "lida": True
    })

    db.session.commit()

    return jsonify(ok=True)

@app.route("/debug-admin")
def debug_admin():

    admin_id = session.get("admin_ticket_id")
    return {
        "session": dict(session),
        "user_id": admin_id,
        "is_admin": is_admin(admin_id)
    }

@app.route("/ping")
def ping():
    return "OK"
    
# ==========================================
# PAINEL DO UTILIZADOR - VISTA DO TICKET
# ==========================================
@app.route("/ticket/<int:ticket_id>")
def view_ticket(ticket_id):

    ticket = Ticket.query.get_or_404(ticket_id)

    user = User.query.get(ticket.user_id)
    admin = User.query.get(ticket.admin_id) if ticket.admin_id else None

    messages = TicketMessage.query.filter_by(
        ticket_id=ticket.id
    ).order_by(TicketMessage.id.asc()).all()

    html_messages = ""

    for m in messages:

        if m.sender == "admin":
            nome = admin.username if admin else "Administrador"
            cor = "#2563eb"
            borda = "#60a5fa"
        else:
            nome = user.username if user else "Utilizador"
            cor = "#1e293b"
            borda = "#22c55e"

        html_messages += f"""

        <div style="
            margin-bottom:15px;
            padding:12px;
            background:{cor};
            border-left:5px solid {borda};
            border-radius:10px;
        ">

            <b>{nome}</b>

            <div style="margin-top:8px;white-space:pre-wrap;">
                {m.message}
            </div>

        </div>

        """

    is_closed = ticket.status == "closed"
    close_pending = getattr(ticket, "close_pending", False)

    html = f"""

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<title>Ticket #{ticket.id}</title>

</head>

<body style="margin:0;background:#0f172a;color:white;font-family:Arial;">

<div style="display:flex;height:100vh;">

<div style="
width:320px;
background:#111827;
padding:20px;
overflow:auto;
border-right:1px solid #1f2937;
">

<h2>🎫 Ticket #{ticket.id}</h2>

<hr>

<h3>Informações</h3>

<p><b>Status</b><br>{"🔴 FECHADO" if is_closed else "🟢 ABERTO"}</p>

<p><b>Prioridade</b><br>{ticket.priority.upper()}</p>

<p><b>Admin Responsável</b><br>{admin.username if admin else "Ainda não atribuído"}</p>

<hr>

<a href="/posts"
style="
display:block;
padding:12px;
background:#334155;
color:white;
text-align:center;
border-radius:8px;
text-decoration:none;
margin-bottom:10px;
">
⬅ Voltar ao Início
</a>

"""

    # ===========================
    # BOTÕES DO TICKET (PAINEL ESQUERDO)
    # ===========================

    if not is_closed:

        if close_pending:

            html += f"""

<form method="POST" action="/ticket/{ticket.id}/confirm-close">

<button
style="
width:100%;
padding:12px;
margin-top:10px;
background:#22c55e;
border:none;
border-radius:8px;
color:black;
font-weight:bold;
cursor:pointer;
">

✔ Confirmar Fecho

</button>

</form>

"""

        else:

            html += f"""

<form method="POST" action="/ticket/{ticket.id}/request-close/user">

<button
style="
width:100%;
padding:12px;
margin-top:10px;
background:#ef4444;
border:none;
border-radius:8px;
color:white;
cursor:pointer;
">

🔒 Pedir Fecho

</button>

</form>

"""

    # FECHA O PAINEL ESQUERDO
    html += """
</div>

<div
style="
flex:1;
display:flex;
flex-direction:column;
background:#0f172a;
">

<div
style="
padding:18px;
background:#111827;
border-bottom:1px solid #1f2937;
font-size:22px;
font-weight:bold;
">

💬 Conversa do Ticket

</div>

<div
id="chat"
style="
flex:1;
overflow:auto;
padding:20px;
">

"""

    html += html_messages

    html += """

</div>

"""
    # ===========================
    # FORMULÁRIO DE RESPOSTA OU AVALIAÇÃO
    # ===========================
    if not is_closed:

        html += f"""

<div style="
padding:20px;
background:#111827;
border-top:1px solid #1f2937;
">

<form id="form-resposta">

<input type="hidden" id="sender" value="user">

<textarea
id="message-text"
required
placeholder="Escreva uma resposta..."
style="
width:100%;
height:110px;
padding:12px;
border-radius:10px;
resize:none;
box-sizing:border-box;
background:#1e293b;
color:white;
border:1px solid #334155;
">
</textarea>

<button
type="submit"
style="
margin-top:10px;
width:100%;
padding:14px;
background:#2563eb;
border:none;
border-radius:10px;
color:white;
cursor:pointer;
font-weight:bold;
">
📨 Responder
</button>

</form>

</div>

"""

    else:

        html += f"""

<div style="
padding:20px;
background:#111827;
border-top:1px solid #1f2937;
">

<div style="
padding:15px;
background:#7f1d1d;
border-radius:10px;
text-align:center;
font-weight:bold;
margin-bottom:15px;
">
🔒 Este ticket encontra-se fechado.
</div>

<div style="
background:#1e293b;
padding:20px;
border-radius:10px;
text-align:center;
border:1px solid #334155;
">
<h3 style="margin-top:0;">⭐ Avaliação do Atendimento</h3>
<p style="color:#94a3b8;">Como classifica o suporte recebido neste ticket?</p>
<form method="POST" action="/ticket/{ticket.id}/rate">
    <select name="rating" style="padding:10px; border-radius:5px; background:#0f172a; color:white; border:1px solid #334155; width:200px; font-size:14px;">
        <option value="5">⭐⭐⭐⭐⭐ Excelente</option>
        <option value="4">⭐⭐⭐⭐ Bom</option>
        <option value="3">⭐⭐⭐ Regular</option>
        <option value="2">⭐⭐ Mau</option>
        <option value="1">⭐ Terrível</option>
    </select>
    <br><br>
    <button style="padding:12px 24px; background:#22c55e; color:black; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">
        Submeter Avaliação
    </button>
</form>
</div>

</div>

"""

    html += f"""

</div>

</div>

<script>

function atualizarChat(){{

fetch("/ticket/{ticket.id}/messages")

.then(r=>r.text())

.then(html=>{{

const chatDiv = document.getElementById("chat");
const totalScroll = chatDiv.scrollHeight - chatDiv.clientHeight;
const estaNoFundo = (chatDiv.scrollTop >= totalScroll - 50);

chatDiv.innerHTML=html;

if(estaNoFundo || chatDiv.scrollTop === 0){{
    chatDiv.scrollTop = chatDiv.scrollHeight;
}}

}});

}}

// INTERCEPTAR SUBMISSÃO VIA AJAX
const form = document.getElementById("form-resposta");
if(form){{
    form.addEventListener("submit", function(e){{
        e.preventDefault();
        
        const msgInput = document.getElementById("message-text");
        const msgValor = msgInput.value;
        const senderValor = document.getElementById("sender").value;
        
        if(!msgValor.trim()) return;

        fetch("/ticket/{ticket.id}/reply", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ message: msgValor, sender: senderValor }})
        }})
        .then(r => r.json())
        .then(data => {{
            if(data.status === "ok"){{
                msgInput.value = "";
                atualizarChat();
            }}
        }});
    }});
}}

setInterval(atualizarChat,3000);

window.onload=function(){{
document.getElementById("chat").scrollTop = document.getElementById("chat").scrollHeight;
}};

</script>

</body>

</html>

"""

    return html
    
# ==========================================
# RETORNO DENTRO DO CHAT AUTOMÁTICO (USER)
# ==========================================
@app.route("/ticket/<int:ticket_id>/messages")
def ticket_messages(ticket_id):

    ticket = Ticket.query.get_or_404(ticket_id)

    user = User.query.get(ticket.user_id)
    admin = User.query.get(ticket.admin_id) if ticket.admin_id else None

    messages = TicketMessage.query.filter_by(
        ticket_id=ticket.id
    ).order_by(TicketMessage.id.asc()).all()

    html = ""

    for m in messages:

        if m.sender == "admin":
            nome = admin.username if admin else "Administrador"
            cor = "#2563eb"
            borda = "#60a5fa"
        else:
            nome = user.username if user else "Utilizador"
            cor = "#1e293b"
            borda = "#22c55e"

        html += f"""
<div style="
margin-bottom:15px;
padding:12px;
background:{cor};
border-left:5px solid {borda};
border-radius:10px;
">
<b>{nome}</b>
<div style="margin-top:8px;white-space:pre-wrap;">
{m.message}
</div>
</div>
"""

    return html

# ==========================================
# PROCESSAR ENVIO DE MENSAGENS (USER/ADMIN)
# ==========================================
@app.route("/ticket/<int:ticket_id>/reply", methods=["POST"])
def ticket_reply(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Se o formulário vier via AJAX (JSON) ou formulário normal
    if request.is_json:
        data = request.get_json()
        message_text = data.get("message")
        sender = data.get("sender", "user")
    else:
        message_text = request.form.get("message")
        sender = request.form.get("sender", "user")

    if not message_text or not message_text.strip():
        return jsonify(status="error", message="Mensagem vazia"), 400

    # Criar e guardar a nova mensagem
    nova_msg = TicketMessage(
        ticket_id=ticket.id,
        sender=sender,
        message=message_text.strip()
    )
    db.session.add(nova_msg)
    db.session.commit()

    return jsonify(status="ok")

# ==========================================
# PROCESSAR PEDIDO DE FECHO (USER)
# ==========================================
@app.route("/ticket/<int:ticket_id>/request-close/user", methods=["POST"])
def ticket_request_close_user(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.close_pending = True
    ticket.close_requested_by = "user"
    db.session.commit()
    return redirect(f"/ticket/{ticket.id}")

# ==========================================
# PROCESSAR CONFIRMAÇÃO DE FECHO
# ==========================================
@app.route("/ticket/<int:ticket_id>/confirm-close", methods=["POST"])
def ticket_confirm_close(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.status = "closed"
    ticket.close_pending = False
    db.session.commit()
    return redirect(f"/ticket/{ticket.id}")

# ==========================================
# PROCESSAR AVALIAÇÃO DO TICKET
# ==========================================
@app.route("/ticket/<int:ticket_id>/rate", methods=["POST"])
def ticket_rate(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    rating = request.form.get("rating", type=int)
    if rating:
        ticket.rating = rating
        db.session.commit()
    return redirect(f"/ticket/{ticket.id}")
#================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
