from flask import Flask, request, render_template, redirect, url_for, session
import logging
import os
from src.youtube_stats import YouTubeStats
from src.sentiment_analyzer import SentimentAnalyzer, LocalSentimentAnalyzer
from src.data_storage import DataStorage
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key_here')  # Required for session

@app.route('/', methods=['GET'])
def homepage():
    # Render the homepage template
    return render_template('homepage.html')

@app.route('/config', methods=['GET', 'POST'])
def config():
    """
    Configuration page for the application
    Allow users to toggle between Google Cloud API and local sentiment analysis
    """
    if request.method == 'POST':
        use_google_api = 'use_google_api' in request.form
        # Store in session
        session['use_google_api'] = use_google_api
        return redirect(url_for('homepage'))
    
    # Get current setting from session or default to True
    use_google_api = session.get('use_google_api', True)
    
    return render_template('config.html', use_google_api=use_google_api)

@app.route('/sentiment', methods=['GET'])
def sentiment_analysis():
    try:
        # Initialize the YouTube stats client
        youtube_stats = YouTubeStats()
        # Get the top privacy videos
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
        
        @app.template_filter('format_date')
        def format_date(date_string):
            try:
                date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
                return date.strftime("%b %d, %Y")
            except Exception as e:
                return date_string
        
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

@app.route('/youtube-privacy', methods=['GET'])
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
        
        return render_template('youtube_privacy.html', videos=videos, error=None, average_views=avg_views, average_likes=avg_likes, average_comments=avg_comments)
    except Exception as e:
        logger.error(f"Error in YouTube privacy route: {str(e)}")
        return render_template('youtube_privacy.html', error=f"An error occurred: {str(e)}", videos=[])

@app.route('/top20', methods=['GET'])
def top20():
    try:
        youtube_stats = YouTubeStats()
        videos = youtube_stats.get_top_popular_videos()
        
        if isinstance(videos, dict) and 'error' in videos:
            return render_template('top20.html', error=videos['error'], videos=[])
        
        return render_template('top20.html', videos=videos, error=None)
    except Exception as e:
        logger.error(f"Error in Top 20 route: {str(e)}")
        return render_template('top20.html', error=f"An error occurred: {str(e)}", videos=[])

@app.route('/more', methods=['GET'])
def more():
    return render_template('more.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)