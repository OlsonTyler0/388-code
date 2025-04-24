# ╔═══════════════════════════════════════════════════════════╗
#   data_storage.py
#       Handles the data storage for the website
# ╚═══════════════════════════════════════════════════════════╝

from google.cloud import storage
import json
from datetime import datetime
import logging
from flask import session

logger = logging.getLogger(__name__)

class DataStorage:
    def __init__(self, bucket_name=None):
        """
        Initialize the Storage client and set bucket name
        
        Args:
            bucket_name: Name of the GCS bucket, defaults to session bucket if available
        """
        try:
            # Allow bucket name to be overridden by session if available
            self.bucket_name = bucket_name or session.get('storage_bucket', 'itc-388-youtube-r6')
            
            # Initialize Google Cloud Storage client without requiring explicit credentials file
            self.storage_client = storage.Client()
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            logger.info(f"Initialized DataStorage with bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error initializing DataStorage: {str(e)}")
            raise RuntimeError(f"Failed to initialize storage: {str(e)}") from e
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            # Try to get the bucket
            self.bucket = self.storage_client.get_bucket(self.bucket_name)
            logger.debug(f"Using existing bucket: {self.bucket_name}")
        except Exception as e:
            # If bucket does not exist, create it
            logger.info(f"Bucket {self.bucket_name} does not exist. Creating...")
            try:
                self.bucket = self.storage_client.create_bucket(self.bucket_name)
                logger.info(f"Bucket {self.bucket.name} created successfully.")
            except Exception as create_error:
                logger.error(f"Failed to create bucket {self.bucket_name}: {str(create_error)}")
                raise RuntimeError(f"Failed to create bucket: {str(create_error)}") from create_error
    
    def save_videos_data(self, videos_data, blob_name=None):
        """
        Save videos data to Cloud Storage
        
        Args:
            videos_data: List of video dictionaries to save
            blob_name: Optional custom name for the blob
        
        Returns:
            Blob name of the saved data
        """
        if not videos_data:
            logger.warning("Attempting to save empty video data")
            return None
            
        try:
            # Generate a default blob name if not provided
            if blob_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                blob_name = f"videos_data_{timestamp}.json"
            
            # Reference to the blob
            blob = self.bucket.blob(blob_name)
            
            # Convert data to JSON with proper formatting
            # Add better error handling for non-serializable objects
            try:
                data_json = json.dumps(videos_data, indent=2)
            except TypeError as e:
                logger.error(f"JSON serialization error: {str(e)}")
                # Try a more basic approach for serialization
                data_json = json.dumps(self._sanitize_for_json(videos_data), indent=2)
            
            # Upload the JSON string to the bucket
            blob.upload_from_string(
                data_json,
                content_type="application/json"
            )
            
            # Set metadata on the blob
            blob.metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'item_count': str(len(videos_data)) if isinstance(videos_data, list) else 'N/A',
                'content_type': 'youtube_videos'
            }
            blob.patch()
            
            logger.info(f"Successfully saved {len(videos_data) if isinstance(videos_data, list) else 'unknown'} videos to {blob_name}")
            return blob_name
        except Exception as e:
            logger.error(f"Error saving videos data: {str(e)}")
            raise RuntimeError(f"Failed to save data: {str(e)}") from e

    def _sanitize_for_json(self, data):
        """
        Sanitize data to ensure it's JSON serializable
        
        Args:
            data: The data to sanitize
            
        Returns:
            JSON serializable version of the data
        """
        if isinstance(data, dict):
            return {k: self._sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_json(item) for item in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        else:
            # Convert non-serializable objects to strings
            return str(data)

    def save_comments_data(self, video_id, comments_data):
        """
        Save comments data to Cloud Storage
        
        Args:
            video_id: YouTube video ID
            comments_data: List of comment dictionaries to save
        
        Returns:
            Blob name of the saved data
        """
        if not video_id or not comments_data:
            logger.warning("Missing video_id or comments_data")
            return None
            
        try:
            # Generate blob name with video ID and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            blob_name = f"comments_{video_id}_{timestamp}.json"
            
            # Reference to the blob
            blob = self.bucket.blob(blob_name)
            
            # Convert data to JSON with proper formatting
            try:
                data_json = json.dumps(comments_data, indent=2)
            except TypeError as e:
                logger.error(f"JSON serialization error: {str(e)}")
                # Try a more basic approach for serialization
                data_json = json.dumps(self._sanitize_for_json(comments_data), indent=2)
            
            # Upload the JSON string to the bucket
            blob.upload_from_string(
                data_json, 
                content_type="application/json"
            )
            
            # Set metadata on the blob
            blob.metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'video_id': video_id,
                'comment_count': str(len(comments_data)),
                'content_type': 'youtube_comments'
            }
            blob.patch()
            
            logger.info(f"Successfully saved {len(comments_data)} comments for video {video_id} to {blob_name}")
            return blob_name
        except Exception as e:
            logger.error(f"Error saving comments data: {str(e)}")
            raise RuntimeError(f"Failed to save comments: {str(e)}") from e

    def load_data(self, blob_name):
        """
        Load data from Cloud Storage
        
        Args:
            blob_name: Name of the blob to load
            
        Returns:
            Dictionary containing the loaded data
        """
        if not blob_name:
            logger.warning("No blob name provided")
            return None
            
        try:
            # Reference to the blob
            blob = self.bucket.blob(blob_name)
            
            # Check if blob exists
            if not blob.exists():
                logger.warning(f"Blob {blob_name} does not exist")
                raise FileNotFoundError(f"File {blob_name} not found in bucket {self.bucket_name}")
            
            # Download and parse the JSON data
            data_json = blob.download_as_string()
            return json.loads(data_json)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {blob_name}: {str(e)}")
            raise ValueError(f"Invalid JSON in file {blob_name}") from e
        except Exception as e:
            logger.error(f"Error loading data from {blob_name}: {str(e)}")
            raise RuntimeError(f"Failed to load data: {str(e)}") from e
            
    def list_blobs(self, prefix=None, max_results=None):
        """
        List all blobs in the bucket
        
        Args:
            prefix: Optional prefix to filter blobs
            max_results: Optional maximum number of results to return
            
        Returns:
            List of blob names
        """
        try:
            # List blobs with optional filters
            blobs = self.bucket.list_blobs(prefix=prefix, max_results=max_results)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Error listing blobs: {str(e)}")
            raise RuntimeError(f"Failed to list files: {str(e)}") from e
    
    def get_blob_metadata(self, blob_name):
        """
        Get metadata for a specific blob
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            Dictionary of metadata
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.reload()  # Ensure we have the latest metadata
            
            # Combine standard and custom metadata
            metadata = {
                'name': blob.name,
                'size': blob.size,
                'updated': blob.updated.isoformat() if blob.updated else None,
                'content_type': blob.content_type,
                'custom_metadata': blob.metadata or {}
            }
            
            return metadata
        except Exception as e:
            logger.error(f"Error getting metadata for {blob_name}: {str(e)}")
            raise RuntimeError(f"Failed to get metadata: {str(e)}") from e
    
    def delete_blob(self, blob_name):
        """
        Delete a blob from the bucket
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info(f"Successfully deleted {blob_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {blob_name}: {str(e)}")
            raise RuntimeError(f"Failed to delete file: {str(e)}") from e# Enhanced version of data_storage.py

