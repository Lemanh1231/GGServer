#!/usr/bin/env python3
"""Run the Guitar Girl emulator.

  python3 run.py                      # HTTP on 0.0.0.0:8080
  python3 run.py --https --port 443   # HTTPS (auto self-signed cert if --cert omitted)
  python3 run.py --https --http       # both: HTTPS:443 + HTTP:8080

Env: GG_PUBLIC_HOST, GG_CDN_URL, GG_VERBOSE.
"""
import argparse, os, sys, threading, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import app

CERT = os.path.join(os.path.dirname(__file__), 'data', 'server.pem')

def ensure_cert():
    if os.path.exists(CERT):
        return CERT
    os.makedirs(os.path.dirname(CERT), exist_ok=True)
    # self-signed cert valid for the pmang hosts + wildcard
    san = "DNS:game.gtgl.pmang.cloud,DNS:dl.gtgl.pmang.cloud,DNS:*.pmang.cloud,DNS:*.neonapi.com,DNS:localhost,IP:127.0.0.1"
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
        '-keyout', CERT, '-out', CERT, '-days', '3650',
        '-subj', '/CN=*.pmang.cloud',
        '-addext', f'subjectAltName={san}',
    ], check=True)
    print("generated self-signed cert:", CERT)
    return CERT

def serve(host, port, cert):
    httpd = app.make_server(host, port, cert)
    proto = 'https' if cert else 'http'
    print(f"listening {proto}://{host}:{port}")
    httpd.serve_forever()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--https', action='store_true')
    ap.add_argument('--http', action='store_true', help='also start plain HTTP:8080')
    ap.add_argument('--cert', default=None)
    args = ap.parse_args()

    threads = []
    if args.https:
        cert = args.cert or ensure_cert()
        threads.append(threading.Thread(target=serve, args=(args.host, args.port, cert), daemon=True))
        if args.http:
            threads.append(threading.Thread(target=serve, args=(args.host, 8080, None), daemon=True))
    else:
        threads.append(threading.Thread(target=serve, args=(args.host, args.port, None), daemon=True))

    for t in threads: t.start()
    print("Ctrl-C to stop. Captures -> emulator/captures/, player data -> emulator/data/")
    try:
        while True: threading.Event().wait(3600)
    except KeyboardInterrupt:
        print("\nbye")

if __name__ == '__main__':
    main()
