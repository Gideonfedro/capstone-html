from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)  # user | admin
    otp_code = db.Column(db.String(10))
    otp_expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ads = db.relationship("Ad", backref="user", lazy=True, foreign_keys="Ad.user_id")
    quotations = db.relationship(
        "Quotation", backref="vendor", lazy=True, foreign_keys="Quotation.vendor_id"
    )
    bills = db.relationship("Bill", backref="user", lazy=True)
    past_works = db.relationship("PastWork", backref="vendor", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Ad(db.Model):
    __tablename__ = "ads"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # private/devotional/political
    location = db.Column(db.String(150), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255))
    status = db.Column(db.String(30), default="open", nullable=False)  # open/quoted/accepted/billed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quotations = db.relationship("Quotation", backref="ad", lazy=True, cascade="all,delete")


class Quotation(db.Model):
    __tablename__ = "quotations"

    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Float, nullable=False)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending/accepted/rejected
    contact_name = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    bill = db.relationship("Bill", backref="quotation", uselist=False)


class Bill(db.Model):
    __tablename__ = "bills"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default="paid", nullable=False)
    invoice_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotations.id"), nullable=False, unique=True)


class PastWork(db.Model):
    __tablename__ = "past_works"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vendor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
