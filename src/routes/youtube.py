from flask import Blueprint, render_template, session
from flask_login import login_required
from ..youtube_stats import YouTubeStats
import logging
from datetime import datetime  # Add this import

logger = logging.getLogger(__name__)
youtube_bp = Blueprint('youtube', __name__)

@youtube_bp.route('/youtube_privacy')
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
        session['last_search_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return render_template('youtube_privacy.html', 
                             videos=videos, 
                             error=None, 
                             average_views=avg_views, 
                             average_likes=avg_likes, 
                             average_comments=avg_comments)
    except Exception as e:
        logger.error(f"Error in YouTube privacy route: {str(e)}")
        return render_template('youtube_privacy.html', error=f"An error occurred: {str(e)}", videos=[])