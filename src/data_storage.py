from google.cloud import storage
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataStorage:
    def __init__(self, bucket_name):
        """
        Initialize the Storage client and set bucket name
        
        Args:
            bucket_name: Name of the GCS bucket
        """
        try:
            self.storage_client = storage.Client()
            self.bucket_name = bucket_name
            self._ensure_bucket_exists()
        except Exception as e:
            logger.error(f"Error initializing DataStorage: {str(e)}")
            raise e
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            self.storage_client.get_bucket(self.bucket_name)
        except Exception:
            logger.info(f"Bucket {self.bucket_name} does not exist. Creating...")
            bucket = self.storage_client.create_bucket(self.bucket_name)
            logger.info(f"Bucket {bucket.name} created.")
    
    def save_videos_data(self, videos_data):
        """
        Save videos data to Cloud Storage
        
        Args:
            videos_data: List of video dictionaries to save
        
        Returns:
            Blob name of the saved data
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            blob_name = f"videos_data_{timestamp}.json"
            blob = bucket.blob(blob_name)
            
            data_json = json.dumps(videos_data, indent=2)
            
            blob.upload_from_string(data_json, content_type="application/json")
            
            logger.info(f"Saved videos data to {blob_name}")
            return blob_name
        except Exception as e:
            logger.error(f"Error saving videos data: {str(e)}")
            raise e

    def save_comments_data(self, video_id, comments_data):
        """
        Save comments data to Cloud Storage
        
        Args:
            video_id: YouTube video ID
            comments_data: List of comment dictionaries to save
        
        Returns:
            Blob name of the saved data
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            blob_name = f"comments_{video_id}_{timestamp}.json"
            blob = bucket.blob(blob_name)
            
            data_json = json.dumps(comments_data, indent=2)
            
            blob.upload_from_string(data_json, content_type="application/json")
            
            logger.info(f"Saved comments data to {blob_name}")
            return blob_name
        except Exception as e:
            logger.error(f"Error saving comments data: {str(e)}")
            raise e

    def load_data(self, blob_name):
        """
        Load data from Cloud Storage
        
        Args:
            blob_name: Name of the blob to load
        
        Returns:
            Loaded data as Python object
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            
            content = blob.download_as_text()
            
            data = json.loads(content)
            
            logger.info(f"Loaded data from {blob_name}")
            return data
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            raise e
            
    def list_blobs(self, prefix=None):
        """
        List all blobs in the bucket
        
        Args:
            prefix: Optional prefix to filter blobs
            
        Returns:
            List of blob names
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Error listing blobs: {str(e)}")
            raise e