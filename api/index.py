import sys
import os

# Add project root to sys.path so server and core modules import cleanly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app