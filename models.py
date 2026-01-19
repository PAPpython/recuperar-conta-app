from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # ===== DADOS PRINCIPAIS =====
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # ===== RECUPERAÇÃO DE CONTA =====
    recovery_code = db.Column(db.String(32), nullable=True)
    recovery_expires = db.Column(db.DateTime, nullable=True)

    # ===== METADADOS =====
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.username}>"
