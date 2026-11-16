"""

Usage:
    from quant_settings import QUANT_DB_PATH
"""

import os

QUANT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "quant.db"))
