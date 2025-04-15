from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import logging
import os
from datetime import datetime
from src.youtube_stats import YouTubeStats
from src.sentiment_analyzer import SentimentAnalyzer, LocalSentimentAnalyzer
from src.data_storage import DataStorage
from src.models import User, db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app():
    app = Flask(__name__, template_folder='src/templates')
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key_here')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'login'

    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin-password'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

    return app

app = create_app()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.template_filter('format_date')
def format_date(date_string):
    try:
        date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
        return date.strftime("%b %d, %Y")
    except Exception as e:
        logger.error(f"Error formatting date: {str(e)}")
        return date_string

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
        return redirect(url_for('homepage'))
        return render_template('login.html', error="Invalid username or password")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
def homepage():
    return render_template('homepage.html')

@app.route('/config', methods=['GET', 'POST'])
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
        use_google_api = 'use_google_api' in request.form
        session['use_google_api'] = use_google_api
        
        return redirect(url_for('config'))
        
    users = User.query.all()
    use_google_api = session.get('use_google_api', True)
    current_bucket = session.get('storage_bucket', 'itc-388-youtube-r6')
    return render_template('config.html', 
                         use_google_api=use_google_api,
                         current_bucket=current_bucket,
                         users=users)

@app.route('/sentiment', methods=['GET'])
@login_required
def sentiment_analysis():
    try:
        youtube_stats = YouTubeStats()
        videos = youtube_stats.search_privacy_videos(max_results=20)
        
        if isinstance(videos, dict) and 'error' in videos:
            return render_template('sentiment.html',
                                   error=videos['error'],
                                   videos=[],
                                   comments=[],
                                   selected_video=None,
                                   selected_video_id=None,
                                   sentiment_stats=None,
                                   comments_limited=False,
                                   use_google_api=session.get('use_google_api', True))

        selected_video_id = request.args.get('video_id')
        selected_video = None
        comments = []
        sentiment_stats = None
        comments_limited = False

        if selected_video_id:
            selected_video = next((video for video in videos if video['id'] == selected_video_id), None)

            if selected_video:
                total_comment_count = int(selected_video.get('comments', '0'))
                if total_comment_count > 50:
                    comments_limited = True

                comments_data = youtube_stats.get_video_comments(selected_video_id, max_results=50)

                if isinstance(comments_data, dict) and 'error' in comments_data:
                    return render_template('sentiment.html',
                                           error=comments_data['error'],
                                           videos=videos,
                                           comments=[],
                                           selected_video=selected_video,
                                           selected_video_id=selected_video_id,
                                           sentiment_stats=None,
                                           comments_limited=comments_limited,
                                           use_google_api=session.get('use_google_api', True))

                use_google_api = session.get('use_google_api', True)

                try:
                    sentiment_analyzer = SentimentAnalyzer() if use_google_api else LocalSentimentAnalyzer()
                except Exception as e:
                    logger.error(f"Error initializing sentiment analyzer: {str(e)}")
                    sentiment_analyzer = LocalSentimentAnalyzer()
                    use_google_api = False
                    session['use_google_api'] = False

                for comment in comments_data:
                    if not comment['text']:
                        continue
                    sentiment = sentiment_analyzer.analyze_text(comment['text'])
                    comment['sentiment'] = sentiment

                try:
                    storage = DataStorage('data_privacy_analysis')
                    storage.save_comments_data(selected_video_id, comments_data)
                except Exception as e:
                    logger.error(f"Error saving to Cloud Storage: {str(e)}")

                total_comments = len(comments_data)
                positive_count = sum(1 for comment in comments_data if comment.get('sentiment', {}).get('category') == 'positive')
                neutral_count = sum(1 for comment in comments_data if comment.get('sentiment', {}).get('category') == 'neutral')
                negative_count = sum(1 for comment in comments_data if comment.get('sentiment', {}).get('category') == 'negative')

                positive_percent = int((positive_count / total_comments) * 100) if total_comments > 0 else 0
                neutral_percent = int((neutral_count / total_comments) * 100) if total_comments > 0 else 0
                negative_percent = int((negative_count / total_comments) * 100) if total_comments > 0 else 0

                sentiment_stats = {
                    'total_comments': total_comments,
                    'positive_count': positive_count,
                    'neutral_count': neutral_count,
                    'negative_count': negative_count,
                    'positive_percent': positive_percent,
                    'neutral_percent': neutral_percent,
                    'negative_percent': negative_percent
                }

                comments = comments_data

        return render_template('sentiment.html',
                               videos=videos,
                               comments=comments,
                               selected_video=selected_video,
                               selected_video_id=selected_video_id,
                               sentiment_stats=sentiment_stats,
                               error=None,
                               comments_limited=comments_limited,
                               use_google_api=session.get('use_google_api', True))

    except Exception as e:
        logger.error(f"Error in sentiment analysis route: {str(e)}")
        return render_template('sentiment.html',
                               error=f"An error occurred: {str(e)}",
                               videos=[],
                               comments=[],
                               selected_video=None,
                               selected_video_id=None,
                               sentiment_stats=None,
                               comments_limited=False,
                               use_google_api=session.get('use_google_api', True))

