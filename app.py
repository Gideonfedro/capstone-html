import os
import random
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_mail import Mail, Message
from flask_uploads import IMAGES, UploadSet, configure_uploads
from fpdf import FPDF

from models import Ad, Bill, PastWork, Quotation, User, db


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
INVOICE_DIR = os.path.join(BASE_DIR, "static", "invoices")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(INVOICE_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///eventx.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOADED_PHOTOS_DEST"] = UPLOAD_DIR

# Mail config (set env vars for actual email delivery)
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", "noreply@eventx.local")

mail = Mail(app)
db.init_app(app)

photos = UploadSet("photos", IMAGES)
configure_uploads(app, photos)

login_manager = LoginManager(app)
login_manager.login_view = "user_login"


def render_page(page: str, **context):
    """Render every screen from a single consolidated HTML template."""
    return render_template("app.html", page=page, **context)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash("You are not allowed to access this page.", "error")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def send_email(subject: str, recipients: list[str], body: str) -> None:
    if not recipients:
        return
    try:
        msg = Message(subject=subject, recipients=recipients, body=body)
        mail.send(msg)
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("Email send skipped/failed: %s", exc)


def bootstrap_admin() -> None:
    if not User.query.filter_by(role="admin").first():
        admin = User(
            full_name="Platform Admin",
            email="admin@eventx.local",
            phone="9999999999",
            role="admin",
        )
        admin.set_password("Admin@123")
        db.session.add(admin)
        db.session.commit()


def generate_invoice(bill: Bill, user: User, quotation: Quotation) -> str:
    filename = f"invoice_{bill.id}.pdf"
    path = os.path.join(INVOICE_DIR, filename)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "EventX Invoice", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Invoice ID: {bill.id}", ln=True)
    pdf.cell(0, 10, f"Date: {bill.created_at.strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(0, 10, f"Customer: {user.full_name} ({user.email})", ln=True)
    pdf.cell(0, 10, f"Quotation ID: {quotation.id}", ln=True)
    pdf.cell(0, 10, f"Amount Paid: INR {bill.amount:.2f}", ln=True)
    pdf.multi_cell(0, 10, f"Quotation Details: {quotation.details}")
    pdf.output(path)
    return f"invoices/{filename}"


@app.route("/")
def index():
    recent_ads = Ad.query.order_by(Ad.created_at.desc()).limit(6).all()
    return render_page("index", recent_ads=recent_ads)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for("register"))

        user = User(
            full_name=request.form["full_name"].strip(),
            email=email,
            phone=request.form["phone"].strip(),
            role="user",
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Login now.", "success")
        return redirect(url_for("user_login"))

    return render_page("register")


@app.route("/login/user", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email, role="user").first()
        if user and user.check_password(password):
            login_user(user)
            flash("Welcome to EventX.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "error")
    return render_page("login_user")


@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        admin = User.query.filter_by(email=email, role="admin").first()
        if admin and admin.check_password(password):
            otp = str(random.randint(100000, 999999))
            admin.otp_code = otp
            admin.otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
            db.session.commit()
            session["pending_admin_id"] = admin.id
            send_email(
                "EventX Admin OTP",
                [admin.email],
                f"Your EventX OTP is {otp}. It expires in 5 minutes.",
            )
            flash("OTP sent to your email.", "success")
            return redirect(url_for("admin_verify_otp"))
        flash("Invalid admin credentials.", "error")
    return render_page("login_admin")


@app.route("/login/admin/verify", methods=["GET", "POST"])
def admin_verify_otp():
    pending_id = session.get("pending_admin_id")
    if not pending_id:
        return redirect(url_for("admin_login"))

    admin = User.query.get_or_404(pending_id)
    if request.method == "POST":
        otp = request.form["otp"].strip()
        if (
            admin.otp_code == otp
            and admin.otp_expires_at
            and datetime.utcnow() <= admin.otp_expires_at
        ):
            admin.otp_code = None
            admin.otp_expires_at = None
            db.session.commit()
            session.pop("pending_admin_id", None)
            login_user(admin)
            flash("Admin login successful.", "success")
            return redirect(url_for("admin_panel"))
        flash("Invalid or expired OTP.", "error")
    return render_page("verify_otp")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
@role_required("user")
def dashboard():
    categories = ["private", "devotional", "political"]
    return render_page("dashboard", categories=categories)


@app.route("/category/<string:category>", methods=["GET", "POST"])
@login_required
@role_required("user")
def category_portal(category):
    allowed = {"private", "devotional", "political"}
    if category not in allowed:
        flash("Invalid category.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        image_filename = None
        image = request.files.get("photo")
        if image and image.filename:
            image_filename = photos.save(image)

        ad = Ad(
            category=category,
            location=request.form["location"].strip(),
            event_date=datetime.strptime(request.form["event_date"], "%Y-%m-%d").date(),
            description=request.form["description"].strip(),
            image_filename=image_filename,
            user_id=current_user.id,
        )
        db.session.add(ad)
        db.session.commit()

        admins = [u.email for u in User.query.filter_by(role="admin").all()]
        send_email(
            "New Ad Posted on EventX",
            admins,
            f"A new {category} ad has been posted by {current_user.full_name}.",
        )
        flash("Ad posted successfully.", "success")
        return redirect(url_for("my_profile"))

    ads = Ad.query.filter_by(category=category).order_by(Ad.created_at.desc()).all()
    return render_page("category_portal", category=category, ads=ads)


@app.route("/admin/panel")
@login_required
@role_required("admin")
def admin_panel():
    ads = Ad.query.order_by(Ad.created_at.desc()).all()
    quotations = Quotation.query.order_by(Quotation.created_at.desc()).all()
    past_works = PastWork.query.filter_by(vendor_id=current_user.id).all()
    return render_page("admin_panel", ads=ads, quotations=quotations, past_works=past_works)


@app.route("/admin/quotation/<int:ad_id>", methods=["POST"])
@login_required
@role_required("admin")
def create_quotation(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    quotation = Quotation(
        ad_id=ad.id,
        vendor_id=current_user.id,
        price=float(request.form["price"]),
        details=request.form["details"].strip(),
        contact_name=current_user.full_name,
        contact_phone=current_user.phone,
        contact_email=current_user.email,
    )
    ad.status = "quoted"
    db.session.add(quotation)
    db.session.commit()

    send_email(
        "New EventX Quotation",
        [ad.user.email],
        f"A quotation has been sent for your ad #{ad.id}.",
    )
    flash("Quotation sent successfully.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/past-work", methods=["POST"])
@login_required
@role_required("admin")
def add_past_work():
    image = request.files.get("image")
    if not image or not image.filename:
        flash("Past work image is required.", "error")
        return redirect(url_for("admin_panel"))

    filename = photos.save(image)
    work = PastWork(
        title=request.form["title"].strip(),
        description=request.form["description"].strip(),
        image_filename=filename,
        vendor_id=current_user.id,
    )
    db.session.add(work)
    db.session.commit()
    flash("Past work added.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/quotations")
@login_required
@role_required("user")
def quotation_comparison():
    user_ads = Ad.query.filter_by(user_id=current_user.id).all()
    ad_ids = [ad.id for ad in user_ads]
    quotations = (
        Quotation.query.filter(Quotation.ad_id.in_(ad_ids)).order_by(Quotation.created_at.desc()).all()
        if ad_ids
        else []
    )
    return render_page("quotation_comparison", quotations=quotations)


@app.route("/quotation/<int:quotation_id>/accept", methods=["POST"])
@login_required
@role_required("user")
def accept_quotation(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    if quotation.ad.user_id != current_user.id:
        flash("Unauthorized action.", "error")
        return redirect(url_for("quotation_comparison"))

    for q in quotation.ad.quotations:
        q.status = "accepted" if q.id == quotation.id else "rejected"
    quotation.ad.status = "accepted"
    db.session.commit()
    flash("Quotation accepted. Proceed to billing.", "success")
    return redirect(url_for("cart"))


@app.route("/cart")
@login_required
@role_required("user")
def cart():
    accepted = (
        Quotation.query.join(Ad)
        .filter(Ad.user_id == current_user.id, Quotation.status == "accepted")
        .all()
    )
    return render_page("cart", quotations=accepted)


@app.route("/payment/<int:quotation_id>", methods=["POST"])
@login_required
@role_required("user")
def simulate_payment(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    if quotation.ad.user_id != current_user.id:
        flash("Unauthorized payment request.", "error")
        return redirect(url_for("cart"))

    existing = Bill.query.filter_by(quotation_id=quotation.id).first()
    if existing:
        flash("Bill already generated for this quotation.", "success")
        return redirect(url_for("bill_history"))

    bill = Bill(amount=quotation.price, user_id=current_user.id, quotation_id=quotation.id, invoice_path="")
    db.session.add(bill)
    db.session.commit()

    bill.invoice_path = generate_invoice(bill, current_user, quotation)
    quotation.ad.status = "billed"
    db.session.commit()

    send_email(
        "EventX Bill Generated",
        [current_user.email],
        f"Your bill #{bill.id} for INR {bill.amount:.2f} is generated.",
    )
    flash("Payment simulated and bill generated.", "success")
    return redirect(url_for("bill_history"))


@app.route("/bills")
@login_required
@role_required("user")
def bill_history():
    bills = Bill.query.filter_by(user_id=current_user.id).order_by(Bill.created_at.desc()).all()
    return render_page("bill_history", bills=bills)


@app.route("/invoice/<path:filename>")
@login_required
def invoice(filename):
    return send_from_directory(os.path.join(app.static_folder, "invoices"), filename)


@app.route("/profile")
@login_required
@role_required("user")
def my_profile():
    ads = Ad.query.filter_by(user_id=current_user.id).order_by(Ad.created_at.desc()).all()
    accepted = (
        Quotation.query.join(Ad)
        .filter(Ad.user_id == current_user.id, Quotation.status == "accepted")
        .all()
    )
    bills = Bill.query.filter_by(user_id=current_user.id).order_by(Bill.created_at.desc()).all()
    return render_page("user_profile", ads=ads, accepted=accepted, bills=bills)


@app.route("/vendor/profile")
@login_required
@role_required("admin")
def vendor_profile():
    past_works = PastWork.query.filter_by(vendor_id=current_user.id).all()
    active_quotations = Quotation.query.filter_by(vendor_id=current_user.id, status="pending").all()
    completed = Quotation.query.filter_by(vendor_id=current_user.id, status="accepted").all()
    return render_page(
        "vendor_profile",
        past_works=past_works,
        active_quotations=active_quotations,
        completed=completed,
    )


with app.app_context():
    db.create_all()
    bootstrap_admin()


if __name__ == "__main__":
    app.run(debug=True)
