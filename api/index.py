import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Admin, run_migrations

# Create all database tables and default admin on startup
with app.app_context():
    db.create_all()
    run_migrations()
    
    # Admin credentials from environment variables (secure)
    admin_configs = [
        {
            'username': os.environ.get('ADMIN1_USER'),
            'email': os.environ.get('ADMIN1_EMAIL'),
            'password': os.environ.get('ADMIN1_PASS')
        },
        {
            'username': os.environ.get('ADMIN2_USER'),
            'email': os.environ.get('ADMIN2_EMAIL'),
            'password': os.environ.get('ADMIN2_PASS')
        },
        {
            'username': os.environ.get('ADMIN3_USER'),
            'email': os.environ.get('ADMIN3_EMAIL'),
            'password': os.environ.get('ADMIN3_PASS')
        }
    ]
    
    for config in admin_configs:
        if config['username'] and config['email'] and config['password']:
            if not Admin.query.filter_by(username=config['username']).first():
                admin = Admin(
                    username=config['username'],
                    email=config['email'],
                    role='admin'
                )
                admin.set_password(config['password'])
                db.session.add(admin)
                db.session.commit()

# Export the Flask app directly for Vercel
# Vercel expects the WSGI application to be named 'app'
app = app
