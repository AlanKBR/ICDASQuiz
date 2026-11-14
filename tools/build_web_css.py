#!/usr/bin/env python3
"""Build the local, dependency-free CSS bundle for ICDASQuiz.

The three readable source sheets stay versioned for maintenance. The application
loads only app.css, preserving cascade order while reducing render-blocking
requests. Use --check in CI/tests to prevent a stale generated bundle.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "static/css/app.css"
SOURCES = (
    ROOT / "src/css/design-tokens.css",
    ROOT / "src/css/design-components.css",
    ROOT / "src/css/redesign.css",
)
RESET = """/* ICDASQuiz responsive UI. This single stylesheet is the production
   bundle of the approved design tokens, components, and application styles.
   Rebuild after editing one of the three source sheets. */
:where(html,body){margin:0;padding:0}
:where(h1,h2,h3,h4,h5,h6,p,figure,blockquote){margin:0}
:where(img,svg,video){max-width:100%;vertical-align:middle}
:where(button,input,textarea,select){font:inherit}
:where(button){cursor:pointer}
:where(a){color:inherit}
"""


def build() -> str:
    return RESET + "".join(
        "\n/* --- " + source.relative_to(ROOT).as_posix() + " --- */\n" + source.read_text()
        for source in SOURCES
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if app.css is stale")
    args = parser.parse_args()
    contents = build()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != contents:
            print("app.css is out of date: run python3 tools/build_web_css.py")
            return 1
        print("app.css is current")
        return 0
    OUTPUT.write_text(contents)
    print(f"Built {OUTPUT.relative_to(ROOT)} ({len(contents.encode())} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
