from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os, random, string, hashlib

app = Flask(__name__)
CORS(app)

# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "SQLALCHEMY_DATABASE_URI", "sqlite:///db.sqlite3"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150))
    email = db.Column(db.String(150))
    password = db.Column(db.String(256))

class RecoveryCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150))
    code = db.Column(db.String(6))

with app.app_context():
    db.create_all()

# ================= ROTAS =================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/recover-username", methods=["GET", "POST"])
def recover_username():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template("message.html", msg="❌ Email não encontrado")
        return render_template(
            "message.html",
            msg="✅ O nome de utilizador foi enviado para o teu email"
        )
    return render_template("recover_username.html")

@app.route("/recover-password", methods=["GET", "POST"])
def recover_password():
    if request.method == "POST":
        return render_template(
            "message.html",
            msg="✅ Password alterada com sucesso"
        )
    return render_template("recover_password.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
