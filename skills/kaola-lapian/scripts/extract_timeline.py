#!/usr/bin/env python3
"""Extract timestamped frames, a long storyboard, audio, and media metadata."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def media_info(video: Path, ffprobe: str) -> dict:
    result = run([
        ffprobe, "-v", "error",
        "-show_entries", "format=duration,size,format_name:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,sample_rate,channels",
        "-of", "json", str(video),
    ])
    return json.loads(result.stdout)


def detect_scene_cuts(video: Path, ffmpeg: str, duration: float, threshold: float, min_gap: float) -> dict:
    result = subprocess.run([
        ffmpeg, "-hide_banner", "-i", str(video),
        "-filter:v", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-",
    ], text=True, capture_output=True)
    candidates = [float(value) for value in re.findall(r"pts_time:([0-9.]+)", result.stderr)]
    cuts = []
    for value in candidates:
        if value <= 0 or value >= duration:
            continue
        if not cuts or value - cuts[-1] >= min_gap:
            cuts.append(round(value, 3))
    boundaries = [0.0, *cuts, round(duration, 3)]
    segments = [
        {"index": idx + 1, "start_seconds": start, "end_seconds": end}
        for idx, (start, end) in enumerate(zip(boundaries, boundaries[1:]))
    ]
    return {"threshold": threshold, "minimum_gap_seconds": min_gap, "cuts": cuts, "segments": segments}


def timestamp(seconds: float) -> str:
    total_ms = max(0, round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    return f"{minutes:02d}:{secs:02d}.{millis:03d}"


def build_storyboards(frame_rows: list[dict], output: Path, cell_width: int, columns: int, max_height: int) -> list[str]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("Pillow is required to build the long storyboard") from exc

    if not frame_rows:
        return []
    try:
        font = ImageFont.load_default(size=18)
    except TypeError:
        font = ImageFont.load_default()
    header_h, gap = 34, 4
    prepared = []
    for item_index, row in enumerate(frame_rows):
        image = Image.open(row["absolute_path"]).convert("RGB")
        target_h = max(1, round(image.height * cell_width / image.width))
        image = image.resize((cell_width, target_h), Image.Resampling.LANCZOS)
        row["storyboard_order"] = item_index + 1
        row["storyboard_row"] = item_index // columns + 1
        row["storyboard_column"] = item_index % columns + 1
        prepared.append((row, image))

    cell_height = header_h + prepared[0][1].height
    rows_per_page = max(1, (max_height + gap) // (cell_height + gap))
    items_per_page = rows_per_page * columns
    pages = [prepared[start:start + items_per_page] for start in range(0, len(prepared), items_per_page)]

    paths = []
    multi = len(pages) > 1
    for page_index, page in enumerate(pages, start=1):
        row_count = math.ceil(len(page) / columns)
        canvas_width = columns * cell_width + (columns - 1) * gap
        canvas_height = row_count * cell_height + (row_count - 1) * gap
        canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
        draw = ImageDraw.Draw(canvas)
        for page_item_index, (row, image) in enumerate(page):
            local_row = page_item_index // columns
            local_column = page_item_index % columns
            x = local_column * (cell_width + gap)
            y = local_row * (cell_height + gap)
            draw.rectangle((x, y, x + cell_width, y + header_h), fill=(18, 18, 18))
            draw.text((x + 8, y + 8), f"#{row['index']:03d}  {row['timestamp']}", fill="white", font=font)
            canvas.paste(image, (x, y + header_h))
            row["storyboard_page"] = page_index
        name = f"storyboard-grid-{page_index:02d}.jpg" if multi else "storyboard-grid.jpg"
        path = output / name
        canvas.save(path, quality=90, optimize=True)
        paths.append(name)
    return paths


def write_storyboard_order(frame_rows: list[dict], output: Path, columns: int, storyboards: list[str]) -> None:
    items = [
        {
            "order": row["storyboard_order"],
            "row": row["storyboard_row"],
            "column": row["storyboard_column"],
            "page": row["storyboard_page"],
            "timestamp": row["timestamp"],
            "seconds": row["seconds"],
            "frame": row["path"],
        }
        for row in frame_rows
    ]
    payload = {
        "reading_order": "left-to-right, then top-to-bottom",
        "columns_per_row": columns,
        "storyboards": storyboards,
        "items": items,
    }
    (output / "storyboard-order.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 分镜顺序",
        "",
        f"- 阅读顺序：从左到右，排满 {columns} 张后进入下一行。",
        f"- 总分镜数：{len(items)}",
        "",
        "| 顺序 | 行 | 列 | 时间码 | 图片 |",
        "|---:|---:|---:|---|---|",
    ]
    lines.extend(
        f"| {item['order']:03d} | {item['row']} | {item['column']} | {item['timestamp']} | {item['frame']} |"
        for item in items
    )
    (output / "storyboard-order.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--cell-width", "--sheet-width", dest="cell_width", type=int, default=240)
    parser.add_argument("--columns", type=int, default=6)
    parser.add_argument("--max-sheet-height", type=int, default=60000)
    parser.add_argument("--scene-threshold", type=float, default=0.18)
    parser.add_argument("--minimum-scene-gap", type=float, default=0.35)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if args.columns <= 0:
        parser.error("--columns must be greater than zero")
    video = args.video.expanduser().resolve()
    if not video.is_file():
        parser.error(f"video not found: {video}")
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        parser.error("ffmpeg and ffprobe must be available on PATH")

    output = args.output.expanduser().resolve()
    frames_dir = output / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    info = media_info(video, ffprobe)
    duration = float(info.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise RuntimeError("could not determine video duration")
    (output / "video-info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    scene_data = detect_scene_cuts(video, ffmpeg, duration, args.scene_threshold, args.minimum_scene_gap)
    (output / "scene-cuts.json").write_text(json.dumps(scene_data, ensure_ascii=False, indent=2), encoding="utf-8")

    for old in frames_dir.glob("frame_*.jpg"):
        old.unlink()
    fps = 1.0 / args.interval
    run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
        "-vf", f"fps=fps={fps:.12g}:start_time=0", "-q:v", "2",
        str(frames_dir / "frame_%06d.jpg"),
    ])

    rows = []
    for idx, path in enumerate(sorted(frames_dir.glob("frame_*.jpg"))):
        seconds = min(idx * args.interval, duration)
        rows.append({
            "index": idx + 1,
            "seconds": round(seconds, 3),
            "timestamp": timestamp(seconds),
            "path": str(path.relative_to(output)),
            "absolute_path": str(path),
        })
    storyboards = build_storyboards(rows, output, args.cell_width, args.columns, args.max_sheet_height)
    write_storyboard_order(rows, output, args.columns, storyboards)
    for row in rows:
        row.pop("absolute_path", None)
    manifest = {
        "source": os.path.relpath(video, output),
        "duration_seconds": duration,
        "interval_seconds": args.interval,
        "expected_minimum_frames": math.floor(duration / args.interval),
        "actual_frames": len(rows),
        "storyboards": storyboards,
        "storyboard_reading_order": "left-to-right, then top-to-bottom",
        "storyboard_columns_per_row": args.columns,
        "storyboard_order_files": ["storyboard-order.json", "storyboard-order.md"],
        "frames": rows,
    }
    (output / "frames.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    audio_path = output / "audio.wav"
    has_audio = any(stream.get("codec_type") == "audio" for stream in info.get("streams", []))
    if has_audio:
        run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio_path),
        ])
    print(json.dumps({
        "ok": True,
        "duration_seconds": duration,
        "frame_count": len(rows),
        "storyboards": storyboards,
        "scene_count": len(scene_data["segments"]),
        "audio": str(audio_path) if has_audio else None,
        "output": str(output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or str(exc), file=sys.stderr)
        raise SystemExit(exc.returncode)
