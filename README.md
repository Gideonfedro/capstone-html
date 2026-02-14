# EventX – OLX-Style Event Management Marketplace

A professional Flask full-stack marketplace platform for event requirement posting, vendor quotation management, and billing simulation.

## 1) Project Structure

```text
capstone-html/
├── app.py
├── models.py
├── requirements.txt
├── README.md
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   ├── uploads/
│   └── invoices/
└── templates/
    └── app.html  # Single template containing all pages
```

## 2) Setup Instructions

1. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure email (for OTP + notifications)**
   ```bash
   export MAIL_SERVER=smtp.gmail.com
   export MAIL_PORT=587
   export MAIL_USERNAME=your_email@example.com
   export MAIL_PASSWORD=your_app_password
   export MAIL_DEFAULT_SENDER=your_email@example.com
   export SECRET_KEY='change-this-in-production'
   ```
4. **Run app**
   ```bash
   python app.py
   ```
5. Open `http://127.0.0.1:5000`

## 3) Default Admin Credentials

- Email: `admin@eventx.local`
- Password: `Admin@123`

> Change this immediately for real deployment.

## 4) Features Added

- Dual role authentication (User + Vendor/Admin)
- Admin 2FA OTP verification via Flask-Mail
- Event dashboard with three category portals:
  - Private Events
  - Devotional Events
  - Political Events
- User ad posting with location/date/description/photo upload
- Admin quotation engine with pricing and details
- Quotation comparison table and accept flow
- Contact sharing after accepted quote
- Billing/cart payment simulation
- PDF invoice generation using FPDF
- Bill history tracking and invoice download
- User profile with personal info/ads/accepted quotations/bills
- Vendor profile with past works/active quotations/completed events
- Dark-mode neon glassmorphism UI with responsive layout
- Single-template architecture: all UI pages consolidated in `templates/app.html`

## 5) Workflow Summary

1. User registers and logs in.
2. User opens dashboard and picks event category.
3. User posts ad with event requirement details + image.
4. Vendor receives ad in admin panel and sends quotation.
5. User compares quotations and accepts one option.
6. Accepted quotation reveals vendor contact details.
7. User proceeds to cart and simulates payment.
8. Bill is generated and PDF invoice is stored + listed in bill history.
9. Vendor can showcase past works in vendor profile.

## 6) Production Notes

- Use PostgreSQL/MySQL in production instead of SQLite.
- Use Celery/RQ for background email jobs.
- Protect forms with CSRF (Flask-WTF) and add rate-limits for login/OTP.
- Store uploads in cloud storage (S3/GCS) for scalability.
