from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import requests
import json
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import storage
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for session

class YouTubeStats:
    def __init__(self):
        # You'll need to set this in your environment variables
        self.api_key = os.environ.get('YOUTUBE_API_KEY', 'your-api-key-here')
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    def get_top_popular_videos(self, max_results=20, region_code='US'):
        """
        Get the top popular videos from YouTube
        
        Args:
            max_results: Number of videos to return (max 50)
            region_code: ISO 3166-1 alpha-2 country code
            
        Returns:
            A list of dictionaries with video information
        """
        try:
            # Call the videos.list method to get most popular videos
            videos_response = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                chart='mostPopular',
                regionCode=region_code,
                maxResults=max_results
            ).execute()
            
            videos_data = []
            
            for video in videos_response.get('items', []):
                video_data = {
                    'id': video['id'],
                    'title': video['snippet']['title'],
                    'channel': video['snippet']['channelTitle'],
                    'views': video['statistics'].get('viewCount', '0'),
                    'thumbnail': video['snippet']['thumbnails']['medium']['url'],
                    'url': f"https://www.youtube.com/watch?v={video['id']}"
                }
                videos_data.append(video_data)
                
            return videos_data
            
        except HttpError as e:
            error_message = json.loads(e.content).get('error', {}).get('message', 'Unknown error')
            return {'error': f"YouTube API error: {error_message}"}
        except Exception as e:
            return {'error': f"An unexpected error occurred: {str(e)}"}
    
    def search_privacy_videos(self, max_results=20):
        """
        Search for videos related to data privacy
        
        Args:
            max_results: Number of videos to return
            
        Returns:
            A list of dictionaries with video information
        """
        try:
            # Call the search.list method to search for videos about data privacy
            search_response = self.youtube.search().list(
                part='snippet',
                q='data privacy',
                type='video',
                order='relevance',
                maxResults=max_results
            ).execute()
            
            videos_data = []
            video_ids = []
            
            # Extract video IDs from search results
            for item in search_response.get('items', []):
                video_ids.append(item['id']['videoId'])
            
            if not video_ids:
                return []
            
            # Get detailed information about the videos
            videos_response = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=','.join(video_ids)
            ).execute()
            
            for video in videos_response.get('items', []):
                video_data = {
                    'id': video['id'],
                    'title': video['snippet']['title'],
                    'channel': video['snippet']['channelTitle'],
                    'views': video['statistics'].get('viewCount', '0'),
                    'likes': video['statistics'].get('likeCount', '0'),
                    'comments': video['statistics'].get('commentCount', '0'),
                    'description': video['snippet']['description'],
                    'thumbnail': video['snippet']['thumbnails']['medium']['url'],
                    'url': f"https://www.youtube.com/watch?v={video['id']}"
                }
                videos_data.append(video_data)
                
            return videos_data
            
        except HttpError as e:
            error_message = json.loads(e.content).get('error', {}).get('message', 'Unknown error')
            return {'error': f"YouTube API error: {error_message}"}
        except Exception as e:
            return {'error': f"An unexpected error occurred: {str(e)}"}
    
    def get_video_comments(self, video_id, max_results=50):
        """
        Get a limited number of comments for a specific video
        
        Args:
            video_id: YouTube video ID
            max_results: Maximum number of comments to retrieve (default: 50)
                
        Returns:
            A list of comment dictionaries
        """
        try:
            # Call the commentThreads.list method to retrieve comments
            comments_response = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                textFormat='plainText',
                maxResults=max_results  # Limit to 50 comments
            ).execute()
            
            comments_data = []
            
            for item in comments_response.get('items', []):
                comment = item['snippet']['topLevelComment']['snippet']
                comment_data = {
                    'id': item['id'],
                    'text': comment['textDisplay'],
                    'author': comment['authorDisplayName'],
                    'likes': comment['likeCount'],
                    'published_at': comment['publishedAt']
                }
                comments_data.append(comment_data)
                
            return comments_data
            
        except HttpError as e:
            error_message = json.loads(e.content).get('error', {}).get('message', 'Unknown error')
            return {'error': f"YouTube API error: {error_message}"}
        except Exception as e:
            return {'error': f"An unexpected error occurred: {str(e)}"}

