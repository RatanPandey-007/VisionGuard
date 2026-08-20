import os
import sys

# Add root directory to path to enable package resolution for app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
