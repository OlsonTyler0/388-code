# 388 Code

This Flask application provides functionality for YouTube privacy analysis and JSON data management using Google Cloud Services.

## The layout of this code

- src/routes
    Contains the routes for all the different parts of the website
- src/templates
    Contains all the templates aka html files
- src/utils
    Contains the utilities for the system.



## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```
Install required dependencies:
`pip install -r requirements.txt`

```bash
export YOUTUBE_API_KEY='your_key_here'
```

```bash 
export FLASK_SECRET_KEY='your_secret_key_here'
```