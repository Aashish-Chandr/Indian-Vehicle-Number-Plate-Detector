import sys
import os
from vercel_python_runtime import wsgi_handler
from wsgiref.simple_server import make_server

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel requires a handler function, not just the app object
handler = app
