#!/usr/bin/env python3
"""Build a merged CA bundle: certifi's Mozilla list + Windows system store.

Needed because this machine has something (AV / corporate proxy) doing TLS
interception that injects a root cert only Windows' native store trusts.
curl_cffi (yfinance's HTTP backend) reads SSL_CERT_FILE/CURL_CA_BUNDLE as a
plain PEM file, so we generate one here instead of relying on certifi alone.
Re-run this if you start seeing SSL errors again (e.g. after a Windows
certificate update).
"""
import ssl
import base64
import os
import certifi

out_path = os.path.join(os.path.dirname(__file__), "combined_cacert.pem")

with open(certifi.where(), "r", encoding="utf-8") as f:
    bundle = f.read()

seen_ders = set()
for store in ("ROOT", "CA"):
    for der, encoding, trust in ssl.enum_certificates(store):
        if encoding != "x509_asn":
            continue
        if der in seen_ders:
            continue
        seen_ders.add(der)
        pem = ssl.DER_cert_to_PEM_cert(der)
        bundle += pem

with open(out_path, "w", encoding="utf-8") as f:
    f.write(bundle)

print(f"Wrote merged bundle ({len(seen_ders)} Windows certs + certifi) to {out_path}")
