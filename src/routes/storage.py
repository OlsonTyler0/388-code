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

        # Initialize DataStorage
        logger.info(f"Initializing DataStorage with bucket: {bucket_name}")
        try:
            data_storage = DataStorage(bucket_name)
            logger.info("DataStorage initialized successfully")
            files = data_storage.list_blobs()
            logger.info(f"Retrieved {len(files)} files from bucket")
        except Exception as storage_error:
            logger.error(f"Error connecting to Google Cloud Storage: {str(storage_error)}")
            upload_error = f"Could not connect to Google Cloud Storage: {str(storage_error)}"
        
        if request.method == 'POST':
            logger.info(f"POST request received with form data: {request.form}")
            
            if 'upload' in request.form and not upload_error:
                logger.info("Upload operation requested")
                try:
                    # Get fresh data from YouTube API
                    logger.info("Initializing YouTubeStats")
                    youtube_stats = YouTubeStats()
                    logger.info("Fetching privacy videos from YouTube API")
                    current_videos = youtube_stats.search_privacy_videos(max_results=20)
                    
                    # Add detailed debugging for the response
                    if current_videos:
                        logger.info(f"Type of current_videos: {type(current_videos)}")
                        if isinstance(current_videos, list):
                            logger.info(f"Number of videos retrieved: {len(current_videos)}")
                            if current_videos:
                                logger.info(f"First video keys: {list(current_videos[0].keys())}")
                        elif isinstance(current_videos, dict):
                            logger.info(f"Dictionary keys: {list(current_videos.keys())}")
                            if 'error' in current_videos:
                                logger.error(f"YouTube API error: {current_videos['error']}")
                                flash(f"YouTube API error: {current_videos['error']}", 'danger')
                    else:
                        logger.warning("current_videos is None or empty")
                    
                    # Now attempt to process and save the data
                    if current_videos and isinstance(current_videos, list) and not ('error' in current_videos if isinstance(current_videos, dict) else False):
                        logger.info(f"Retrieved {len(current_videos)} videos from YouTube API")
                        
                        # Create a timestamp and blob name
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        blob_name = f"privacy_videos_{timestamp}.json"
                        
                        # Save to Google Cloud Storage
                        logger.info(f"Attempting to save videos data to {blob_name}")
                        saved_filename = data_storage.save_videos_data(current_videos, blob_name)
                        
                        if saved_filename:
                            logger.info(f"Successfully saved data to {saved_filename}")
                            flash(f'Data successfully uploaded as {saved_filename}!', 'success')
                            latest_upload = saved_filename
                            
                            # Refresh the file list after upload
                            logger.info("Refreshing file list")
                            files = data_storage.list_blobs()
                            logger.info(f"File list refreshed, found {len(files)} files")
                        else:
                            logger.error("Upload failed. No filename was returned.")
                            flash('Upload failed. No filename was returned.', 'danger')
                    else:
                        logger.warning("No videos retrieved from YouTube API or received error")
                        flash('No data retrieved from YouTube API or received error', 'warning')
                except Exception as e:
                    logger.error(f"Error during upload process: {str(e)}", exc_info=True)
                    flash(f"Upload failed: {str(e)}", 'danger')
            
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
        logger.error(f"Error in storage manager: {str(e)}", exc_info=True)
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

@storage_bp.route('/check_storage', methods=['GET'])
@login_required
def check_storage():
    try:
        bucket_name = session.get('storage_bucket', 'itc-388-youtube-r6')
        results = {
            'bucket_name': bucket_name,
            'status': 'Checking...',
            'errors': [],
            'file_list': []
        }
        
        # Try to initialize storage
        try:
            data_storage = DataStorage(bucket_name)
            results['status'] = 'DataStorage initialized'
            
            # Try to list files
            try:
                files = data_storage.list_blobs()
                results['file_list'] = files
                results['status'] = 'Successfully listed files'
            except Exception as list_error:
                results['errors'].append(f"Error listing files: {str(list_error)}")
                
            # Try to create a test file
            try:
                test_data = {'test': 'data', 'timestamp': datetime.now().isoformat()}
                test_blob = f"test_file_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                saved = data_storage.save_videos_data([test_data], test_blob)
                if saved:
                    results['status'] = 'Successfully created test file'
                    results['test_file'] = saved
                else:
                    results['errors'].append("Failed to create test file")
            except Exception as save_error:
                results['errors'].append(f"Error creating test file: {str(save_error)}")
                
        except Exception as init_error:
            results['errors'].append(f"Error initializing DataStorage: {str(init_error)}")
            
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@storage_bp.route('/test_youtube_api', methods=['GET'])
@login_required
def test_youtube_api():
    try:
        logger.info("Testing YouTube API connection")
        youtube_stats = YouTubeStats()
        logger.info("YouTubeStats initialized, attempting to search for videos")
        videos = youtube_stats.search_privacy_videos(max_results=5)
        logger.info(f"Received response from YouTube API: type={type(videos)}")
        
        result = {
            'success': not (isinstance(videos, dict) and 'error' in videos),
            'videos_count': len(videos) if isinstance(videos, list) else 0,
            'data_type': type(videos).__name__,
            'error': videos.get('error') if isinstance(videos, dict) and 'error' in videos else None,
            'sample': videos[0] if isinstance(videos, list) and videos else videos
        }
        
        logger.info(f"YouTube API test result: {result['success']}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing YouTube API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        })