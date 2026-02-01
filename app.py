from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from config import Config
import os
import secrets
import smtplib
import bleach
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import re
from functools import lru_cache

# Set for O(1) lookup of blocked disposable email domains
BLOCKED_EMAIL_DOMAINS = frozenset({
    'tempmail.com', 'temp-mail.org', 'guerrillamail.com', 'guerrillamail.org',
    'mailinator.com', 'throwaway.email', 'fakeinbox.com', 'trashmail.com',
    'yopmail.com', 'sharklasers.com', 'guerrillamail.info', 'grr.la',
    'mailnesia.com', 'mytemp.email', 'tempmailaddress.com', 'throwawaymail.com',
    'getnada.com', 'tempail.com', 'emailondeck.com', 'mohmal.com',
    '10minutemail.com', '10minutemail.net', 'minutemail.com', 'tempinbox.com',
    'discard.email', 'mailcatch.com', 'mailsac.com', 'spamgourmet.com',
    'maildrop.cc', 'getairmail.com', 'fakemailgenerator.com', 'emailfake.com',
    'crazymailing.com', 'tempmailo.com', 'tempr.email', 'dispostable.com',
    'mailnull.com', 'spamfree24.org', 'binkmail.com', 'safetymail.info'
})

# Pre-compile regex for better performance
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

@lru_cache(maxsize=256)
def is_valid_email(email):
    """Validate email format and check against blocked domains (cached)"""
    if not email or len(email) < 6:
        return False, "Email is required" if not email else "Email is too short"
    
    email = email.strip().lower()
    
    # Fast regex check with pre-compiled pattern
    if not EMAIL_PATTERN.match(email):
        return False, "Invalid email format"
    
    # Extract and validate domain
    domain = email.rsplit('@', 1)[-1]
    if '.' not in domain or domain in BLOCKED_EMAIL_DOMAINS:
        return (False, "Invalid email domain") if '.' not in domain else (False, "Disposable/temporary emails are not allowed.")
    
    return True, "Valid email"


# Password strength validation
def is_strong_password(password):
    """Check password strength: min 8 chars, 1 uppercase, 1 lowercase, 1 digit"""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, "Strong password"


# Input sanitization
def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if text is None:
        return None
    return bleach.clean(str(text).strip(), tags=[], strip=True)


# Use /tmp for instance folder (writable in serverless environments)
app = Flask(__name__, instance_path='/tmp')
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)

# CSRF Protection
csrf = CSRFProtect(app)

# Rate Limiting (uses in-memory storage - for production use Redis)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Security headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    # CSP - allow Bootstrap and FontAwesome CDNs
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "connect-src 'self';"
    )
    return response

# ==================== Models ====================

class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    role = db.Column(db.String(20), default='admin')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'


class Election(db.Model):
    __tablename__ = 'elections'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='upcoming')  # upcoming, active, completed
    created_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    candidates = db.relationship('Candidate', backref='election', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='election', lazy=True, cascade='all, delete-orphan')
    creator = db.relationship('Admin', foreign_keys=[created_by])

    def update_status(self):
        now = datetime.now()
        if now < self.start_date:
            self.status = 'upcoming'
        elif now > self.end_date:
            self.status = 'completed'
        else:
            self.status = 'active'


class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    party = db.Column(db.String(100))
    description = db.Column(db.Text)
    photo_url = db.Column(db.String(255))
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    votes = db.relationship('Vote', backref='candidate', lazy=True)

    def get_vote_count(self):
        return Vote.query.filter_by(candidate_id=self.id).count()


