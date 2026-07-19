# conftest.py — pytest loads this automatically before any test in this folder.
# Its only job: put the repo root on the import path so tests can
# `import fetch_data` even though they live one level down in tests/.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