class SentimentAnalyzer:
    def __init__(self):
        try:
            # Initialize the Natural Language API client
            from google.cloud import language_v1
            self.client = language_v1.LanguageServiceClient()
            self.language_v1 = language_v1
        except Exception as e:
            logger.error(f"Error initializing Google Cloud Natural Language API: {str(e)}")
            raise e
    
    def analyze_text(self, text):
        """
        Analyze the sentiment of a text
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary with sentiment score and magnitude
        """
        try:
            document = self.language_v1.Document(
                content=text,
                type_=self.language_v1.Document.Type.PLAIN_TEXT
            )
            
            # Detect sentiment
            sentiment = self.client.analyze_sentiment(
                request={"document": document}
            ).document_sentiment
            
            score = sentiment.score
            magnitude = sentiment.magnitude
            
            # Determine sentiment category
            if score > 0.25:
                category = "positive"
            elif score < -0.25:
                category = "negative"
            else:
                category = "neutral"
            
            return {
                "score": score,
                "magnitude": magnitude,
                "category": category
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "score": 0,
                "magnitude": 0,
                "category": "neutral",
                "error": str(e)
            }

class LocalSentimentAnalyzer:
    """
    A simple sentiment analyzer that uses TextBlob to analyze text sentiment locally,
    without requiring API calls to Google Cloud Natural Language API.
    
    This provides a cost-effective alternative with reasonable accuracy for many cases.
    """
    def __init__(self):
        """
        Initialize the local sentiment analyzer
        No setup needed for TextBlob as it's installed via pip
        """
        try:
            # Import TextBlob here to ensure it's available
            from textblob import TextBlob
            self.TextBlob = TextBlob
        except ImportError:
            logger.warning("TextBlob not installed. Run 'pip install textblob' to use local sentiment analysis.")
    
    def analyze_text(self, text):
        """
        Analyze the sentiment of a text using TextBlob
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary with sentiment score and category
        """
        try:
            from textblob import TextBlob
            
            # Create a TextBlob object
            blob = TextBlob(text)
            
            # Get polarity score (-1 to 1)
            score = blob.sentiment.polarity
            
            # Determine sentiment category
            if score > 0.2:
                category = "positive"
            elif score < -0.2:
                category = "negative"
            else:
                category = "neutral"
            
            # TextBlob also provides subjectivity (0 to 1)
            # 0 is objective, 1 is subjective
            magnitude = blob.sentiment.subjectivity
            
            return {
                "score": score,
                "magnitude": magnitude,
                "category": category
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment locally: {str(e)}")
            return {
                "score": 0,
                "magnitude": 0,
                "category": "neutral",
                "error": str(e)
            }

class DataStorage:
    def __init__(self, bucket_name):
        """
        Initialize the data storage with a Google Cloud Storage bucket
        
        Args:
            bucket_name: Name of the GCS bucket
        """
        self.bucket_name = bucket_name
        
        try:
            self.storage_client = storage.Client()
            
            # Try to get the bucket, create it if it doesn't exist
            try:
                self.bucket = self.storage_client.get_bucket(bucket_name)
            except Exception:
                self.bucket = self.storage_client.create_bucket(bucket_name)
        except Exception as e:
            logger.error(f"Error initializing Google Cloud Storage: {str(e)}")
            # Create a mock implementation for local development
            self.storage_client = None
            self.bucket = None
    
    def save_videos_data(self, videos_data):
        """
        Save videos data to GCS
        
        Args:
            videos_data: List of video dictionaries
            
        Returns:
            The blob name where the data was saved
        """
        if not self.bucket:
            logger.warning("Storage not initialized, data not saved")
            return None
        
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"privacy_videos_{timestamp}.json"
        
        # Create a new blob
        blob = self.bucket.blob(blob_name)
        
        # Convert data to JSON and upload
        blob.upload_from_string(
            json.dumps(videos_data, indent=2),
            content_type="application/json"
        )
        
        return blob_name
    
    def save_comments_data(self, video_id, comments_data):
        """
        Save comments data to GCS
        
        Args:
            video_id: YouTube video ID
            comments_data: List of comment dictionaries
            
        Returns:
            The blob name where the data was saved
        """
        if not self.bucket:
            logger.warning("Storage not initialized, data not saved")
            return None
        
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"comments_{video_id}_{timestamp}.json"
        
        # Create a new blob
        blob = self.bucket.blob(blob_name)
        
        # Convert data to JSON and upload
        blob.upload_from_string(
            json.dumps(comments_data, indent=2),
            content_type="application/json"
        )
        
        return blob_name
    
    def load_data(self, blob_name):
        """
        Load data from GCS
        
        Args:
            blob_name: Name of the blob to load
            
        Returns:
            The loaded data
        """
        if not self.bucket:
            logger.warning("Storage not initialized, cannot load data")
            return None
        
        try:
            # Get the blob
            blob = self.bucket.blob(blob_name)
            
            # Download the blob as a string
            data_string = blob.download_as_string()
            
            # Parse the JSON data
            return json.loads(data_string)
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return None

def download_json_and_summarize(bucket_name, source_blob_name):
    """
    Download a JSON file from Google Cloud Storage and summarize its contents
    
    Args:
        bucket_name: Name of the Google Cloud Storage bucket
        source_blob_name: Name of the blob (file) in the bucket
        
    Returns:
        A dictionary with summary information
    """
    try:
        # Initialize storage client
        storage_client = storage.Client()
        
        # Get bucket and blob
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        
        # Download the blob as a string
        json_data_string = blob.download_as_string()
        
        # Parse the JSON data
        json_data = json.loads(json_data_string)
        
        # Create a simple summary of the data
        summary = {
            'file_name': source_blob_name,
            'data_type': type(json_data).__name__,
            'total_items': len(json_data) if isinstance(json_data, list) else 'N/A',
            'keys': list(json_data.keys()) if isinstance(json_data, dict) else 'N/A',
            'sample': json_data[:3] if isinstance(json_data, list) and len(json_data) > 0 else 'N/A'
        }
        
        return summary
        
    except Exception as e:
        return {'error': f"Failed to download and summarize JSON: {str(e)}"}

# HTML template for the homepage with Bootstrap styling
homepage_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Analysis Dashboard</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container py-4">
        <header class="pb-3 mb-4 border-bottom">
            <h1 class="display-5 fw-bold text-center">Data Analysis Dashboard</h1>
        </header>
        
        <div class="row justify-content-center mb-4">
            <div class="col-md-8 text-center">
                <div class="d-grid gap-3 d-sm-flex justify-content-sm-center">
                    <a href="/sentiment" class="btn btn-primary btn-lg px-4 gap-3">Sentiment Analysis</a>
                    <a href="/youtube-privacy" class="btn btn-primary btn-lg px-4">YouTube Stats of Online Privacy</a>
                    <a href="/top20" class="btn btn-primary btn-lg px-4">Top 20 Popular</a>
                    <a href="/config" class="btn btn-warning btn-lg px-4">Settings</a>
                    <a href="/more" class="btn btn-secondary btn-lg px-4">More</a>
                </div>
            </div>
        </div>
        
        <footer class="pt-3 mt-4 text-muted border-top text-center">
            &copy; 2025 Data Analysis Dashboard
        </footer>
    </div>
    
    <!-- Bootstrap JS Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

# Top 20 popular videos template
top20_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Top 20 Popular YouTube Videos</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container py-4">
        <header class="pb-3 mb-4 border-bottom">
            <div class="d-flex justify-content-between align-items-center">
                <a href="/" class="btn btn-outline-primary">Back to Home</a>
                <h1 class="display-5 fw-bold text-center">Top 20 Popular YouTube Videos</h1>
                <div style="width: 100px;"></div> <!-- Empty div for centering -->
            </div>
        </header>
        
        {% if error %}
        <div class="alert alert-danger" role="alert">
            {{ error }}
        </div>
        {% else %}
        <div class="row row-cols-1 row-cols-md-2 g-4">
            {% for video in videos %}
            <div class="col">
                <div class="card h-100">
                    <img src="{{ video.thumbnail }}" class="card-img-top" alt="{{ video.title }}">
                    <div class="card-body">
                        <h5 class="card-title">{{ video.title }}</h5>
                        <p class="card-text">Channel: {{ video.channel }}</p>
                        <p class="card-text"><small class="text-muted">{{ video.views }} views</small></p>
                        <a href="{{ video.url }}" target="_blank" class="btn btn-primary">Watch Video</a>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <footer class="pt-3 mt-4 text-muted border-top text-center">
            &copy; 2025 Data Analysis Dashboard
        </footer>
    </div>
    
    <!-- Bootstrap JS Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

# YouTube privacy videos template
youtube_privacy_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Videos on Data Privacy</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container py-4">
        <header class="pb-3 mb-4 border-bottom">
            <div class="d-flex justify-content-between align-items-center">
                <a href="/" class="btn btn-outline-primary">Back to Home</a>
                <h1 class="display-5 fw-bold text-center">Data Privacy on YouTube</h1>
                <div style="width: 100px;"></div> <!-- Empty div for centering -->
            </div>
        </header>
        
        {% if error %}
        <div class="alert alert-danger" role="alert">
            {{ error }}
        </div>
        {% else %}
        <div class="mb-4">
            <h2>Analysis Overview</h2>
            <div class="card">
                <div class="card-body">
                    <p>Total videos analyzed: {{ videos|length }}</p>
                    <p>Average view count: {{ average_views }}</p>
                    <p>Average like count: {{ average_likes }}</p>
                    <p>Average comment count: {{ average_comments }}</p>
                </div>
            </div>
        </div>
        
        <h2>Video Details</h2>
        <div class="row row-cols-1 row-cols-md-2 g-4">
            {% for video in videos %}
            <div class="col">
                <div class="card h-100">
                    <img src="{{ video.thumbnail }}" class="card-img-top" alt="{{ video.title }}">
                    <div class="card-body">
                        <h5 class="card-title">{{ video.title }}</h5>
                        <p class="card-text">Channel: {{ video.channel }}</p>
                        <div class="d-flex justify-content-between">
                            <span><i class="bi bi-eye"></i> {{ video.views }} views</span>
                            <span><i class="bi bi-hand-thumbs-up"></i> {{ video.likes }}</span>
                            <span><i class="bi bi-chat"></i> {{ video.comments }}</span>
                        </div>
                        <p class="card-text mt-2">
                            <small class="text-muted">{{ video.description|truncate(100) }}</small>
                        </p>
                        <a href="{{ video.url }}" target="_blank" class="btn btn-primary">Watch Video</a>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <footer class="pt-3 mt-4 text-muted border-top text-center">
            &copy; 2025 Data Analysis Dashboard
        </footer>
    </div>
    
    <!-- Bootstrap JS Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
</body>
</html>
'''

# Sentiment analysis template with video selection
sentiment_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Privacy Sentiment Analysis</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .sentiment-positive {
            background-color: rgba(40, 167, 69, 0.2);
        }
        .sentiment-neutral {
            background-color: rgba(108, 117, 125, 0.2);
        }
        .sentiment-negative {
            background-color: rgba(220, 53, 69, 0.2);
        }
        .chart-container {
            height: 300px;
        }
    </style>
</head>
<body>
    <div class="container py-4">
        <header class="pb-3 mb-4 border-bottom">
            <div class="d-flex justify-content-between align-items-center">
                <a href="/" class="btn btn-outline-primary">Back to Home</a>
                <h1 class="display-5 fw-bold text-center">Data Privacy Sentiment Analysis</h1>
                <div style="width: 100px;"></div> <!-- Empty div for centering -->
            </div>
        </header>
        
        {% if error %}
        <div class="alert alert-danger" role="alert">
            {{ error }}
        </div>
        {% endif %}
        
        <div class="row mb-4">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h2>Video Selection</h2>
                    </div>
                    <div class="card-body">
                        <form id="videoSelectForm" action="/sentiment" method="get">
                            <div class="mb-3">
                                <label for="videoSelect" class="form-label">Select a data privacy video:</label>
                                <select class="form-select" id="videoSelect" name="video_id" onchange="this.form.submit()">
                                    <option value="">-- Select a video --</option>
                                    {% for video in videos %}
                                    <option value="{{ video.id }}" {% if video.id == selected_video_id %}selected{% endif %}>
                                        {{ video.title }} ({{ video.channel }})
                                    </option>
                                    {% endfor %}
                                </select>
                            </div>
                        </form>
                        
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> 
                            Using {{ 'Google Cloud Natural Language API' if use_google_api else 'Local TextBlob Analysis' }} for sentiment analysis.
                            <a href="/config" class="alert-link">Change Settings</a>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h2>Sentiment Overview</h2>
                    </div>
                    <div class="card-body">
                        {% if sentiment_stats %}
                        <div class="progress mb-3" style="height: 30px;">
                            <div class="progress-bar bg-success" role="progressbar" style="width: {{ sentiment_stats.positive_percent }}%">
                                {{ sentiment_stats.positive_percent }}%
                            </div>
                            <div class="progress-bar bg-secondary" role="progressbar" style="width: {{ sentiment_stats.neutral_percent }}%">
                                {{ sentiment_stats.neutral_percent }}%
                            </div>
                            <div class="progress-bar bg-danger" role="progressbar" style="width: {{ sentiment_stats.negative_percent }}%">
                                {{ sentiment_stats.negative_percent }}%
                            </div>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span class="text-success">Positive: {{ sentiment_stats.positive_count }}</span>
                            <span class="text-secondary">Neutral: {{ sentiment_stats.neutral_count }}</span>
                            <span class="text-danger">Negative: {{ sentiment_stats.negative_count }}</span>
                        </div>
                        <p class="mt-2">Total comments analyzed: {{ sentiment_stats.total_comments }}</p>
                        {% else %}
                        <p>Select a video to see sentiment analysis.</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        
        {% if selected_video %}
        <div class="row mb-4">
            <div class="col">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h3>Selected Video</h3>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <img src="{{ selected_video.thumbnail }}" class="img-fluid rounded" alt="{{ selected_video.title }}">
                            </div>
                            <div class="col-md-8">
                                <h4>{{ selected_video.title }}</h4>
                                <p>Channel: {{ selected_video.channel }}</p>
                                <div class="d-flex justify-content-between mb-2">
                                    <span><i class="bi bi-eye"></i> {{ selected_video.views }} views</span>
                                    <span><i class="bi bi-hand-thumbs-up"></i> {{ selected_video.likes }} likes</span>
                                    <span><i class="bi bi-chat"></i> {{ selected_video.comments }} comments</span>
                                </div>
                                <p>{{ selected_video.description | truncate(200) }}</p>
                                <a href="{{ selected_video.url }}" target="_blank" class="btn btn-primary">Watch on YouTube</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
        
        {% if comments %}
        <div class="row mb-4">
            <div class="col">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h3>Comment Sentiment Analysis</h3>
                        <select class="form-select" style="width: auto;" id="sentimentFilter" onchange="filterComments()">
                            <option value="all">All Comments</option>
                            <option value="positive">Positive</option>
                            <option value="neutral">Neutral</option>
                            <option value="negative">Negative</option>
                        </select>
                    </div>
                    <div class="card-body">
                        {% if comments_limited %}
                        <div class="alert alert-info mb-3">
                            <i class="bi bi-info-circle"></i> 
                            Showing 50 comments out of {{ selected_video.comments }} total comments to optimize API usage and costs.
                        </div>
                        {% endif %}
                        
                        <div class="list-group">
                            {% for comment in comments %}
                            <div class="list-group-item sentiment-{{ comment.sentiment.category }}" data-sentiment="{{ comment.sentiment.category }}">
                                <div class="d-flex w-100 justify-content-between">
                                    <h5 class="mb-1">{{ comment.author }}</h5>
                                    <small>{{ comment.published_at | format_date }}</small>
                                </div>
                                <p class="mb-1">{{ comment.text }}</p>
                                <small>
                                    Sentiment: 
                                    <span class="badge {% if comment.sentiment.category == 'positive' %}bg-success{% elif comment.sentiment.category == 'negative' %}bg-danger{% else %}bg-secondary{% endif %}">
                                        {{ comment.sentiment.category | capitalize }} ({{ "%.2f"|format(comment.sentiment.score) }})
                                    </span>
                                    <span class="ms-2">Likes: {{ comment.likes }}</span>
                                </small>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
        
        <footer class="pt-3 mt-4 text-muted border-top text-center">
            &copy; 2025 Data Analysis Dashboard
        </footer>
    </div>
    <!-- Bootstrap JS Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <script>
        function filterComments() {
            const filter = document.getElementById('sentimentFilter').value;
            const comments = document.querySelectorAll('.list-group-item');
            
            comments.forEach(comment => {
                if (filter === 'all' || comment.dataset.sentiment === filter) {
                    comment.style.display = 'block';
                } else {
                    comment.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
'''

# Configuration page template
config_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Application Configuration</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container py-4">
        <header class="pb-3 mb-4 border-bottom">
            <div class="d-flex justify-content-between align-items-center">
                <a href="/" class="btn btn-outline-primary">Back to Home</a>
                <h1 class="display-5 fw-bold text-center">Application Settings</h1>
                <div style="width: 100px;"></div> <!-- Empty div for centering -->
            </div>
        </header>
        
        <div class="row mb-4">
            <div class="col-md-8 mx-auto">
                <div class="card">
                    <div class="card-header">
                        <h2>Sentiment Analysis Settings</h2>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="form-check form-switch mb-3">
                                <input class="form-check-input" type="checkbox" id="use_google_api" name="use_google_api" {% if use_google_api %}checked{% endif %}>
                                <label class="form-check-label" for="use_google_api">
                                    Use Google Cloud Natural Language API
                                </label>
                            </div>
                            
                            <div class="alert alert-info">
                                <h5>Cost Information:</h5>
                                <p>Google Cloud Natural Language API costs approximately $1 per 1,000 comments analyzed.</p>
                                <p>If disabled, the application will use a local TextBlob-based sentiment analyzer which is free but less accurate.</p>
                            </div>
                            
                            <button type="submit" class="btn btn-primary">Save Settings</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        
        <footer class="pt-3 mt-4 text-muted border-top text-center">
            &copy; 2025 Data Analysis Dashboard
        </footer>
    </div>
    
    <!-- Bootstrap JS Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

# Homepage route
@app.route('/', methods=['GET'])
def homepage():
    return render_template_string(homepage_template)

# Configuration route
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
    
    return render_template_string(config_template, use_google_api=use_google_api)

# Sentiment analysis route
@app.route('/sentiment', methods=['GET'])
def sentiment_analysis():
    try:
        # Initialize the YouTube stats client
        youtube_stats = YouTubeStats()
        
        # Get the top privacy videos
        videos = youtube_stats.search_privacy_videos(max_results=20)
        
        if isinstance(videos, dict) and 'error' in videos:
            return render_template_string(
                sentiment_template, 
                error=videos['error'], 
                videos=[], 
                comments=[], 
                selected_video=None,
                selected_video_id=None,
                sentiment_stats=None,
                comments_limited=False,
                use_google_api=session.get('use_google_api', True)
            )
        
        # Get the selected video ID from the query parameters
        selected_video_id = request.args.get('video_id')
        selected_video = None
        comments = []
        sentiment_stats = None
        comments_limited = False
        
        # If a video is selected, get its comments and analyze sentiment
        if selected_video_id:
            # Find the selected video in the list
            for video in videos:
                if video['id'] == selected_video_id:
                    selected_video = video
                    break
            
            if selected_video:
                # Check if total comments exceed our limit
                total_comment_count = int(selected_video.get('comments', '0'))
                if total_comment_count > 50:
                    comments_limited = True
                
                # Get comments for the selected video (limited to 50)
                comments_data = youtube_stats.get_video_comments(selected_video_id, max_results=50)
                
                if isinstance(comments_data, dict) and 'error' in comments_data:
                    return render_template_string(
                        sentiment_template, 
                        error=comments_data['error'], 
                        videos=videos, 
                        comments=[], 
                        selected_video=selected_video,
                        selected_video_id=selected_video_id,
                        sentiment_stats=None,
                        comments_limited=comments_limited,
                        use_google_api=session.get('use_google_api', True)
                    )
                
                # Get sentiment analyzer based on configuration
                use_google_api = session.get('use_google_api', True)
                
                try:
                    if use_google_api:
                        sentiment_analyzer = SentimentAnalyzer()  # Google Cloud
                    else:
                        sentiment_analyzer = LocalSentimentAnalyzer()  # Local analysis
                except Exception as e:
                    logger.error(f"Error initializing sentiment analyzer: {str(e)}")
                    # Default to local analyzer if Google API fails
                    sentiment_analyzer = LocalSentimentAnalyzer()
                    use_google_api = False
                    session['use_google_api'] = False
                
                # Analyze sentiment for each comment
                for comment in comments_data:
                    # Skip empty comments
                    if not comment['text']:
                        continue
                    
                    # Analyze sentiment
                    sentiment = sentiment_analyzer.analyze_text(comment['text'])
                    
                    # Add sentiment to comment
                    comment['sentiment'] = sentiment
                
                # Try to save data to Google Cloud Storage
                try:
                    storage = DataStorage('data_privacy_analysis')
                    storage.save_comments_data(selected_video_id, comments_data)
                except Exception as e:
                    logger.error(f"Error saving to Cloud Storage: {str(e)}")
                
                # Calculate sentiment statistics
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
        
        # Define a filter to format dates
        @app.template_filter('format_date')
        def format_date(date_string):
            try:
                date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
                return date.strftime("%b %d, %Y")
            except:
                return date_string
        
        return render_template_string(
            sentiment_template, 
            videos=videos, 
            comments=comments, 
            selected_video=selected_video,
            selected_video_id=selected_video_id,
            sentiment_stats=sentiment_stats,
            error=None,
            comments_limited=comments_limited,
            use_google_api=session.get('use_google_api', True)
        )
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis route: {str(e)}")
        return render_template_string(
            sentiment_template, 
            error=f"An error occurred: {str(e)}", 
            videos=[], 
            comments=[],
            selected_video=None,
            selected_video_id=None,
            sentiment_stats=None,
            comments_limited=False,
            use_google_api=session.get('use_google_api', True)
        )

# YouTube stats route
@app.route('/youtube-privacy', methods=['GET'])
def youtube_privacy():
    try:
        youtube_stats = YouTubeStats()
        videos = youtube_stats.search_privacy_videos(max_results=20)
        
        if isinstance(videos, dict) and 'error' in videos:
            return render_template_string(youtube_privacy_template, error=videos['error'], videos=[])
        
        # Calculate average stats
        total_views = sum(int(video['views']) for video in videos)
        total_likes = sum(int(video['likes']) for video in videos)
        total_comments = sum(int(video['comments']) for video in videos)
        
        avg_views = format(total_views / len(videos), ',.0f') if videos else 0
        avg_likes = format(total_likes / len(videos), ',.0f') if videos else 0
        avg_comments = format(total_comments / len(videos), ',.0f') if videos else 0
        
        return render_template_string(
            youtube_privacy_template, 
            videos=videos, 
            error=None,
            average_views=avg_views,
            average_likes=avg_likes,
            average_comments=avg_comments
        )
    except Exception as e:
        return render_template_string(
            youtube_privacy_template, 
            error=f"An error occurred: {str(e)}", 
            videos=[]
        )

@app.route('/top20', methods=['GET'])  
def top20():
    try:
        youtube_stats = YouTubeStats()
        videos = youtube_stats.get_top_popular_videos()
        
        if isinstance(videos, dict) and 'error' in videos:
            return render_template_string(top20_template, error=videos['error'], videos=[])
        
        return render_template_string(top20_template, videos=videos, error=None)
    except Exception as e:
        return render_template_string(top20_template, error=f"An error occurred: {str(e)}", videos=[])

@app.route('/more', methods=['GET'])
def more():
    more_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>More Options</title>
        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container py-4">
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex justify-content-between align-items-center">
                    <a href="/" class="btn btn-outline-primary">Back to Home</a>
                    <h1 class="display-5 fw-bold text-center">More Options</h1>
                    <div style="width: 100px;"></div> <!-- Empty div for centering -->
                </div>
            </header>
            
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h2>Explore Data from Google Cloud Storage</h2>
                        </div>
                        <div class="card-body">
                            <form action="/servicename" method="get" id="gcsForm">
                                <div class="mb-3">
                                    <label for="bucket_name" class="form-label">Bucket Name</label>
                                    <input type="text" class="form-control" id="bucket_name" name="bucket_name" required>
                                </div>
                                <div class="mb-3">
                                    <label for="source_blob_name" class="form-label">File Name</label>
                                    <input type="text" class="form-control" id="source_blob_name" name="source_blob_name" required>
                                </div>
                                <button type="submit" class="btn btn-primary">Get Data Summary</button>
                            </form>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h2>About This Project</h2>
                        </div>
                        <div class="card-body">
                            <p>This data analysis dashboard provides insights into YouTube data related to data privacy topics.</p>
                            <p>The project aims to track data privacy sentiment and trends on YouTube to help understand public awareness and concerns.</p>
                            <p>Data is collected using the YouTube API and stored in Google Cloud Storage for analysis.</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <footer class="pt-3 mt-4 text-muted border-top text-center">
                &copy; 2025 Data Analysis Dashboard
            </footer>
        </div>
        
        <!-- Bootstrap JS Bundle with Popper -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''
    return render_template_string(more_template)

@app.route('/hereyougo', methods=['GET'])
def hereyougo():
    return "You got me"

@app.route('/servicename', methods=['GET'])
def summarize_json():
    # Get query parameters
    bucket_name = request.args.get('bucket_name')
    source_blob_name = request.args.get('source_blob_name')
    
    if not bucket_name or not source_blob_name:
        return jsonify({"error": "Both 'bucket_name' and 'source_blob_name' are required."}), 400
    
    # Call the function
    summary = download_json_and_summarize(bucket_name, source_blob_name)
    
    # Create a nice HTML display of the summary
    summary_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JSON Summary</title>
        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container py-4">
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex justify-content-between align-items-center">
                    <a href="/more" class="btn btn-outline-primary">Back to More Options</a>
                    <h1 class="display-5 fw-bold text-center">JSON Data Summary</h1>
                    <div style="width: 100px;"></div> <!-- Empty div for centering -->
                </div>
            </header>
            
            {% if error %}
            <div class="alert alert-danger" role="alert">
                {{ error }}
            </div>
            {% else %}
            <div class="card mb-4">
                <div class="card-header">
                    <h2>File Information</h2>
                </div>
                <div class="card-body">
                    <p><strong>File Name:</strong> {{ summary.file_name }}</p>
                    <p><strong>Data Type:</strong> {{ summary.data_type }}</p>
                    {% if summary.total_items != 'N/A' %}
                    <p><strong>Total Items:</strong> {{ summary.total_items }}</p>
                    {% endif %}
                    
                    {% if summary.keys != 'N/A' %}
                    <div class="mb-3">
                        <h4>Available Keys</h4>
                        <ul class="list-group">
                            {% for key in summary.keys %}
                            <li class="list-group-item">{{ key }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                    
                    {% if summary.sample != 'N/A' %}
                    <div>
                        <h4>Sample Data</h4>
                        <pre class="bg-light p-3 rounded"><code>{{ summary.sample | tojson(indent=2) }}</code></pre>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
            <footer class="pt-3 mt-4 text-muted border-top text-center">
                &copy; 2025 Data Analysis Dashboard
            </footer>
        </div>
        
        <!-- Bootstrap JS Bundle with Popper -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''
    
    if "error" in summary:
        return render_template_string(summary_template, error=summary["error"], summary=None)
    else:
        return render_template_string(summary_template, error=None, summary=summary)

if __name__ == '__main__':
    # Use PORT environment variable if available (for Cloud Run)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
    
    <!-- Bootstrap JS Bundle with Popper -->