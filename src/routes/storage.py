# Enhanced version of storage.py route for uploading data

from flask import Blueprint, render_template, request, session, flash, jsonify, redirect, url_for, send_file
from flask_login import login_required
from ..data_storage import DataStorage
from ..youtube_stats import YouTubeStats
from datetime import datetime
import logging
import json
import io
import os

logger = logging.getLogger(__name__)
storage_bp = Blueprint('storage', __name__)

@storage_bp.route('/storage_manager', methods=['GET', 'POST'])
@login_required
def storage_manager():
    try:
        # Get bucket name from session or use default
        bucket_name = session.get('storage_bucket', 'itc-388-youtube-r6')
        latest_upload = None
        upload_error = None
        files = []

        # Check if Google Cloud credentials are available
        if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            logger.warning("Google Cloud credentials not found in environment variables")
            upload_error = "Google Cloud credentials are not configured properly. Please check configuration."
        
        try:
            # Initialize DataStorage - wrap in try/except to handle connection issues
            data_storage = DataStorage(bucket_name)
            files = data_storage.list_blobs()
        except Exception as storage_error:
            logger.error(f"Error connecting to Google Cloud Storage: {str(storage_error)}")
            upload_error = f"Could not connect to Google Cloud Storage: {str(storage_error)}"
        
        if request.method == 'POST':
            if 'upload' in request.form and not upload_error:
                try:
                    # Get fresh data from YouTube API
                    youtube_stats = YouTubeStats()
                    current_videos = youtube_stats.search_privacy_videos(max_results=20)
                    
                    if not current_videos:
                        flash('No data retrieved from YouTube API', 'warning')
                        return render_template('storage_manager.html', 
                                              files=files, 
                                              latest_upload=None,
                                              upload_error=upload_error)
                                              
                    if isinstance(current_videos, dict) and 'error' in current_videos:
                        flash(f"YouTube API error: {current_videos['error']}", 'danger')
                        return render_template('storage_manager.html', 
                                              files=files, 
                                              latest_upload=None,
                                              upload_error=upload_error)
                    
                    # Create a timestamp and blob name
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    blob_name = f"privacy_videos_{timestamp}.json"
                    
                    # Save to Google Cloud Storage
                    saved_filename = data_storage.save_videos_data(current_videos, blob_name)
                    
                    if saved_filename:
                        flash(f'Data successfully uploaded as {saved_filename}!', 'success')
                        latest_upload = saved_filename
                        
                        # Refresh the file list after upload
                        files = data_storage.list_blobs()
                    else:
                        flash('Upload failed. No filename was returned.', 'danger')
                
                except Exception as upload_error:
                    logger.error(f"Error during upload process: {str(upload_error)}")
                    flash(f"Upload failed: {str(upload_error)}", 'danger')
            
            elif 'download' in request.form:
                blob_name = request.form.get('blob_name')
                if blob_name:
                    try:
                        data = data_storage.load_data(blob_name)
                        # Create a downloadable file
                        json_data = json.dumps(data, indent=2)
                        buffer = io.BytesIO(json_data.encode('utf-8'))
                        buffer.seek(0)
                        return send_file(
                            buffer,
                            mimetype='application/json',
                            as_attachment=True,
                            download_name=blob_name
                        )
                    except Exception as e:
                        logger.error(f"Error downloading file: {str(e)}")
                        flash(f"Error downloading file: {str(e)}", 'danger')
        
        return render_template('storage_manager.html', 
                              files=files, 
                              latest_upload=latest_upload,
                              upload_error=upload_error)

    except Exception as e:
        logger.error(f"Error in storage manager: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
        return render_template('storage_manager.html', 
                              files=[], 
                              upload_error=str(e))