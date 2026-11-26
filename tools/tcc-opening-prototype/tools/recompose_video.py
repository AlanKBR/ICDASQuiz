#!/usr/bin/env python3
"""Recompose the approved 4 s intro to begin on the exact final quiz monitor.

The initial Gemini video had a white/blank monitor for ~0.2 s and a smaller
different-looking quiz panel after that. Its camera movement and person are
preserved; the bridge replaces only the initial still monitor portion.

Requires Pillow and FFmpeg. Source and output are local private prototype assets.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFilter

W, H, FPS, N = 1280, 720, 24, 96
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "public" / "assets"


def smooth(a: float, b: float, value: float) -> float:
    t = max(0., min(1., (value-a)/(b-a)))
    return t*t*(3-2*t)


def signed_off_source(static: Image.Image) -> Image.Image:
    """Reproduce the green checked #4 state at the exact UI coordinates."""
    result = static.copy()
    draw = ImageDraw.Draw(result)
    cx, cy, radius = round(W*.5506), round(H*.5987), round(W*.0384/2)
    draw.ellipse((cx-radius-2,cy-radius-2,cx+radius+2,cy+radius+2),
                 fill="#effff9")
    draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),
                 fill="#148a73")
    check = [
        (cx-radius*.49, cy),
        (cx-radius*.13, cy+radius*.37),
        (cx+radius*.53, cy-radius*.45)
    ]
    draw.line(check, fill="white", width=round(radius*.20), joint="curve")
    return result


def perspective_bridge(frame: Image.Image, static: Image.Image,
                       output_time: float, source_time: float) -> Image.Image:
    # Source video starts on a blank monitor, while the approved quiz already
    # displays a clinical image and a selected answer. Retain the EXACT final
    # static image until the moment the camera begins its fast whip-pan.
    # Then simulate the first part of that pan by moving+blurring the still;
    # switch to the original Gemini camera ONLY when both sides are in motion.
    # No crossfade between two differently positioned monitors.
    cut_at = .50
    hold_until = .29
    if output_time >= cut_at:
        return frame
    if output_time <= hold_until:
        return static
    t=smooth(hold_until,cut_at,output_time)
    offset=round(640*t)
    moving=static.transform((W,H),Image.Transform.AFFINE,
                            (1,0,offset,0,1,0),
                            resample=Image.Resampling.BICUBIC,
                            fillcolor=(248,249,250))
    return moving.filter(ImageFilter.GaussianBlur(radius=1+17*t))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=BASE/"intro_video_4s.mp4")
    args = parser.parse_args()
    # The original 4-second footage lives outside public/, so private source
    # frames are never copied to dist or served over the network.
    source = ROOT/"assets"/"intro_video_4s.mp4"
    if not source.is_file():
        raise SystemExit(f"Missing source video: {source}")
    reference = Image.open(BASE/"monitor_quiz_reference.png").convert("RGB")
    static = reference.resize((W,H),Image.Resampling.LANCZOS)
    static = signed_off_source(static)

    # Extract the original video frames as an RGB stream.
    decoder = subprocess.Popen([
        "ffmpeg","-v","error","-i",str(source),
        "-f","rawvideo","-pix_fmt","rgb24","-vsync","0","-"
    ],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert decoder.stdout
    raw_frames=[]
    block=W*H*3
    while True:
        frame=decoder.stdout.read(block)
        if len(frame)!=block:break
        raw_frames.append(Image.frombytes("RGB",(W,H),frame))
    err=decoder.stderr.read()
    if decoder.wait()!=0 or len(raw_frames)<90:
        raise RuntimeError("Could not decode the input clip: "+str(err[:300]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoder=subprocess.Popen([
        "ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24",
        "-s",f"{W}x{H}","-r",str(FPS),"-i","-",
        "-c:v","libx264","-preset","fast","-crf","18",
        "-pix_fmt","yuv420p","-movflags","+faststart",
        str(args.output)
    ],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    assert encoder.stdin
    try:
        for i in range(N):
            t=i/FPS
            source_t=min(t+.25, (len(raw_frames)-1)/FPS)
            src_idx=min(round(source_t*FPS),len(raw_frames)-1)
            corrected=perspective_bridge(raw_frames[src_idx],static,t,source_t)
            encoder.stdin.write(corrected.tobytes())
        encoder.stdin.close()
        error=encoder.stderr.read()
        if encoder.wait()!=0:
            raise RuntimeError("Could not encode output: "+str(error[:300]))
    finally:
        if decoder.poll() is None: decoder.terminate()
        if encoder.poll() is None: encoder.terminate()
    print(f"Rendered {N/FPS:.2f}s -> {args.output}, {args.output.stat().st_size} bytes")


if __name__=="__main__":
    main()