class Voter(db.Model):
    __tablename__ = 'voters'
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    votes = db.relationship('Vote', backref='voter', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_voted(self, election_id):
        return Vote.query.filter_by(voter_id=self.id, election_id=election_id).first() is not None


class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('voters.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# ==================== Routes ====================

# Store admin access tokens (in production, use Redis or database)
admin_access_tokens = {}
password_reset_tokens = {}

def send_admin_access_email(email, token, base_url):
    """Send admin access link via email"""
    try:
        access_link = f"{base_url}/admin/verify/{token}"
        
        msg = MIMEMultipart()
        msg['From'] = Config.MAIL_USERNAME
        msg['To'] = email
        msg['Subject'] = 'Admin Access Link - Online Voting System'
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h2 style="color: #2563eb;">🔐 Admin Access Request</h2>
                <p>You requested access to the Admin Login page.</p>
                <p>Click the button below to access the admin login:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{access_link}" style="background: #2563eb; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Access Admin Login
                    </a>
                </p>
                <p style="color: #666; font-size: 14px;">This link expires in 10 minutes.</p>
                <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">Online Voting System</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_password_reset_email(email, token, base_url):
    """Send password reset link via email"""
    try:
        reset_link = f"{base_url}/voter/reset-password/{token}"
        
        msg = MIMEMultipart()
        msg['From'] = Config.MAIL_USERNAME
        msg['To'] = email
        msg['Subject'] = 'Password Reset - Online Voting System'
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h2 style="color: #2563eb;">🔑 Password Reset Request</h2>
                <p>You requested to reset your password.</p>
                <p>Click the button below to set a new password:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background: #2563eb; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Reset Password
                    </a>
                </p>
                <p style="color: #666; font-size: 14px;">This link expires in 15 minutes.</p>
                <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">Online Voting System</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


@app.route('/admin', methods=['GET', 'POST'])
def admin_email_verify():
    """Admin access - require email verification first"""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        # Check if email belongs to an admin
        admin = Admin.query.filter_by(email=email).first()
        if admin:
            # Generate secure token
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(minutes=10)
            admin_access_tokens[token] = {'email': email, 'expiry': expiry}
            
            # Get base URL
            base_url = request.url_root.rstrip('/')
            
            # Send email
            if send_admin_access_email(email, token, base_url):
                flash('Access link sent to your email! Check your inbox.', 'success')
            else:
                flash('Failed to send email. Please try again or contact support.', 'danger')
        else:
            # Don't reveal if email exists or not
            flash('If this email is registered as admin, you will receive an access link.', 'info')
        
        return redirect(url_for('admin_email_verify'))
    
    return render_template('admin/email_verify.html')


@app.route('/admin/verify/<token>')
def admin_verify_token(token):
    """Verify the token and redirect to login"""
    if token in admin_access_tokens:
        token_data = admin_access_tokens[token]
        
        if datetime.now() < token_data['expiry']:
            # Token is valid - store in session and redirect to login
            session['admin_access_verified'] = True
            session['admin_access_email'] = token_data['email']
            session['admin_access_expiry'] = (datetime.now() + timedelta(minutes=15)).isoformat()
            
            # Remove used token
            del admin_access_tokens[token]
            
            flash('Email verified! Please login with your credentials.', 'success')
            return redirect(url_for('login'))
        else:
            # Token expired
            del admin_access_tokens[token]
            flash('Access link has expired. Please request a new one.', 'danger')
    else:
        flash('Invalid or expired access link.', 'danger')
    
    return redirect(url_for('admin_email_verify'))


@app.route('/')
def index():
    elections = Election.query.all()
    for election in elections:
        election.update_status()
    db.session.commit()
    return render_template('index.html', elections=elections)


@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", error_message="Too many login attempts. Please wait a minute.")
def login():
    # Check if admin access is verified
    if not session.get('admin_access_verified'):
        flash('Please verify your email first to access admin login.', 'warning')
        return redirect(url_for('admin_email_verify'))
    
    # Check if session expired
    expiry = session.get('admin_access_expiry')
    if expiry and datetime.fromisoformat(expiry) < datetime.now():
        session.pop('admin_access_verified', None)
        session.pop('admin_access_email', None)
        session.pop('admin_access_expiry', None)
        flash('Session expired. Please verify your email again.', 'warning')
        return redirect(url_for('admin_email_verify'))
    
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            login_user(admin)
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('admin/login.html')


@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    elections = Election.query.all()
    
    for election in elections:
        election.update_status()
    db.session.commit()
    
    total_elections = Election.query.count()
    total_candidates = Candidate.query.count()
    total_voters = Voter.query.count()
    total_votes = Vote.query.count()
    
    return render_template('admin/dashboard.html', 
                         elections=elections,
                         total_elections=total_elections,
                         total_candidates=total_candidates,
                         total_voters=total_voters,
                         total_votes=total_votes)


@app.route('/admin/elections')
@login_required
def manage_elections():
    elections = Election.query.all()
    
    # Update election statuses based on current time
    for election in elections:
        election.update_status()
    db.session.commit()
    
    return render_template('admin/elections.html', elections=elections)


@app.route('/admin/elections/add', methods=['GET', 'POST'])
@login_required
def add_election():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%dT%H:%M')
        
        election = Election(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            created_by=current_user.id
        )
        election.update_status()
        
        db.session.add(election)
        db.session.commit()
        flash('Election created successfully!', 'success')
        return redirect(url_for('manage_elections'))
    
    return render_template('admin/add_election.html')


@app.route('/admin/elections/<int:election_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_election(election_id):
    election = Election.query.get_or_404(election_id)
    
    if request.method == 'POST':
        election.title = request.form.get('title')
        election.description = request.form.get('description')
        election.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M')
        election.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%dT%H:%M')
        election.update_status()
        
        db.session.commit()
        flash('Election updated successfully!', 'success')
        return redirect(url_for('manage_elections'))
    
    return render_template('admin/edit_election.html', election=election)


@app.route('/admin/elections/<int:election_id>/delete', methods=['POST'])
@login_required
def delete_election(election_id):
    election = Election.query.get_or_404(election_id)
    db.session.delete(election)
    db.session.commit()
    flash('Election deleted successfully!', 'success')
    return redirect(url_for('manage_elections'))


@app.route('/admin/elections/<int:election_id>/candidates')
@login_required
def manage_candidates(election_id):
    election = Election.query.get_or_404(election_id)
    return render_template('admin/candidates.html', election=election)


@app.route('/admin/elections/<int:election_id>/candidates/add', methods=['GET', 'POST'])
@login_required
def add_candidate(election_id):
    election = Election.query.get_or_404(election_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        party = request.form.get('party')
        description = request.form.get('description')
        photo_url = request.form.get('photo_url')
        
        candidate = Candidate(
            name=name,
            party=party,
            description=description,
            photo_url=photo_url,
            election_id=election_id
        )
        
        db.session.add(candidate)
        db.session.commit()
        flash('Candidate added successfully!', 'success')
        return redirect(url_for('manage_candidates', election_id=election_id))
    
    return render_template('admin/add_candidate.html', election=election)


@app.route('/admin/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    
    if request.method == 'POST':
        candidate.name = request.form.get('name')
        candidate.party = request.form.get('party')
        candidate.description = request.form.get('description')
        candidate.photo_url = request.form.get('photo_url')
        
        db.session.commit()
        flash('Candidate updated successfully!', 'success')
        return redirect(url_for('manage_candidates', election_id=candidate.election_id))
    
    return render_template('admin/edit_candidate.html', candidate=candidate)


@app.route('/admin/candidates/<int:candidate_id>/delete', methods=['POST'])
@login_required
def delete_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    election_id = candidate.election_id
    db.session.delete(candidate)
    db.session.commit()
    flash('Candidate deleted successfully!', 'success')
    return redirect(url_for('manage_candidates', election_id=election_id))


@app.route('/admin/elections/<int:election_id>/results')
@login_required
def view_results(election_id):
    election = Election.query.get_or_404(election_id)
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    
    results = []
    for candidate in candidates:
        results.append({
            'id': candidate.id,
            'name': candidate.name,
            'party': candidate.party,
            'votes': candidate.get_vote_count()
        })
    
    total_votes = sum(r['votes'] for r in results)
    
    # Get detailed vote information (who voted for whom) - for admin and teachers only
    detailed_votes = []
    votes = Vote.query.filter_by(election_id=election_id).all()
    for vote in votes:
        detailed_votes.append({
            'voter_name': vote.voter.name,
            'voter_id': vote.voter.voter_id,
            'candidate_name': vote.candidate.name,
            'timestamp': vote.timestamp
        })
    
    return render_template('admin/results.html', 
                         election=election, 
                         results=results,
                         total_votes=total_votes,
                         detailed_votes=detailed_votes)


@app.route('/api/elections/<int:election_id>/results')
def api_results(election_id):
    election = Election.query.get_or_404(election_id)
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    
    results = []
    for candidate in candidates:
        results.append({
            'id': candidate.id,
            'name': candidate.name,
            'party': candidate.party,
            'votes': candidate.get_vote_count()
        })
    
    return jsonify(results)


@app.route('/voter/register', methods=['GET', 'POST'])
@limiter.limit("10 per hour", error_message="Too many registration attempts. Please try again later.")
def voter_register():
    if request.method == 'POST':
        voter_id = sanitize_input(request.form.get('voter_id'))
        name = sanitize_input(request.form.get('name'))
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        
        # Validate password strength
        is_strong, password_error = is_strong_password(password)
        if not is_strong:
            flash(password_error, 'danger')
            return redirect(url_for('voter_register'))
        
        # Validate email format and check for disposable emails
        is_valid, email_error = is_valid_email(email)
        if not is_valid:
            flash(email_error, 'danger')
            return redirect(url_for('voter_register'))
        
        # Check if voter ID already exists
        if Voter.query.filter_by(voter_id=voter_id).first():
            flash('Voter ID already exists! Please use a different Voter ID.', 'danger')
            return redirect(url_for('voter_register'))
        
        # Check if email already exists
        if Voter.query.filter_by(email=email).first():
            flash('Email already registered! Please use a different email or login.', 'danger')
            return redirect(url_for('voter_register'))
        
        voter = Voter(voter_id=voter_id, name=name, email=email)
        voter.set_password(password)
        
        db.session.add(voter)
        db.session.commit()
        flash('Registration successful! Please login to vote.', 'success')
        return redirect(url_for('voter_login'))
    
    return render_template('voter/register.html')


@app.route('/voter/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", error_message="Too many login attempts. Please wait a minute.")
def voter_login():
    if request.method == 'POST':
        email = sanitize_input(request.form.get('email')).lower()
        password = request.form.get('password')
        
        voter = Voter.query.filter_by(email=email).first()
        
        if voter and voter.check_password(password):
            session['voter_id'] = voter.id
            flash('Login successful!', 'success')
            return redirect(url_for('voter_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('voter/login.html')


@app.route('/voter/forgot-password', methods=['GET', 'POST'])
def voter_forgot_password():
    """Handle forgot password request"""
    if request.method == 'POST':
        voter_id = request.form.get('voter_id', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        # Find voter by voter_id and email
        voter = Voter.query.filter_by(voter_id=voter_id, email=email).first()
        
        if voter:
            # Generate secure token
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(minutes=15)
            password_reset_tokens[token] = {
                'voter_id': voter.id,
                'email': email,
                'expiry': expiry
            }
            
            # Get base URL and send email
            base_url = request.url_root.rstrip('/')
            if send_password_reset_email(email, token, base_url):
                flash('Password reset link sent to your email!', 'success')
            else:
                flash('Failed to send email. Please try again.', 'danger')
        else:
            # Don't reveal if voter exists
            flash('If this voter ID and email match, you will receive a reset link.', 'info')
        
        return redirect(url_for('voter_forgot_password'))
    
    return render_template('voter/forgot_password.html')


@app.route('/voter/reset-password/<token>', methods=['GET', 'POST'])
def voter_reset_password(token):
    """Handle password reset with token"""
    if token not in password_reset_tokens:
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('voter_forgot_password'))
    
    token_data = password_reset_tokens[token]
    
    # Check if token expired
    if datetime.now() > token_data['expiry']:
        del password_reset_tokens[token]
        flash('Reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('voter_forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('voter_reset_password', token=token))
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters!', 'danger')
            return redirect(url_for('voter_reset_password', token=token))
        
        # Update password
        voter = Voter.query.get(token_data['voter_id'])
        if voter:
            voter.set_password(new_password)
            db.session.commit()
            
            # Remove used token
            del password_reset_tokens[token]
            
            flash('Password reset successful! Please login with your new password.', 'success')
            return redirect(url_for('voter_login'))
        else:
            flash('User not found.', 'danger')
            return redirect(url_for('voter_forgot_password'))
    
    return render_template('voter/reset_password.html', token=token)


@app.route('/voter/dashboard')
def voter_dashboard():
    if 'voter_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('voter_login'))
    
    voter = Voter.query.get(session['voter_id'])
    
    # Update election statuses based on current time before filtering
    elections_to_check = Election.query.all()
    for election in elections_to_check:
        election.update_status()
    db.session.commit()
    
    # Show only active elections
    elections = Election.query.filter_by(status='active').all()
    
    return render_template('voter/dashboard.html', voter=voter, elections=elections)


@app.route('/voter/logout')
def voter_logout():
    session.pop('voter_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/voter/vote/<int:election_id>', methods=['GET', 'POST'])
def vote(election_id):
    if 'voter_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('voter_login'))
    
    voter = Voter.query.get(session['voter_id'])
    election = Election.query.get_or_404(election_id)
    
    # Update election status based on current time
    election.update_status()
    db.session.commit()
    
    if election.status != 'active':
        flash('This election is not currently active!', 'warning')
        return redirect(url_for('voter_dashboard'))
    
    if voter.has_voted(election_id):
        flash('You have already voted in this election!', 'warning')
        return redirect(url_for('voter_dashboard'))
    
    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        
        vote = Vote(
            voter_id=voter.id,
            election_id=election_id,
            candidate_id=candidate_id
        )
        
        db.session.add(vote)
        db.session.commit()
        flash('Your vote has been recorded successfully!', 'success')
        return redirect(url_for('voter_dashboard'))
    
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    return render_template('voter/vote.html', election=election, candidates=candidates)


# ==================== Voter Management ====================

@app.route('/admin/voters', methods=['GET'])
@login_required
def manage_voters():
    """View and manage registered voters"""
    # Use joinedload for eager loading to avoid N+1 queries
    voters = Voter.query.options(joinedload(Voter.votes)).order_by(Voter.created_at.desc()).all()
    
    return render_template('admin/voters.html', voters=voters)


@app.route('/admin/voters/<int:voter_id>/delete', methods=['POST'])
@login_required
def delete_voter(voter_id):
    """Delete a voter account"""
    voter = Voter.query.get_or_404(voter_id)
    
    voter_name = voter.name
    voter_email = voter.email
    
    # Delete associated votes first (cascade should handle this, but being explicit)
    Vote.query.filter_by(voter_id=voter.id).delete()
    
    db.session.delete(voter)
    db.session.commit()
    flash(f'Voter "{voter_name}" ({voter_email}) deleted successfully!', 'success')
    return redirect(url_for('manage_voters'))


# ==================== Database Viewer ====================

@app.route('/admin/database')
@login_required
def view_database():
    # Get all data from tables
    admins = Admin.query.all()
    voters = Voter.query.all()
    elections = Election.query.all()
    candidates = Candidate.query.all()
    votes = Vote.query.all()
    
    return render_template('admin/database.html',
                         admins=admins,
                         voters=voters,
                         elections=elections,
                         candidates=candidates,
                         votes=votes)


# ==================== Initialize Database ====================

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin if not exists
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(
                username='admin', 
                email='admin@voting.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
