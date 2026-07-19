import numpy as np
import pandas as pd
import pytest
import json, os

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")

def load_fixture(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)
    
