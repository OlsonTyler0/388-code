# src/routes/analysis.py
from flask import Blueprint, render_template
from flask_login import login_required
from ..youtube_stats import YouTubeStats
import logging

logger = logging.getLogger(__name__)
analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/tag_analysis')
@login_required
def tag_analysis():
    try:
        youtube_stats = YouTubeStats()
        videos = youtube_stats.search_privacy_videos(max_results=20)
        
        if isinstance(videos, dict) and 'error' in videos:
            return render_template('tag_analysis.html', error=videos['error'], tags=[], total_videos=0)
            
        # Create a tag frequency dictionary
        tag_frequency = {}
        valid_videos = 0
        
        for video in videos:
            # Check if tags exist in the video data
            if 'tags' in video and video['tags']:
                valid_videos += 1
                for tag in video['tags']:
                    if tag:  # Make sure tag is not empty
                        tag = tag.lower().strip()  # Normalize tags
                        tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
                
        # Sort tags by frequency
        sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)
        
        # Get top 20 tags
        top_tags = sorted_tags[:20]
        
        return render_template('tag_analysis.html', 
                             tags=top_tags,
                             total_videos=valid_videos,
                             error=None)
    except Exception as e:
        logger.error(f"Error in tag analysis route: {str(e)}")
        return render_template('tag_analysis.html', 
                             error=f"An error occurred: {str(e)}",
                             tags=[],
                             total_videos=0)


@analysis_bp.route('/more', methods=['GET'])
@login_required
def more():
    return render_template('more.html')