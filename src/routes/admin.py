# ╔═══════════════════════════════════════════════════════════╗
#   admin routes
#       This file routes all traffic from the following routes:
#       - /config
# ╚═══════════════════════════════════════════════════════════╝

from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from src.models import User, db
from src.utils.decorators import admin_required
import os

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/config', methods=['GET', 'POST'])
@login_required
@admin_required
def config():
    if request.method == 'POST':
        if 'new_user' in request.form:
            username = request.form.get('new_username')
            password = request.form.get('new_password')
            role = request.form.get('role', 'user')
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists')
            else:
                new_user = User(
                    username=username,
                    password=generate_password_hash(password),
                    role=role
                )
                db.session.add(new_user)
                db.session.commit()
                flash('User created successfully')
        
        if 'update_bucket' in request.form:
            new_bucket_name = request.form.get('bucket_name')
            if new_bucket_name:
                session['storage_bucket'] = new_bucket_name
                flash('Storage bucket updated successfully')
        # Add new condition for updating YouTube API key
        if 'update_api_key' in request.form:
            new_api_key = request.form.get('api_key')
            if new_api_key:
                # Store in both session and environment
                session['youtube_api_key'] = new_api_key
                os.environ['YOUTUBE_API_KEY'] = new_api_key
                flash('YouTube API key updated successfully')

        use_google_api = 'use_google_api' in request.form
        session['use_google_api'] = use_google_api

        return redirect(url_for('admin.config'))
        
    users = User.query.all()
    use_google_api = session.get('use_google_api', True)
    current_bucket = session.get('storage_bucket', 'itc-388-youtube-r6')
    current_api_key = session.get('youtube_api_key', '') 
    return render_template('config.html', 
                         use_google_api=use_google_api,
                         current_bucket=current_bucket,
                         current_api_key=current_api_key,
                         users=users)
