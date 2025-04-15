# ╔═══════════════════════════════════════════════════════════╗
#   youtube_stats.py
#       This file contains the code for retrieving data from
#       The youtube api for later use throughout the website
# ╚═══════════════════════════════════════════════════════════╝

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
import logging

logger = logging.getLogger(__name__)

class YouTubeStats:
    def __init__(self):
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
            logger.error(f"YouTube API error: {error_message}")
            return {'error': f"YouTube API error: {error_message}"}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
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
            search_response = self.youtube.search().list(
                part='snippet',
                q='data privacy',
                type='video',
                order='relevance',
                maxResults=max_results
            ).execute()
            
            videos_data = []
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            if not video_ids:
                return []
            
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
            logger.error(f"YouTube API error: {error_message}")
            return {'error': f"YouTube API error: {error_message}"}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
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
            comments_response = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                textFormat='plainText',
                maxResults=max_results
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
            logger.error(f"YouTube API error: {error_message}")
            return {'error': f"YouTube API error: {error_message}"}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            return {'error': f"An unexpected error occurred: {str(e)}"}