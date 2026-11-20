#!/usr/bin/env python3
"""ICDASQuiz offline presentation runner. Python 3 stdlib only.

Binds exclusively to 127.0.0.1; never needs Zezin, Tailscale or internet.
Run from the extracted package root: python3 run_offline.py
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import webbrowser

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tools"))
from preview_server import PreviewHandler  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Open the ICDASQuiz presentation offline")
    parser.add_argument("--port", type=int, default=0, help="Localhost port, 0 finds a free one")
    parser.add_argument("--no-browser", action="store_true", help="Serve only, without launching a browser")
    parser.add_argument("--presentation", action="store_true", help="Start in clean stage-only presentation mode")
    args = parser.parse_args()
    if not (0 <= args.port <= 65535):
        parser.error("Invalid port")
    site = HERE / "site"
    if not (site / "index.html").is_file():
        parser.error("Missing site/index.html: extract the entire archive before launching")
    handler = partial(PreviewHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    url = "http://127.0.0.1:%d/" % server.server_address[1]
    if args.presentation:
        url += "?presentation=1"
    print("ICDASQuiz offline ready at " + url, flush=True)
    print("Ctrl+C stops the local server. No internet connection is required.", flush=True)
    try:
        if not args.no_browser:
            webbrowser.open_new_tab(url)
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nOffline preview stopped.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
