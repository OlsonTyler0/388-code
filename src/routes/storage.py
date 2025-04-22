# src/routes/storage.py
from flask import Blueprint, render_template, request, session, flash, jsonify, redirect, url_for, send_file
from flask_login import login_required
from ..data_storage import DataStorage
from ..youtube_stats import YouTubeStats
from datetime import datetime
import logging
import json
import io

logger = logging.getLogger(__name__)
storage_bp = Blueprint('storage', __name__)

@storage_bp.route('/storage_manager', methods=['GET', 'POST'])
@login_required
def storage_manager():
    try:
        bucket_name = session.get('storage_bucket', 'itc-388-youtube-r6')
        data_storage = DataStorage(bucket_name)
        latest_upload = None
        
        if request.method == 'POST':
            if 'upload' in request.form:
                # Get fresh data from YouTube API - using search_privacy_videos instead of get_top_popular_videos
                youtube_stats = YouTubeStats()
                current_videos = youtube_stats.search_privacy_videos(max_results=20)
                
                if current_videos and not isinstance(current_videos, dict):  # Check it's not an error response
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    blob_name = f"privacy_videos_{timestamp}.json"
                    saved_filename = data_storage.save_videos_data(current_videos, blob_name)
                    flash(f'Data successfully uploaded as {saved_filename}!', 'success')
                    latest_upload = saved_filename
                else:
                    error_message = current_videos.get('error', 'No current video data to upload') if isinstance(current_videos, dict) else 'No current video data to upload'
                    flash(error_message, 'danger')
            
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
                        flash(f"Error downloading file: {str(e)}", 'danger')
        
        files = data_storage.list_blobs()
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

        # Fix for the view error - handle different data types properly
        if isinstance(data, list):
            item_count = len(data)
            keys = list(data[0].keys()) if data and isinstance(data[0], dict) else "No keys found or empty list"
            sample = data[0] if data else "No sample available"
        elif isinstance(data, dict):
            item_count = len(data.keys())
            keys = list(data.keys())
            sample = {k: data[k] for k in list(data.keys())[:5]} if data else "No sample available"
        else:
            item_count = "Not a list or dictionary"
            keys = "Not a list or dictionary"
            sample = str(data)[:200] + "..." if len(str(data)) > 200 else str(data)

        summary = {
            "file_name": source_blob_name,
            "data_type": type(data).__name__,
            "item_count": item_count,
            "keys": keys,
            "sample": sample
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