from fetch_data import sma

def test_sma_basic():
    closes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert sma(closes, 5) == 8.0   # mean of the LAST five: (6+7+8+9+10)/5
    