from google.cloud import storage
import json
from datetime import datetime
import logging
from flask import session
import os

logger = logging.getLogger(__name__)

class DataStorage:
    def __init__(self, bucket_name=None):
        """
        Initialize the Storage client and set bucket name
        
        Args:
            bucket_name: Name of the GCS bucket, defaults to session bucket if available
        """
        try:
            # Allow bucket name to be overridden by session if available
            self.bucket_name = bucket_name or session.get('storage_bucket', 'itc-388-youtube-r6')
            
            # Verify Google Cloud credentials are available
            if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                logger.warning("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
                
            # Initialize Google Cloud Storage client
            self.storage_client = storage.Client()
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            logger.info(f"Initialized DataStorage with bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error initializing DataStorage: {str(e)}")
            raise RuntimeError(f"Failed to initialize storage: {str(e)}") from e
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            # Try to get the bucket
            self.bucket = self.storage_client.get_bucket(self.bucket_name)
            logger.debug(f"Using existing bucket: {self.bucket_name}")
        except Exception as e:
            # If bucket does not exist, create it
            logger.info(f"Bucket {self.bucket_name} does not exist. Creating...")
            try:
                # Check if we have permissions to create a bucket
                self.bucket = self.storage_client.create_bucket(self.bucket_name)
                logger.info(f"Bucket {self.bucket.name} created successfully.")
            except Exception as create_error:
                logger.error(f"Failed to create bucket {self.bucket_name}: {str(create_error)}")
                raise RuntimeError(f"Failed to create bucket: {str(create_error)}") from create_error
    
    def verify_connection(self):
        """
        Verify connection to Google Cloud Storage
        
        Returns:
            Boolean indicating if connection is successful
        """
        try:
            # Simple operation to check connection
            _ = list(self.storage_client.list_buckets(max_results=1))
            return True
        except Exception as e:
            logger.error(f"Connection verification failed: {str(e)}")
            return False
    
    def save_videos_data(self, videos_data, blob_name=None):
        """
        Save videos data to Cloud Storage
        
        Args:
            videos_data: List of video dictionaries to save
            blob_name: Optional custom name for the blob
        
        Returns:
            Blob name of the saved data or None if failed
        """
        if not videos_data:
            logger.warning("Attempting to save empty video data")
            return None
            
        try:
            # Verify we have data in proper format
            if not isinstance(videos_data, list) and not isinstance(videos_data, dict):
                logger.error(f"Invalid data type: {type(videos_data)}")
                return None
            
            # Generate a default blob name if not provided
            if blob_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                blob_name = f"videos_data_{timestamp}.json"
            
            # Reference to the blob
            blob = self.bucket.blob(blob_name)
            
            # Convert data to JSON with proper formatting
            # Add better error handling for non-serializable objects
            try:
                data_json = json.dumps(videos_data, indent=2, default=str)
            except TypeError as e:
                logger.error(f"JSON serialization error: {str(e)}")
                # Try a more basic approach for serialization
                data_json = json.dumps(self._sanitize_for_json(videos_data), indent=2)
            
            # Upload the JSON string to the bucket
            blob.upload_from_string(
                data_json,
                content_type="application/json"
            )
            
            # Set metadata on the blob
            blob.metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'item_count': str(len(videos_data)) if isinstance(videos_data, list) else 'N/A',
                'content_type': 'youtube_videos'
            }
            blob.patch()
            
            # Verify upload was successful by checking blob exists
            if blob.exists():
                logger.info(f"Successfully saved {len(videos_data) if isinstance(videos_data, list) else 'unknown'} videos to {blob_name}")
                return blob_name
            else:
                logger.error(f"Blob {blob_name} was not found after upload")
                return None
                
        except Exception as e:
            logger.error(f"Error saving videos data: {str(e)}")
            raise RuntimeError(f"Failed to save data: {str(e)}") from e

    def _sanitize_for_json(self, data):
        """
        Sanitize data to ensure it's JSON serializable
        
        Args:
            data: The data to sanitize
            
        Returns:
            JSON serializable version of the data
        """
        if isinstance(data, dict):
            return {k: self._sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_json(item) for item in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        else:
            # Convert non-serializable objects to strings
            return str(data)

    def save_comments_data(self, video_id, comments_data):
        """
        Save comments data to Cloud Storage
        
        Args:
            video_id: YouTube video ID
            comments_data: List of comment dictionaries to save
        
        Returns:
            Blob name of the saved data
        """
        if not video_id or not comments_data:
            logger.warning("Missing video_id or comments_data")
            return None
            
        try:
            # Generate blob name with video ID and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            blob_name = f"comments_{video_id}_{timestamp}.json"
            
            # Reference to the blob
            blob = self.bucket.blob(blob_name)
            
            # Convert data to JSON with proper formatting
            try:
                data_json = json.dumps(comments_data, indent=2, default=str)
            except TypeError as e:
                logger.error(f"JSON serialization error: {str(e)}")
                # Try a more basic approach for serialization
                data_json = json.dumps(self._sanitize_for_json(comments_data), indent=2)
            
            # Upload the JSON string to the bucket
            blob.upload_from_string(
                data_json, 
                content_type="application/json"
            )
            
            # Set metadata on the blob
            blob.metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'video_id': video_id,
                'comment_count': str(len(comments_data)),
                'content_type': 'youtube_comments'
            }
            blob.patch()
            
            # Verify upload was successful
            if blob.exists():
                logger.info(f"Successfully saved {len(comments_data)} comments for video {video_id} to {blob_name}")
                return blob_name
            else:
                logger.error(f"Blob {blob_name} was not found after upload")
                return None
                
        except Exception as e:
            logger.error(f"Error saving comments data: {str(e)}")
            raise RuntimeError(f"Failed to save comments: {str(e)}") from e

    def load_data(self, blob_name):
        """
        Load data from Cloud Storage
        
        Args:
            blob_name: Name of the blob to load
            
        Returns:
            Dictionary containing the loaded data
        """
        if not blob_name:
            logger.warning("No blob name provided")
            return None
            
        try:
            # Reference to the blob
            blob = self.bucket.blob(blob_name)
            
            # Check if blob exists
            if not blob.exists():
                logger.warning(f"Blob {blob_name} does not exist")
                raise FileNotFoundError(f"File {blob_name} not found in bucket {self.bucket_name}")
            
            # Download and parse the JSON data
            data_json = blob.download_as_string()
            return json.loads(data_json)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {blob_name}: {str(e)}")
            raise ValueError(f"Invalid JSON in file {blob_name}") from e
        except Exception as e:
            logger.error(f"Error loading data from {blob_name}: {str(e)}")
            raise RuntimeError(f"Failed to load data: {str(e)}") from e
            
    def list_blobs(self, prefix=None, max_results=None):
        """
        List all blobs in the bucket
        
        Args:
            prefix: Optional prefix to filter blobs
            max_results: Optional maximum number of results to return
            
        Returns:
            List of blob names
        """
        try:
            # List blobs with optional filters
            blobs = self.bucket.list_blobs(prefix=prefix, max_results=max_results)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Error listing blobs: {str(e)}")
            raise RuntimeError(f"Failed to list files: {str(e)}") from e
    
    def get_blob_metadata(self, blob_name):
        """
        Get metadata for a specific blob
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            Dictionary of metadata
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.reload()  # Ensure we have the latest metadata
            
            # Combine standard and custom metadata
            metadata = {
                'name': blob.name,
                'size': blob.size,
                'updated': blob.updated.isoformat() if blob.updated else None,
                'content_type': blob.content_type,
                'custom_metadata': blob.metadata or {}
            }
            
            return metadata
        except Exception as e:
            logger.error(f"Error getting metadata for {blob_name}: {str(e)}")
            raise RuntimeError(f"Failed to get metadata: {str(e)}") from e
    
    def delete_blob(self, blob_name):
        """
        Delete a blob from the bucket
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info(f"Successfully deleted {blob_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {blob_name}: {str(e)}")
            raise RuntimeError(f"Failed to delete file: {str(e)}") from e