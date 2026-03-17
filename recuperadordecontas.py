from flask import Flask, render_template, request, jsonify,send_from_directory
import os
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
from flask import send_from_directory
from flask import request
import os
import time
import hashlib
import hmac
import base64
import json
import uuid

print("ESTE DEPLOY É O NOVO!!!")

# ================= APP =================
app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# garantir que a pasta existe (Render)
os.makedirs(os.path.join(UPLOAD_FOLDER, "fotos"), exist_ok=True)

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

# ================= MODELO USER =================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(128))
    nome = db.Column(db.String(120), nullable=True)
    banner = db.Column(db.String(255), nullable=True)

     # 🔐 Recuperação
    email_recuperacao = db.Column(db.String(120), nullable=True)
    perguntas_recuperacao = db.Column(db.Text, nullable=True)  # JSON

    moedas = db.Column(db.Integer, default=0)

    ativo = db.Column(db.Boolean, default=True)  # Define se a conta está ativa
    desativado_em = db.Column(db.DateTime, nullable=True)  # Data de desativação
    reactivation_code = db.Column(db.String(32), nullable=True)  # Código de reativação temporário
    apagado = db.Column(db.Boolean, default=False)  # Marca se a conta foi apagada
    avatar = db.Column(db.String(50), nullable=True)  # ✅ AVATAR (ID DO AVATAR)

class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.String, primary_key=True)
    autor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    texto = db.Column(db.Text)
    imagem = db.Column(db.String)
    original_post_id = db.Column(db.String, db.ForeignKey("posts.id"))
    data = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.String, primary_key=True)
    post_id = db.Column(
        db.String,
        db.ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False
    )
    autor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.String, db.ForeignKey("comments.id"))
    data = db.Column(db.DateTime, default=datetime.utcnow)


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
        return jsonify(status="error", msg="Dados inválidos"), 400

    if User.query.filter_by(username=username).first():
        return jsonify(status="error", msg="Username já existe"), 409

    if User.query.filter_by(email=email).first():
        return jsonify(status="error", msg="Email já existe"), 409

    user = User(
    username=username,
    email=email,
    password=hash_password(password),
    avatar="default"
)

    db.session.add(user)
    db.session.commit()

    return jsonify(status="ok")
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

    return jsonify(
    status="ok",
    id=user.id,
    username=user.username,
    email=user.email,
    avatar=user.avatar,
    moedas=user.moedas
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
    data = request.get_json(force=True)

    post = Post(
        id=str(uuid.uuid4()),
        autor_id=data["autor_id"],
        texto=data.get("texto"),
        imagem=data.get("imagem"),
        original_post_id=data.get("original_post_id")
    )

    db.session.add(post)
    db.session.commit()

    return jsonify(status="ok", id=post.id)

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
                "avatar": autor.avatar
            }
        })

    return jsonify(res)

