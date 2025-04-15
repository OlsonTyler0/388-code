import json
from google.cloud import storage
from datetime import datetime

def download_json_and_summarize(bucket_name, source_blob_name, destination_file_name):
    """
    Downloads a JSON file from Google Cloud Storage and prints a summary of its content.
    
    Args:
        bucket_name (str): Name of the GCS bucket.
        source_blob_name (str): Name of the file in the bucket.
        destination_file_name (str): Local file path to save the downloaded file.
    """
    # Initialize the GCS client
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    
    # Download the file
    blob.download_to_filename(destination_file_name)
    print(f"File {source_blob_name} downloaded to {destination_file_name}.")
    
    # Load and summarize the JSON content
    with open(destination_file_name, 'r') as json_file:
        data = json.load(json_file)
        print("\nSummary of the JSON content:")
        
        if isinstance(data, list):
            print(f"- The JSON file contains a list with {len(data)} items.")
            print(f"- Example item: {data[0]}")
        elif isinstance(data, dict):
            print(f"- The JSON file contains a dictionary with {len(data.keys())} keys.")
            print(f"- Keys: {list(data.keys())}")
        else:
            print(f"- The JSON file contains data of type {type(data).__name__}.")

# Replace with your bucket details and file names

current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
bucket_name = "itc-388-youtube-r6"
source_blob_name = "youtube_trending_stats.json"
destination_file_name = f"{current_time}_youtube_trending_stats.json"

# Call the function
download_json_and_summarize(bucket_name, source_blob_name, destination_file_name)
