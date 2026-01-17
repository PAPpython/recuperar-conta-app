from flask import Flask, render_template, request, jsonify
import random, hashlib

from models import db, User, RecoveryCode

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "secret"
db.init_app(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/recover-username", methods=["GET", "POST"])
def recover_username():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({"status": "error", "msg": "Email não encontrado"})

        return jsonify({
            "status": "ok",
            "msg": f"O nome de utilizador é: {user.username}"
        })

    return render_template("recover_username.html")

@app.route("/recover-password", methods=["GET", "POST"])
def recover_password():
    if request.method == "POST":
        step = request.form.get("step")

        if step == "email":
            email = request.form.get("email")
            user = User.query.filter_by(email=email).first()

            if not user:
                return jsonify({"status": "error", "msg": "Email não encontrado"})

            code = "".join(random.choices("0123456789", k=6))
            RecoveryCode.query.filter_by(email=email).delete()
            db.session.add(RecoveryCode(email=email, code=code))
            db.session.commit()

            return jsonify({"status": "ok", "msg": "Código enviado para o email"})

        if step == "confirm":
            email = request.form.get("email")
            code = request.form.get("code")
            password = request.form.get("password")

            rec = RecoveryCode.query.filter_by(email=email, code=code).first()
            if not rec:
                return jsonify({"status": "error", "msg": "Código inválido"})

            user = User.query.filter_by(email=email).first()
            user.password = hashlib.sha256(password.encode()).hexdigest()

            db.session.delete(rec)
            db.session.commit()

            return jsonify({"status": "ok", "msg": "Password alterada com sucesso"})

    return render_template("recover_password.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
