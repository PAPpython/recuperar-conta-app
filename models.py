from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80))
    password_hash = db.Column(db.String(200))

    recovery_code = db.Column(db.String(64))
    recovery_expires = db.Column(db.DateTime)
