import os
import sys

CERT = r"C:\Users\marti\trading_agent\.trading_certs\combined_cacert.pem"
if os.path.exists(CERT):
    os.environ["SSL_CERT_FILE"] = CERT
    os.environ["CURL_CA_BUNDLE"] = CERT

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    

import fetch_data
import yfinance as yf
import json

    
raw = yf.download(["AAPL", "META"],
                    period="1y",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    progress=False,
                    threads=True,)
    
hist = raw["AAPL"]
results = fetch_data.process_ticker("AAPL", hist)

print(json.dumps(results, indent=2))

"""info = yf.Ticker("AAPL").info
for key in sorted(info):
    print(key, " = ", info[key])"""