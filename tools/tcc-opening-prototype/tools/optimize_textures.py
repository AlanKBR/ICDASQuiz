#!/usr/bin/env python3
"""Generate reproducible presentation-size textures from the untouched source ZIP.

The original 4K PNG files remain in assets/maxillary_first_molar.zip.
Only the working public assets are resized. Requires Pillow.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from PIL import Image, ImageChops, ImageStat
import hashlib
import math

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "assets" / "maxillary_first_molar.zip"
DEST = ROOT / "public" / "assets" / "molar" / "textures"
TEXTURES = ("defaultMat_baseColor.png", "defaultMat_normal.png")
SIZE = (2048, 2048)


def optimize() -> None:
    with ZipFile(ARCHIVE) as archive:
        for name in TEXTURES:
            data = archive.read("textures/" + name)
            with Image.open(BytesIO(data)) as original:
                if original.size != (4096, 4096):
                    raise RuntimeError(f"Unexpected source dimensions for {name}: {original.size}")
                source = original.convert("RGB")
                # BOX averages tangent normal maps in vector space; the
                # shader renormalizes sampled normals. LANCZOS is used on
                # the sRGB base-color texture to preserve edges and detail.
                resampler = Image.Resampling.BOX if "normal" in name else Image.Resampling.LANCZOS
                resized = source.resize(SIZE, resampler)
                out = DEST / name
                out.parent.mkdir(parents=True, exist_ok=True)
                resized.save(out, format="PNG", optimize=True)

                # Compare original to the downsampled image reprojected to
                # original resolution. This is texture-domain PSNR, not a
                # rendered appearance or clinical-colour accuracy metric.
                restored = resized.resize(source.size, Image.Resampling.BILINEAR)
                diff = ImageChops.difference(source, restored)
                rms = ImageStat.Stat(diff).rms
                mse = sum(v*v for v in rms)/3.0
                psnr = 10*math.log10((255*255)/mse) if mse else float("inf")
                source_sha = hashlib.sha256(data).hexdigest()[:12]
                print(
                    f"{name}: 4096² -> 2048²; "
                    f"{len(data):,} -> {out.stat().st_size:,} bytes; "
                    f"texture PSNR={psnr:.2f} dB; srcsha={source_sha}"
                )


if __name__ == "__main__":
    optimize()
