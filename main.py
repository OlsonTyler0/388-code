# ╔═══════════════════════════════════════════════════════════╗
#   main.py
#       All this does is create the app and let src folder
#       do its thing.
# ╚═══════════════════════════════════════════════════════════╝
from src.app import create_app
import os

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)