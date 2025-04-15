# src/utils/filters.py
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def format_date(date_string):
    try:
        date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
        return date.strftime("%b %d, %Y")
    except Exception as e:
        logger.error(f"Error formatting date: {str(e)}")
        return date_string