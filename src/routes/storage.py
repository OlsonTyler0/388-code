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

        # Initialize DataStorage - wrap in try/except to handle connection issues
        try:
            data_storage = DataStorage(bucket_name)
            # Add a verification step
            connection_status = data_storage.verify_connection()
            if not connection_status:
                upload_error = "Connected to Google Cloud Storage, but failed to verify access permissions."
            else:
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
                    
                    # Add extra logging for debugging
                    if current_videos:
                        if isinstance(current_videos, dict) and 'error' in current_videos:
                            logger.error(f"YouTube API error: {current_videos['error']}")
                            flash(f"YouTube API error: {current_videos['error']}", 'danger')
                        else:
                            logger.info(f"Successfully retrieved {len(current_videos)} videos from YouTube API")
                            
                            # Create a timestamp and blob name
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            blob_name = f"privacy_videos_{timestamp}.json"
                            
                            # Add more detailed logging
                            logger.info(f"Attempting to save data to {blob_name}")
                            
                            # Save to Google Cloud Storage
                            saved_filename = data_storage.save_videos_data(current_videos, blob_name)
                            
                            if saved_filename:
                                logger.info(f"Successfully saved data to {saved_filename}")
                                flash(f'Data successfully uploaded as {saved_filename}!', 'success')
                                latest_upload = saved_filename
                                
                                # Refresh the file list after upload
                                files = data_storage.list_blobs()
                            else:
                                logger.error("Upload failed. No filename was returned from save_videos_data.")
                                flash('Upload failed. No filename was returned.', 'danger')
                    else:
                        logger.error("No data retrieved from YouTube API")
                        flash('No data retrieved from YouTube API', 'warning')
                
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

        # Create a summary based on the data type
        if data is None:
            summary = {
                "data_type": "None",
                "item_count": 0,
                "keys": "No data found",
                "sample": "No data available"
            }
        elif isinstance(data, list):
            summary = {
                "data_type": "List",
                "item_count": len(data),
                "keys": list(data[0].keys()) if data and isinstance(data[0], dict) else "Not dictionaries or empty list",
                "sample": data[0] if data else "Empty list"
            }
        elif isinstance(data, dict):
            summary = {
                "data_type": "Dictionary",
                "item_count": 1,
                "keys": list(data.keys()),
                "sample": {k: data[k] for k in list(data.keys())[:5]} if data else "Empty dictionary"
            }
        else:
            summary = {
                "data_type": type(data).__name__,
                "item_count": "Not applicable",
                "keys": "Not a list or dictionary",
                "sample": str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
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