#================= RESPONDER COMENTÁRIO =================
@app.route("/posts/<post_id>/comment", methods=["POST"])
def comentar(post_id):
    data = request.get_json(force=True)

    user_id = data.get("user_id")
    texto = (data.get("texto") or "").strip()
    parent_id = data.get("parent_id")  # opcional

    if not user_id or not texto:
        return jsonify(error="Dados inválidos"), 400

    # Verificar se o post existe
    post = Post.query.get(post_id)
    if not post:
        return jsonify(error="Post não encontrado"), 404

    # 🚫 BLOQUEIO: autor do post
    if existe_bloqueio(user_id, post.autor_id):
        return jsonify(error="Não podes comentar neste post"), 403

    parent_comment = None

    # Se for resposta, validar comentário pai
    if parent_id:
        parent_comment = Comment.query.get(parent_id)
        if not parent_comment:
            return jsonify(error="Comentário pai não existe"), 404

        if parent_comment.post_id != post_id:
            return jsonify(error="Comentário não pertence a este post"), 400

        # 🚫 BLOQUEIO: autor do comentário pai
        if existe_bloqueio(user_id, parent_comment.autor_id):
            return jsonify(error="Não podes responder a este comentário"), 403

    # Criar comentário
    comment = Comment(
        id=str(uuid.uuid4()),
        post_id=post_id,
        autor_id=user_id,
        texto=texto,
        parent_id=parent_id
    )

    db.session.add(comment)

    # 🔔 NOTIFICAÇÕES (apenas se NÃO houver bloqueio)
    # Resposta a comentário
    if parent_comment and parent_comment.autor_id != user_id:
        if not existe_bloqueio(user_id, parent_comment.autor_id):
            db.session.add(Notification(
                id=str(uuid.uuid4()),
                user_id=parent_comment.autor_id,
                tipo="reply_comment",
                origem_id=user_id,
                post_id=post_id,
                comment_id=parent_id
            ))

    # Comentário normal no post
    elif not parent_id and post.autor_id != user_id:
        if not existe_bloqueio(user_id, post.autor_id):
            db.session.add(Notification(
                id=str(uuid.uuid4()),
                user_id=post.autor_id,
                tipo="comment",
                origem_id=user_id,
                post_id=post_id
            ))

    db.session.commit()

    return jsonify(
        status="ok",
        id=comment.id,
        parent_id=comment.parent_id
    )

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

    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.data).all()
    res = []

    for c in comments:
        # 🔒 BLOQUEIO
        if viewer_id and existe_bloqueio(viewer_id, c.autor_id):
            continue

        autor = User.query.get(c.autor_id)
        if not autor:
            continue

        parent_info = None
        if c.parent_id:
            parent = Comment.query.get(c.parent_id)
            if parent:
                # 🔒 BLOQUEIO DO AUTOR DO COMENTÁRIO PAI
                if viewer_id and existe_bloqueio(viewer_id, parent.autor_id):
                    continue

                parent_user = User.query.get(parent.autor_id)
                if parent_user:
                    parent_info = {
                        "id": parent.id,
                        "username": parent_user.username
                    }

        res.append({
            "id": c.id,
            "texto": c.texto,
            "data": c.data.strftime("%d/%m/%Y %H:%M"),
            "parent_id": c.parent_id,
            "parent": parent_info,
            "likes": CommentLike.query.filter_by(comment_id=c.id).count(),
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
        "avatar": user.avatar,  # ✅
        "banner": user.banner,
        "seguidores": seguidores,
        "seguindo": seguindo
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

    # 🔒 BLOQUEIO TOTAL (dos dois lados)
    if existe_bloqueio(from_user, to_user):
        return jsonify(error="Não é possível enviar mensagem a este utilizador"), 403

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
        "moedas": user.moedas
    })
# ================= ATUALIZAR PERFIL =================
@app.route("/users/update", methods=["POST"])
def atualizar_perfil():
    data = request.get_json(force=True)

    user_id = data.get("id")
    username = (data.get("username") or "").strip().lower()
    apelido = data.get("apelido")
    avatar = data.get("avatar")

    if not user_id or not username:
        return jsonify(error="Dados inválidos"), 400

    user = User.query.get(user_id)
    print("USER:", user_id, "MOEDAS:", user.moedas)
    if not user or user.apagado:
        return jsonify(error="Utilizador não encontrado"), 404

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

@app.route("/avatars/loja", methods=["GET"])
def listar_loja_avatares():
    return jsonify({
        "avatares": AVATARES_LOJA,
        "preco": PRECO_AVATAR
    })


@app.route("/avatars/comprar", methods=["POST"])
def comprar_avatar():
    data = request.get_json(force=True)

    user_id = data.get("user_id")
    avatar_id = data.get("avatar")

    if not user_id or not avatar_id:
        return jsonify(error="Dados inválidos"), 400

    if avatar_id not in AVATARES_LOJA:
        return jsonify(error="Avatar inválido"), 400

    user = User.query.get(user_id)
    if not user or user.apagado:
        return jsonify(error="Utilizador não encontrado"), 404

    # 🔍 DEBUG (podes apagar depois)
    print("USER:", user_id)
    print("MOEDAS DB:", user.moedas)
    print("PREÇO:", PRECO_AVATAR)

    # 🔴 VERIFICAÇÃO CORRETA
    if int(user.moedas) < int(PRECO_AVATAR):
        return jsonify(error="Moedas insuficientes"), 403

    # 💰 DESCONTAR
    user.moedas = int(user.moedas) - int(PRECO_AVATAR)

    # 🖼️ ATUALIZAR AVATAR
    user.avatar = avatar_id

    db.session.commit()

    return jsonify(
        status="ok",
        novo_avatar=user.avatar,
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
    
#================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
