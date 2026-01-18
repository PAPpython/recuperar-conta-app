from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import time
import hmac
import hashlib
import base64
import json

# ================= APP =================
app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
SECRET_TOKEN = b"recuperacao-super-secreta"
CODE_EXPIRATION = 300  # 5 minutos

# ================= UTILS =================
def gerar_token(tipo):
    payload = {
        "type": tipo,
        "exp": int(time.time()) + CODE_EXPIRATION
    }

    payload_bytes = json.dumps(payload).encode()
    assinatura = hmac.new(
        SECRET_TOKEN,
        payload_bytes,
        hashlib.sha256
    ).digest()

    token = base64.urlsafe_b64encode(
        payload_bytes + b"." + assinatura
    ).decode()

    return token


def validar_token(token, tipo_esperado):
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        payload_bytes, assinatura = raw.rsplit(b".", 1)

        assinatura_esperada = hmac.new(
            SECRET_TOKEN,
            payload_bytes,
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(assinatura, assinatura_esperada):
            return False, "Assinatura inválida"

        payload = json.loads(payload_bytes.decode())

        if payload.get("type") != tipo_esperado:
            return False, "Tipo inválido"

        if time.time() > payload.get("exp", 0):
            return False, "Código expirado"

        return True, "OK"

    except Exception:
        return False, "Código inválido"


# ================= PÁGINAS =================
@app.route("/")
def index():
    return "Servidor de recuperação ativo"


@app.route("/recover-password")
def recover_password():
    return render_template("recover_password.html")


@app.route("/recover-username")
def recover_username():
    return render_template("recover_username.html")


# ================= API GERAR CÓDIGOS =================
@app.route("/api/generate-password-code")
def generate_password_code():
    return jsonify(
        status="ok",
        token=gerar_token("password"),
        expires=CODE_EXPIRATION
    )


@app.route("/api/generate-username-code")
def generate_username_code():
    return jsonify(
        status="ok",
        token=gerar_token("username"),
        expires=CODE_EXPIRATION
    )


# ================= API VALIDAR =================
@app.route("/api/validate-password-code", methods=["POST"])
def validate_password_code():
    data = request.get_json(force=True)
    token = data.get("token", "")

    ok, msg = validar_token(token, "password")
    if not ok:
        return jsonify(status="error", msg=msg)

    return jsonify(status="ok")


@app.route("/api/validate-username-code", methods=["POST"])
def validate_username_code():
    data = request.get_json(force=True)
    token = data.get("token", "")

    ok, msg = validar_token(token, "username")
    if not ok:
        return jsonify(status="error", msg=msg)

    return jsonify(status="ok")


# ================= START =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
