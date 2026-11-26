#!/usr/bin/env python3
"""Small Tailscale-only HTTP preview server.

Serves precompressed Vite build artifacts, supports video byte ranges and
immutable caching for content-hashed JS/CSS. Standard library only.
"""
from __future__ import annotations

import argparse
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import re

ROOT = Path(__file__).resolve().parents[1]
RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")
HASHED = re.compile(r"/assets/[^/]+-[A-Za-z0-9_-]{6,}\.(?:js|css)$")


class PreviewHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        if HASHED.search(self.path.split("?", 1)[0]):
            self.send_header("Cache-Control", "private, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "private, no-cache")
        if self.path.split("?", 1)[0].endswith(".mp4"):
            self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        self._range = None
        path = Path(self.translate_path(self.path))
        # The public entrypoint is '/', which SimpleHTTPRequestHandler would
        # otherwise serve through its directory branch (bypassing our gzip
        # negotiation). Resolve index.html explicitly, preserving redirects
        # for directories requested without a trailing slash.
        if path.is_dir() and self.path.split("?", 1)[0].endswith("/"):
            index = path / "index.html"
            if index.is_file():
                path = index
        if not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        range_header = self.headers.get("Range")
        if range_header and path.suffix == ".mp4":
            match = RANGE.fullmatch(range_header.strip())
            if not match:
                self.send_error(HTTPStatus.BAD_REQUEST, "Unsupported byte range")
                return None
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            elif last:
                start = max(0, size-int(last))
                end = size-1
            else:
                self.send_error(HTTPStatus.BAD_REQUEST, "Empty byte range")
                return None
            if start >= size or end < start:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", "bytes */" + str(size))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            f = path.open("rb")
            self._range = (start, end)
            self.send_response(HTTPStatus.PARTIAL_CONTENT)
            self.send_header("Content-Type", self.guess_type(str(path)))
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            f.seek(start)
            return f

        # Gzip is used only for text/geometry payloads, never MP4 or images.
        gzpath = Path(str(path)+".gz")
        accepted = self.headers.get("Accept-Encoding", "")
        if "gzip" in accepted.lower() and gzpath.is_file() and not range_header:
            f = gzpath.open("rb")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", self.guess_type(str(path)))
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
            self.send_header("Content-Length", str(gzpath.stat().st_size))
            self.end_headers()
            return f

        return super().send_head()

    def copyfile(self, source, outputfile):
        if self._range is None:
            return super().copyfile(source, outputfile)
        start, end = self._range
        remaining = end-start+1
        while remaining:
            block = source.read(min(128*1024, remaining))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", required=True, help="Explicit tailnet IP, never public bind")
    ap.add_argument("--port", type=int, default=54173)
    ap.add_argument("--directory", type=Path, default=ROOT/"dist")
    args = ap.parse_args()
    if args.bind in {"0.0.0.0", "::", ""}:
        ap.error("Refusing public bind; use an explicit Tailscale IP")
    if not (args.directory/"index.html").is_file():
        ap.error("Vite dist/index.html missing; run npm run build")
    handler = partial(PreviewHandler, directory=str(args.directory.resolve()))
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print("Serving "+str(args.directory)+" at http://"+args.bind+":"+str(args.port),flush=True)
    try:
        server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
