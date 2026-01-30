from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import time
import hashlib
import hmac
import base64
import json

# ================= POSTS (MEMÓRIA) =================
posts = []

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


# ================= POSTS =================
@app.route("/posts", methods=["GET"])
def listar_posts():
    return jsonify(posts)

@app.route("/posts", methods=["POST"])
def criar_post():
    post = request.get_json()
    if not post:
        return jsonify({"status": "error"}), 400

    # garante estrutura correta
    post.setdefault("id", str(uuid.uuid4()))
    post.setdefault("comments", [])
    post.setdefault("likes", [])
    post.setdefault("reposts", [])
    post.setdefault("shares", [])

    posts.insert(0, post)
    return jsonify({"status": "ok"})

@app.route("/posts/<post_id>", methods=["DELETE"])
def apagar_post(post_id):
    global posts
    posts = [p for p in posts if p.get("id") != post_id]
    return jsonify({"status": "ok"})

# ================= COMMENTS =================
@app.route("/posts/<post_id>/comments", methods=["POST"])
def adicionar_comentario(post_id):
    data = request.get_json()
    if not data:
        return jsonify({"status": "error"}), 400

    data.setdefault("id", str(uuid.uuid4()))

    for p in posts:
        if p.get("id") == post_id:
            p["comments"].append(data)
            return jsonify({"status": "ok"})

    return jsonify({"status": "error", "msg": "Post não encontrado"}), 404

@app.route("/posts/<post_id>/comments/<comment_id>", methods=["DELETE"])
def apagar_comentario(post_id, comment_id):
    for p in posts:
        if p.get("id") == post_id:
            p["comments"] = [
                c for c in p.get("comments", [])
                if c.get("id") != comment_id
            ]
            return jsonify({"status": "ok"})

    return jsonify({"status": "error"}), 404

# ================= LIKES / REPOSTS / SHARES =================
def toggle_lista(post_id, campo, user_id):
    for p in posts:
        if p.get("id") == post_id:
            p.setdefault(campo, [])
            if user_id in p[campo]:
                p[campo].remove(user_id)
            else:
                p[campo].append(user_id)
            return len(p[campo])
    return None

@app.route("/posts/<post_id>/like", methods=["POST"])
def like_post(post_id):
    user_id = request.json.get("user_id")
    total = toggle_lista(post_id, "likes", user_id)
    if total is None:
        return jsonify({"status": "error"}), 404
    return jsonify({"likes": total})

@app.route("/posts/<post_id>/repost", methods=["POST"])
def repost_post(post_id):
    user_id = request.json.get("user_id")
    total = toggle_lista(post_id, "reposts", user_id)
    if total is None:
        return jsonify({"status": "error"}), 404
    return jsonify({"reposts": total})

@app.route("/posts/<post_id>/share", methods=["POST"])
def share_post(post_id):
    user_id = request.json.get("user_id")
    total = toggle_lista(post_id, "shares", user_id)
    if total is None:
        return jsonify({"status": "error"}), 404
    return jsonify({"shares": total})

# ================= START =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
