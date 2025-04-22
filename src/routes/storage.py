# src/routes/storage.py
from flask import Blueprint, render_template, request, session, flash, jsonify, redirect, url_for
from flask_login import login_required
from ..data_storage import DataStorage
from ..youtube_stats import YouTubeStats  # Add this import
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)
storage_bp = Blueprint('storage', __name__)

@storage_bp.route('/storage_manager', methods=['GET', 'POST'])
@login_required
def storage_manager():
    try:
        # Get bucket name from session or use default
        bucket_name = session.get('storage_bucket', 'itc-388-youtube-r6')
        data_storage = DataStorage(bucket_name)
        latest_upload = None
        
        if request.method == 'POST':
            if 'upload' in request.form:
                try:
                    # Initialize YouTube API client
                    youtube_stats = YouTubeStats()
                    
                    # Get videos related to data privacy
                    privacy_videos = youtube_stats.search_privacy_videos(max_results=20)
                    
                    # Check if we received valid data
                    if isinstance(privacy_videos, dict) and 'error' in privacy_videos:
                        flash(f"Error fetching videos: {privacy_videos['error']}", 'danger')
                        return redirect(url_for('storage.storage_manager'))
                    
                    if not privacy_videos:
                        flash('No video data found to upload', 'warning')
                        return redirect(url_for('storage.storage_manager'))
                    
                    # Create filename with timestamp for uniqueness
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"privacy_videos_{timestamp}.json"
                    
                    # Save data to Google Cloud Storage
                    saved_filename = data_storage.save_videos_data(privacy_videos, filename)
                    
                    # Set success message and update latest upload reference
                    flash(f'Data successfully uploaded as {saved_filename}!', 'success')
                    latest_upload = saved_filename
                    
                except Exception as e:
                    logger.error(f"Error during data upload: {str(e)}")
                    flash(f"Error during upload: {str(e)}", 'danger')
                    return redirect(url_for('storage.storage_manager'))
            
            elif 'download' in request.form:
                blob_name = request.form.get('blob_name')
                if not blob_name:
                    flash('No file specified for download', 'warning')
                    return redirect(url_for('storage.storage_manager'))
                
                try:
                    # Load data from Google Cloud Storage
                    data = data_storage.load_data(blob_name)
                    return jsonify(data)
                except Exception as e:
                    logger.error(f"Error downloading file {blob_name}: {str(e)}")
                    flash(f"Error downloading file: {str(e)}", 'danger')
                    return redirect(url_for('storage.storage_manager'))
        
        # List all files in the bucket
        try:
            files = data_storage.list_blobs()
            files.sort(reverse=True)  # Show newest files first
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            flash(f"Error listing files: {str(e)}", 'danger')
            files = []
        
        return render_template('storage_manager.html', 
                              files=files,
                              latest_upload=latest_upload)

    except Exception as e:
        logger.error(f"Error in storage manager: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
        return render_template('storage_manager.html', files=[])

@storage_bp.route('/summarize_json', methods=['GET'])
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