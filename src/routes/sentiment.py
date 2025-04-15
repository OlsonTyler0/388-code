from flask import Blueprint, render_template, request, session
from flask_login import login_required
from ..youtube_stats import YouTubeStats
from ..sentiment_analyzer import SentimentAnalyzer, LocalSentimentAnalyzer
from ..data_storage import DataStorage
import logging

logger = logging.getLogger(__name__)
sentiment_bp = Blueprint('sentiment', __name__)

@sentiment_bp.route('/sentiment', methods=['GET'])
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
