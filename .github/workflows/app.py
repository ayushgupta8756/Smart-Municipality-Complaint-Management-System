"""
Smart Municipality Complaint Management System (SMCMS)
--------------------------------------------------------
Flask + SQLite + Flask-Mail based complaint portal.

Flow:
1. User registers (name, email, phone, password)
2. User logs in, submits a complaint (category, description, location)
3. Confirmation email is sent instantly to user's registered email
   (opens on phone via Gmail/Outlook app -> feels like a notification)
4. Admin logs in to /admin, updates complaint status
5. On every status change, an email is sent to the user automatically
   -> when status = "Resolved", user gets a "Complaint Completed" email
"""

import os
from werkzeug.utils import secure_filename
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

# ---------------------------------------------------------------
# App Config
# ---------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smcms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---- Email (SMTP) config ----
# Gmail use kar rahe ho toh:
#   1. Google Account -> Security -> 2-Step Verification ON karo
#   2. "App Passwords" bana kar yaha daalo (normal Gmail password nahi chalega)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ayush.gupta.8153@gmail.com'
app.config['MAIL_PASSWORD'] = 'uukk zdcr vuao usmm'
app.config['MAIL_DEFAULT_SENDER'] = 'ayush.gupta.8153@gmail.com'

db = SQLAlchemy(app)
mail = Mail(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Login First."

ADMIN_EMAIL = "ayush.gupta.8153@gmail.com"

# ---------------------------------------------------------------
# Models
# ---------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    is_admin = db.Column(db.Boolean, default=False)

    # Block suspicious users
    is_blocked = db.Column(db.Boolean, default=False)

    complaints = db.relationship(
        'Complaint',
        backref='user',
        lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    category = db.Column(
        db.String(50),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    location = db.Column(
        db.String(200),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        default='Pending'
    )  # Pending / In Progress / Resolved

    image = db.Column(
        db.String(255),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# ---------------------------------------------------------------
# Email helper
# ---------------------------------------------------------------
def send_email(to, subject, body):
    """Sends an email. Wrapped in try/except so app doesn't crash
    if SMTP creds are not configured yet (useful during dev/testing)."""
    try:
        msg = Message(subject, recipients=[to], body=body)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Could not send email to {to}: {e}")
        return False

# ---------------------------------------------------------------
# Routes
# ---------------------------------------------------------------

@app.route('/')
def index():
    total = Complaint.query.count()

    pending = Complaint.query.filter_by(status="Pending").count()

    resolved = Complaint.query.filter_by(status="Resolved").count()

    in_progress = Complaint.query.filter_by(status="In Progress").count()

    return render_template(
        'index.html',
        total=total,
        pending=pending,
        resolved=resolved,
        in_progress=in_progress
    )


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash(
                'Already email has been registered. Login karo.',
                'danger'
            )
            return redirect(url_for('register'))

        # Create new user
        user = User(
            name=name,
            email=email,
            phone=phone
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Welcome email
        send_email(
            email,
            "Welcome to Smart Municipality Complaint Management System",
            f"""Hi {name},

Your account has been created successfully.

You can now login to the system and submit complaints.

- SMCMS Team"""
        )

        flash(
            'Registration successful! Do Login.',
            'success'
        )

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            login_user(user)

            # Check whether the account is blocked
            if user.is_blocked:
                flash(
                    'Your account is currently blocked due to excessive complaints. Please contact the administrator.',
                    'danger'
                )
            else:
                flash(
                    'Login successful!',
                    'success'
                )

            # Admin goes to admin panel
            if user.is_admin:
                return redirect(url_for('admin_panel'))

            # Normal user goes to dashboard
            return redirect(url_for('dashboard'))

        flash(
            'Invalid email or password.',
            'danger'
        )

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():

    complaints = Complaint.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Complaint.created_at.desc()
    ).all()

    pending = Complaint.query.filter_by(
        user_id=current_user.id,
        status="Pending"
    ).count()

    progress = Complaint.query.filter_by(
        user_id=current_user.id,
        status="In Progress"
    ).count()

    resolved = Complaint.query.filter_by(
        user_id=current_user.id,
        status="Resolved"
    ).count()

    total = Complaint.query.filter_by(
        user_id=current_user.id
    ).count()

    return render_template(
        "dashboard.html",
        complaints=complaints,
        pending=pending,
        progress=progress,
        resolved=resolved,
        total=total
    )

@app.route('/complaint/new', methods=['GET', 'POST'])
@login_required
def new_complaint():

    if request.method == 'POST':

        # =========================
        # CHECK BLOCKED USER
        # =========================

        if current_user.is_blocked:
            flash(
                "Your account has been blocked due to excessive complaints. "
                "Please contact the administrator.",
                "danger"
            )
            return redirect(url_for('dashboard'))

        # =========================
        # GET FORM DATA
        # =========================

        category = request.form['category']
        description = request.form['description']
        location = request.form['location']

        # =========================
        # SAME USER + SAME LOCATION
        # MAXIMUM 3 COMPLAINTS
        # =========================

        same_location_count = Complaint.query.filter_by(
            user_id=current_user.id,
            location=location
        ).count()

        if same_location_count >= 3:
            flash(
                "You can submit a maximum of 3 complaints "
                "for the same location.",
                "warning"
            )
            return redirect(url_for('new_complaint'))

        # =========================
        # IMAGE UPLOAD
        # =========================

        image = request.files.get('image')
        filename = None

        if image and image.filename != "":
            filename = secure_filename(image.filename)

            upload_folder = os.path.join(
                "static",
                "uploads"
            )

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            image.save(
                os.path.join(
                    upload_folder,
                    filename
                )
            )

        # =========================
        # CREATE COMPLAINT
        # =========================

        complaint = Complaint(
            user_id=current_user.id,
            category=category,
            description=description,
            location=location,
            image=filename
        )

        db.session.add(complaint)
        db.session.commit()

        # =========================
        # AUTOMATIC USER BLOCKING
        # =========================

        total_user_complaints = Complaint.query.filter_by(
            user_id=current_user.id
        ).count()

        if total_user_complaints >= 10:

            current_user.is_blocked = True
            db.session.commit()

            send_email(
                current_user.email,
                "⚠️ Account Blocked - Smart Municipality",
                f"""Hi {current_user.name},

Your complaint has been registered successfully.

However, your account has now been blocked because
10 or more complaints have been submitted from your account.

Total Complaints: {total_user_complaints}

Please contact the administrator if you believe
this action was taken incorrectly.

- SMCMS Team"""
            )

        # =========================
        # EMAIL TO ADMIN
        # =========================

        send_email(
            "ayush.gupta.8153@gmail.com",
            f"🚨 New Complaint Received - #{complaint.id}",
            f"""A new complaint has been submitted.

Complaint ID : #{complaint.id}
User Name    : {current_user.name}
User Email   : {current_user.email}
Phone        : {current_user.phone}

Category     : {category}
Location     : {location}

Description:
{description}

Status       : Pending
"""
        )

        # =========================
        # CONFIRMATION EMAIL TO USER
        # =========================

        send_email(
            current_user.email,
            f"Complaint Registered - #{complaint.id}",
            f"""Hi {current_user.name},

Your complaint has been registered successfully.

Complaint ID : #{complaint.id}
Category     : {category}
Location     : {location}
Description  : {description}
Status       : Pending

Thank you for your submission.

- SMCMS Team"""
        )

        # =========================
        # SUCCESS / BLOCK MESSAGE
        # =========================

        if current_user.is_blocked:
            flash(
                "Complaint submitted successfully. "
                "Your account has now been blocked due to excessive complaints. "
                "Please contact the administrator.",
                "danger"
            )
        else:
            flash(
                "Complaint submitted successfully!",
                "success"
            )

        return redirect(url_for('dashboard'))

    return render_template('new_complaint.html')


# =========================
# COMPLAINT DETAIL
# =========================

@app.route('/complaint/<int:complaint_id>')
@login_required
def complaint_detail(complaint_id):

    complaint = Complaint.query.get_or_404(complaint_id)

    if (
        complaint.user_id != current_user.id
        and not current_user.is_admin
    ):
        flash(
            'You are not the owner of this complaint.',
            'danger'
        )
        return redirect(url_for('dashboard'))

    return render_template(
        'complaint_detail.html',
        complaint=complaint
    )
 
# ---------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------

@app.route('/admin')
@login_required
def admin_panel():

    if not current_user.is_admin:
        flash(
            'Access denied. Only admins can access this page.',
            'danger'
        )
        return redirect(url_for('dashboard'))

    search = request.args.get('search', '')
    status = request.args.get('status', '')

    # Complaints
    complaints = Complaint.query

    if search:
        complaints = complaints.filter(
            db.or_(
                Complaint.category.ilike(f"%{search}%"),
                Complaint.location.ilike(f"%{search}%")
            )
        )

    if status:
        complaints = complaints.filter_by(status=status)

    complaints = complaints.order_by(
        Complaint.created_at.desc()
    ).all()

    # Complaint Statistics
    total = Complaint.query.count()

    pending = Complaint.query.filter_by(
        status="Pending"
    ).count()

    in_progress = Complaint.query.filter_by(
        status="In Progress"
    ).count()

    resolved = Complaint.query.filter_by(
        status="Resolved"
    ).count()

    # Blocked Users
    blocked_users = User.query.filter_by(
        is_blocked=True
    ).all()

    return render_template(
        'admin.html',
        complaints=complaints,
        search=search,
        status=status,
        total=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        blocked_users=blocked_users
    )


# =========================
# UPDATE COMPLAINT STATUS
# =========================

@app.route(
    '/admin/update/<int:complaint_id>',
    methods=['POST']
)
@login_required
def update_status(complaint_id):

    if not current_user.is_admin:
        flash(
            'Access denied.',
            'danger'
        )
        return redirect(url_for('dashboard'))

    complaint = Complaint.query.get_or_404(
        complaint_id
    )

    new_status = request.form['status']

    complaint.status = new_status
    complaint.updated_at = datetime.utcnow()

    db.session.commit()

    # Email user about status update
    if new_status == "Resolved":

        subject = f"✅ Complaint #{complaint.id} Resolved"

        body = f"""
Hello {complaint.user.name},

Good news! 🎉

Your complaint has been resolved.

Complaint ID : {complaint.id}
Category     : {complaint.category}
Location     : {complaint.location}
Status       : {new_status}

Thank you for using Smart Municipality Portal.

- SMCMS Team
"""

    elif new_status == "In Progress":

        subject = f"🚧 Complaint #{complaint.id} In Progress"

        body = f"""
Hello {complaint.user.name},

Your complaint is currently being processed.

Complaint ID : {complaint.id}
Category     : {complaint.category}
Location     : {complaint.location}
Status       : {new_status}

We will update you once it is resolved.

- SMCMS Team
"""

    else:

        subject = f"📝 Complaint #{complaint.id} Status Updated"

        body = f"""
Hello {complaint.user.name},

Your complaint status has been updated.

Complaint ID : {complaint.id}
Category     : {complaint.category}
Location     : {complaint.location}
Status       : {new_status}

- SMCMS Team
"""

    # Send status notification email
    send_email(
        complaint.user.email,
        subject,
        body
    )

    flash(
        'Status updated and user notified.',
        'success'
    )

    return redirect(url_for('admin_panel'))


# =========================
# UNBLOCK USER
# =========================

@app.route(
    '/admin/unblock/<int:user_id>',
    methods=['POST']
)
@login_required
def unblock_user(user_id):

    if not current_user.is_admin:
        flash(
            'Access denied. Only admins can unblock users.',
            'danger'
        )
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    user.is_blocked = False

    db.session.commit()

    flash(
        f'User "{user.name}" has been unblocked successfully.',
        'success'
    )

    return redirect(url_for('admin_panel'))


# ---------------------------------------------------------------
# DB init + first-run admin creation
# ---------------------------------------------------------------
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email=ADMIN_EMAIL).first():
            admin = User(name='Admin', email=ADMIN_EMAIL, phone='0000000000', is_admin=True)
            admin.set_password('admin123')  # change after first login
            db.session.add(admin)
            db.session.commit()
            print(f"[INFO] Default admin created -> email: {ADMIN_EMAIL} | password: admin123")


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
