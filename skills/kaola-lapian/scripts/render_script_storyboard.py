#!/usr/bin/env python3
"""Render the per-second storyboard with matching 时间、画面、脚本 below each frame."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path


TIMELINE_PATTERN = re.compile(
    r"时间\s*[:：]\s*[\"“](.*?)[\"”]\s*\n"
    r"画面\s*[:：]\s*[\"“](.*?)[\"”]\s*\n"
    r"脚本\s*[:：]\s*[\"“](.*?)[\"”]",
    re.DOTALL,
)


def parse_timecode(value: str) -> float:
    parts = value.strip().split(":")
    if not parts or len(parts) > 3:
        raise ValueError(f"invalid timecode: {value}")
    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    return total


def parse_range(value: str) -> tuple[float, float]:
    parts = re.split(r"\s*[-–—]\s*", value.strip(), maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"invalid time range: {value}")
    start, end = parse_timecode(parts[0]), parse_timecode(parts[1])
    if end <= start:
        raise ValueError(f"time range must end after it starts: {value}")
    return start, end


def load_timeline(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    rows = []
    for index, (time_range, visual, script) in enumerate(TIMELINE_PATTERN.findall(text), start=1):
        start, end = parse_range(time_range)
        rows.append({
            "index": index,
            "time": time_range.strip(),
            "start_seconds": start,
            "end_seconds": end,
            "visual": " ".join(visual.split()),
            "script": " ".join(script.split()),
        })
    if not rows:
        raise ValueError(f"no 时间/画面/脚本 blocks found in {path}")
    return rows


def match_segment(seconds: float, timeline: list[dict]) -> dict:
    for segment in timeline:
        if segment["start_seconds"] <= seconds < segment["end_seconds"]:
            return segment
    if math.isclose(seconds, timeline[-1]["end_seconds"], abs_tol=0.05):
        return timeline[-1]
    return min(
        timeline,
        key=lambda row: min(abs(seconds - row["start_seconds"]), abs(seconds - row["end_seconds"])),
    )


def load_font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size, index=1 if bold and path.suffix == ".ttc" else 0)
            except (OSError, ValueError):
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    if not text:
        return ["无"]
    lines, current = [], ""
    for char in text:
        candidate = current + char
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current.rstrip())
            current = char.lstrip()
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    return lines or ["无"]


def draw_labeled_text(draw, x: int, y: int, label: str, value: str, fonts: dict, width: int) -> int:
    label_width = math.ceil(draw.textlength(label, font=fonts["label"]))
    value_width = max(20, width - label_width)
    lines = wrap_text(draw, value, fonts["body"], value_width)
    line_height = fonts["body"].getbbox("测试Ag")[3] + 8
    draw.text((x, y), label, fill=(82, 82, 82), font=fonts["label"])
    draw.text((x + label_width, y), lines[0], fill=(24, 24, 24), font=fonts["body"])
    for line in lines[1:]:
        y += line_height
        draw.text((x + label_width, y), line, fill=(24, 24, 24), font=fonts["body"])
    return y + line_height


def render(project: Path, timeline_path: Path, columns: int, cell_width: int, max_height: int) -> list[str]:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Pillow is required to build the script storyboard") from exc

    manifest_path = project / "frames.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames = manifest.get("frames", [])
    if not frames:
        raise ValueError(f"no frames found in {manifest_path}")
    timeline = load_timeline(timeline_path)
    fonts = {
        "number": load_font(24, bold=True),
        "label": load_font(22, bold=True),
        "body": load_font(22),
    }
    padding, gap, field_gap = 14, 10, 8
    prepared = []
    max_text_height = 0

    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for frame in frames:
        segment = match_segment(float(frame["seconds"]), timeline)
        image_path = project / frame["path"]
        image = Image.open(image_path).convert("RGB")
        image_height = max(1, round(image.height * cell_width / image.width))
        image = image.resize((cell_width, image_height), Image.Resampling.LANCZOS)
        usable_width = cell_width - 2 * padding
        number_h = fonts["number"].getbbox("#000")[3] + 10
        text_h = number_h
        for label, value in (("时间：", segment["time"]), ("画面：", segment["visual"]), ("脚本：", segment["script"])):
            label_width = math.ceil(measure.textlength(label, font=fonts["label"]))
            lines = wrap_text(measure, value, fonts["body"], max(20, usable_width - label_width))
            text_h += len(lines) * (fonts["body"].getbbox("测试Ag")[3] + 8) + field_gap
        max_text_height = max(max_text_height, text_h + 2 * padding)
        prepared.append((frame, segment, image))

    image_height = prepared[0][2].height
    cell_height = image_height + max_text_height
    rows_per_page = max(1, (max_height + gap) // (cell_height + gap))
    items_per_page = rows_per_page * columns
    pages = [prepared[start:start + items_per_page] for start in range(0, len(prepared), items_per_page)]
    multi = len(pages) > 1
    output_names, order_rows = [], []

    for page_index, page in enumerate(pages, start=1):
        row_count = math.ceil(len(page) / columns)
        canvas_width = columns * cell_width + (columns - 1) * gap
        canvas_height = row_count * cell_height + (row_count - 1) * gap
        canvas = Image.new("RGB", (canvas_width, canvas_height), (238, 238, 238))
        draw = ImageDraw.Draw(canvas)
        for page_item_index, (frame, segment, image) in enumerate(page):
            global_index = (page_index - 1) * items_per_page + page_item_index
            row_index = global_index // columns + 1
            column_index = global_index % columns + 1
            local_row = page_item_index // columns
            local_column = page_item_index % columns
            x = local_column * (cell_width + gap)
            y = local_row * (cell_height + gap)
            canvas.paste(image, (x, y))
            panel_top = y + image_height
            draw.rectangle((x, panel_top, x + cell_width - 1, y + cell_height - 1), fill="white")
            text_x, text_y = x + padding, panel_top + padding
            draw.text((text_x, text_y), f"#{frame['index']:03d}", fill=(20, 20, 20), font=fonts["number"])
            text_y += fonts["number"].getbbox("#000")[3] + 10
            text_y = draw_labeled_text(draw, text_x, text_y, "时间：", segment["time"], fonts, cell_width - 2 * padding)
            text_y += field_gap
            text_y = draw_labeled_text(draw, text_x, text_y, "画面：", segment["visual"], fonts, cell_width - 2 * padding)
            text_y += field_gap
            draw_labeled_text(draw, text_x, text_y, "脚本：", segment["script"], fonts, cell_width - 2 * padding)
            order_rows.append({
                "order": int(frame["index"]),
                "row": row_index,
                "column": column_index,
                "page": page_index,
                "frame_timestamp": frame["timestamp"],
                "frame": frame["path"],
                "timeline_segment": segment["index"],
                "time": segment["time"],
                "visual": segment["visual"],
                "script": segment["script"],
            })
        name = f"storyboard-script-grid-{page_index:02d}.jpg" if multi else "storyboard-script-grid.jpg"
        canvas.save(project / name, quality=92, optimize=True)
        output_names.append(name)

    order_payload = {
        "reading_order": "left-to-right, then top-to-bottom",
        "columns_per_row": columns,
        "storyboards": output_names,
        "timeline_source": str(timeline_path.relative_to(project)) if timeline_path.is_relative_to(project) else str(timeline_path),
        "items": order_rows,
    }
    (project / "storyboard-script-order.json").write_text(
        json.dumps(order_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest["script_storyboards"] = output_names
    manifest["script_storyboard_order_file"] = "storyboard-script-order.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--columns", type=int, default=6)
    parser.add_argument("--cell-width", type=int, default=360)
    parser.add_argument("--max-sheet-height", type=int, default=60000)
    args = parser.parse_args()
    if args.columns <= 0 or args.cell_width <= 0 or args.max_sheet_height <= 0:
        parser.error("columns, cell width, and max sheet height must be greater than zero")
    project = args.project.expanduser().resolve()
    timeline = (args.timeline or (project / "lapian-base.md")).expanduser().resolve()
    if not project.is_dir():
        parser.error(f"project directory not found: {project}")
    if not timeline.is_file():
        parser.error(f"timeline file not found: {timeline}")
    outputs = render(project, timeline, args.columns, args.cell_width, args.max_sheet_height)
    print(json.dumps({"ok": True, "storyboards": outputs, "project": str(project)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
