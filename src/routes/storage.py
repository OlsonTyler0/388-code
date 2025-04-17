# src/routes/storage.py
from flask import Blueprint, render_template, request, session, flash, jsonify
from flask_login import login_required
from ..data_storage import DataStorage
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
storage_bp = Blueprint('storage', __name__)

@storage_bp.route('/storage_manager', methods=['GET', 'POST'])
@login_required
def storage_manager():
    try:
        bucket_name = session.get('storage_bucket', 'itc-388-youtube-r6')
        data_storage = DataStorage(bucket_name)
        
        if request.method == 'POST':
            if 'upload' in request.form:
                current_videos = session.get('current_videos')
                if current_videos:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    filename = f"{date_str}-privacy-analysis.json"
                    # Pass the filename to save_videos_data
                    data_storage.save_videos_data(current_videos, filename)  
                    flash('Data successfully uploaded to storage!', 'success')
                else:
                    flash('No current video data to upload', 'error')
            
            elif 'download' in request.form:
                blob_name = request.form.get('blob_name')
                if blob_name:
                    data = data_storage.load_data(blob_name)
                    return jsonify(data)
        
        files = data_storage.list_blobs()
        return render_template('storage_manager.html', files=files)

    except Exception as e:
        logger.error(f"Error in storage manager: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'error')
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