@app.route('/summarize_json', methods=['GET'])
@login_required
def summarize_json():
    try:
        bucket_name = request.args.get('bucket_name')
        source_blob_name = request.args.get('source_blob_name')

        if not bucket_name or not source_blob_name:
            return render_template('json_summary.html',
                                  error="Bucket name and file name are required",
                                  summary=None,
                                  filename=None)

        storage = DataStorage(bucket_name)
        data = storage.load_data(source_blob_name)

        summary = {
            "file_name": source_blob_name,
            "data_type": type(data).__name__,
            "item_count": len(data) if isinstance(data, list) else "Not a list",
            "keys": list(data[0].keys()) if isinstance(data, list) and data else "No keys found or empty list",
            "sample": data[0] if isinstance(data, list) and data else "No sample available"
        }

        return render_template('json_summary.html',
                              error=None,
                              summary=summary,
                              filename=source_blob_name)
    except Exception as e:
        logger.error(f"Error in summarize_json route: {str(e)}")
        return render_template('json_summary.html',
                              error=f"An error occurred: {str(e)}",
                              summary=None,
                              filename=None)

@app.route('/youtube-privacy', methods=['GET'])
@login_required
def youtube_privacy():
    try:
        youtube_stats = YouTubeStats()
        videos = youtube_stats.search_privacy_videos(max_results=20)

        if isinstance(videos, dict) and 'error' in videos:
            return render_template('youtube_privacy.html', error=videos['error'], videos=[])

        total_views = sum(int(video['views']) for video in videos)
        total_likes = sum(int(video['likes']) for video in videos)
        total_comments = sum(int(video['comments']) for video in videos)

        avg_views = format(total_views / len(videos), ',.0f') if videos else 0
        avg_likes = format(total_likes / len(videos), ',.0f') if videos else 0
        avg_comments = format(total_comments / len(videos), ',.0f') if videos else 0

        session['current_videos'] = videos

        return render_template('youtube_privacy.html', 
                             videos=videos, 
                             error=None, 
                             average_views=avg_views, 
                             average_likes=avg_likes, 
                             average_comments=avg_comments)
    except Exception as e:
        logger.error(f"Error in YouTube privacy route: {str(e)}")
        return render_template('youtube_privacy.html', error=f"An error occurred: {str(e)}", videos=[])

@app.route('/storage_manager', methods=['GET', 'POST'])
@login_required
def storage_manager():
    try:
        data_storage = DataStorage(session.get('storage_bucket', 'your-bucket-name'))
        bucket_name = session.get('storage_bucket', 'itc-388-youtube-r6')
        data_storage = DataStorage(bucket_name)
        
        if request.method == 'POST':
            if 'upload' in request.form:
                current_videos = session.get('current_videos')
                if current_videos:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    filename = f"{date_str}-privacy-analysis.json"
                    data_storage.save_videos_data(current_videos)
                    flash('Data successfully uploaded to storage!', 'success')
                else:
                    flash('No current video data to upload', 'error')
            
            elif 'download' in request.form:
                blob_name = request.form.get('blob_name')
                if blob_name:
                    data = data_storage.load_data(blob_name)
                    return jsonify(data)
        
        files = data_storage.list_blobs()
        return render_template('storage_manager.html', files=files)

    except Exception as e:
        logger.error(f"Error in storage manager: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'error')
        return render_template('storage_manager.html', files=[])

@app.route('/legacy_search')
@login_required
def legacy_search():
    try:
        youtube_stats = YouTubeStats()
        videos = youtube_stats.search_privacy_videos(max_results=20)

        if isinstance(videos, dict) and 'error' in videos:
            return render_template('legacy_search.html', error=videos['error'], videos=[])

        total_views = sum(int(video['views']) for video in videos)
        total_likes = sum(int(video['likes']) for video in videos)
        total_comments = sum(int(video['comments']) for video in videos)

        avg_views = format(total_views / len(videos), ',.0f') if videos else 0
        avg_likes = format(total_likes / len(videos), ',.0f') if videos else 0
        avg_comments = format(total_comments / len(videos), ',.0f') if videos else 0
        return render_template('legacy_search.html',
                             videos=videos,
                             error=None,
                             average_views=avg_views,
                             average_likes=avg_likes,
                             average_comments=avg_comments)
    except Exception as e:
        logger.error(f"Error in legacy search route: {str(e)}")
        return render_template('legacy_search.html', error=f"An error occurred: {str(e)}", videos=[])

@app.route('/more', methods=['GET'])
@login_required
def more():
    return render_template('more.html')

@app.route('/tag_analysis')
def tag_analysis():
    try:
        youtube_stats = YouTubeStats()
        videos = youtube_stats.search_privacy_videos(max_results=20)
        
        if isinstance(videos, dict) and 'error' in videos:
            return render_template('tag_analysis.html', error=videos['error'])
            
        # Create a tag frequency dictionary
        tag_frequency = {}
        for video in videos:
            tags = video.get('tags', [])
            for tag in tags:
                tag = tag.lower().strip()  # Normalize tags
                tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
                
        # Sort tags by frequency
        sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)
        
        # Get top 20 tags
        top_tags = sorted_tags[:20]
        
        return render_template('tag_analysis.html', 
                             tags=top_tags,
                             total_videos=len(videos),
                             error=None)
    except Exception as e:
        logger.error(f"Error in tag analysis route: {str(e)}")
        return render_template('tag_analysis.html', 
                             error=f"An error occurred: {str(e)}",
                             tags=[])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
