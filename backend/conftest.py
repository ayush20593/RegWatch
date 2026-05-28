import sys
import os

# Ensure backend/ is at the front of sys.path so `app` resolves to backend/app/
# rather than the top-level app.py
sys.path.insert(0, os.path.dirname(__file__))
