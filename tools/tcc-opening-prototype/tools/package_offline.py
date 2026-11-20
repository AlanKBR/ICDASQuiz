#!/usr/bin/env python3
"""Build a private, portable ICDASQuiz opening delivery archive.

Requires only Python 3. The Vite build must already exist; this tool never
touches the production application, git, CDN or network.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
OUT = ROOT / "assets" / "ICDASQuiz_TCC_Abertura_V0.10.2_OFFLINE.zip"
PREFIX = "ICDASQuiz_TCC_Abertura/"
FILES: dict[str, bytes] = {}

if not (ROOT/"dist"/"index.html").is_file():
    raise SystemExit("Build missing: run npm run build before packaging")

def add_file(archive_name: str, path: Path):
    if not path.is_file():
        raise RuntimeError("Missing essential file: "+str(path))
    FILES[archive_name] = path.read_bytes()

for path in sorted((ROOT/"dist").rglob("*")):
    if path.is_file():
        add_file("site/"+path.relative_to(ROOT/"dist").as_posix(), path)

text_sources = [
    "index.html","package.json","package-lock.json","README.md","INTEGRATION_AGENT.md",
    "src/main.js","src/style.css","src/intro.css","src/quiz.css",
    "tools/prepare_dist.mjs","tools/preview_server.py","tools/smoke_check.mjs",
    "tools/bench_sampling.mjs","tools/optimize_textures.py","tools/recompose_video.py"
]
for relative in text_sources:
    add_file("source/"+relative, ROOT/relative)

add_file("tools/preview_server.py",ROOT/"tools/preview_server.py")
add_file("run_offline.py",ROOT/"tools/run_offline.py")
add_file("INTEGRATION_AGENT.md",ROOT/"INTEGRATION_AGENT.md")
add_file("docs/TCC_ABERTURA_3D_HANDOFF_20261117.md", PROJECT/"docs/TCC_ABERTURA_3D_HANDOFF_20261117.md")
add_file("docs/TCC_ABERTURA_PERFORMANCE_20261120.md",PROJECT/"docs/TCC_ABERTURA_PERFORMANCE_20261120.md")

FILES["start-linux.sh"] = b"""#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec python3 run_offline.py
"""
FILES["start-windows.cmd"] = b"""@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 run_offline.py
) else (
    python run_offline.py
)
pause
"""
FILES["INICIO_AQUI.txt"] = (
    "ICDASQuiz | Abertura do TCC | OFFLINE\n"
    "Extraia o ZIP inteiro e execute start-linux.sh ou start-windows.cmd.\n"
    "Para rodar apenas o slide: python3 run_offline.py --presentation\n"
    "Requer Python 3, sem internet e sem instalacao npm.\n"
    "NAO abra site/index.html diretamente por file://; use o launcher.\n"
    "Leia INTEGRATION_AGENT.md para incorporar ao deck.\n"
    "Os arquivos incluem imagens pessoais: uso privado autorizado, sem publicacao.\n"
).encode("utf-8")

records=[]
for name, data in sorted(FILES.items()):
    records.append({"path":name,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
manifest = {
    "package":"ICDASQuiz TCC Opening Offline",
    "version":"0.10.2",
    "creative_baseline":"0.10",
    "date":"2026-11-20",
    "runtime":"Python 3 stdlib HTTP server, static HTML/CSS/JS/WebGL",
    "file_count":len(records),
    "files":records
}
FILES["manifest.json"]=json.dumps(manifest,ensure_ascii=False,indent=2).encode("utf-8")
FILES["manifest.sha256"]=("\n".join(record["sha256"]+"  "+record["path"] for record in records)+"\n").encode("utf-8")

def info(name:str):
    zi=ZipInfo(PREFIX+name,date_time=(2026,11,20,18,0,0))
    zi.compress_type=ZIP_DEFLATED
    zi.external_attr=(0o755 if name=="start-linux.sh" else 0o644)<<16
    return zi

OUT.parent.mkdir(parents=True,exist_ok=True)
with ZipFile(OUT,"w",compression=ZIP_DEFLATED,compresslevel=9,allowZip64=True) as archive:
    for name,data in sorted(FILES.items()):
        archive.writestr(info(name),data,compress_type=ZIP_DEFLATED,compresslevel=9)

with ZipFile(OUT,"r") as archive:
    if archive.testzip() is not None:
        raise RuntimeError("ZIP integrity failure")

total=sum(len(v) for v in FILES.values())
print(json.dumps({
    "output":str(OUT),"archive_bytes":OUT.stat().st_size,
    "uncompressed_bytes":total,"entries":len(FILES),
    "root":PREFIX,"sha256":hashlib.sha256(OUT.read_bytes()).hexdigest()
},ensure_ascii=False,indent=2))
