#!/usr/bin/env python3
"""Probe or run a local FunASR SenseVoice Small transcription."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import sys
import tempfile
import wave
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()


def dependency_status() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "funasr": importlib.util.find_spec("funasr") is not None,
        "torch": importlib.util.find_spec("torch") is not None,
        "torchaudio": importlib.util.find_spec("torchaudio") is not None,
    }


def use_bundled_runtime_if_needed() -> None:
    """Keep a stable call site without relying on a bundled local runtime."""
    return None


def resolve_cached_model(model: str) -> str:
    direct = Path(model).expanduser()
    if direct.exists():
        return str(direct.resolve())
    aliases = {
        "iic/SenseVoiceSmall": "iic--SenseVoiceSmall",
        "fsmn-vad": "iic--speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch": "iic--speech_fsmn_vad_zh-cn-16k-common-pytorch",
    }
    cache_name = aliases.get(model, model.replace("/", "--"))
    cache_roots = []
    configured_cache = os.environ.get("MODELSCOPE_CACHE")
    if configured_cache:
        configured = Path(configured_cache).expanduser()
        cache_roots.extend((configured / "models", configured))
    cache_roots.append(Path.home() / ".cache" / "modelscope" / "models")
    for cache_root in cache_roots:
        cached = cache_root / cache_name / "snapshots" / "master"
        if cached.exists():
            return str(cached.resolve())
    return model


def clean_text(value: str) -> str:
    return re.sub(r"<\|[^|]+\|>", "", value or "").strip()


def write_wave_segment(source: Path, target: Path, start_seconds: float, end_seconds: float) -> None:
    with wave.open(str(source), "rb") as reader:
        rate = reader.getframerate()
        start = max(0, round(start_seconds * rate))
        end = min(reader.getnframes(), round(end_seconds * rate))
        reader.setpos(start)
        frames = reader.readframes(max(0, end - start))
        params = reader.getparams()
    with wave.open(str(target), "wb") as writer:
        writer.setparams(params)
        writer.writeframes(frames)


def serializable(value):
    if isinstance(value, dict):
        return {str(key): serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def main() -> int:
    use_bundled_runtime_if_needed()
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default="iic/SenseVoiceSmall")
    parser.add_argument("--vad-model", default="fsmn-vad")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--language", default="auto")
    parser.add_argument("--segments", type=Path, help="scene-cuts.json produced by extract_timeline.py")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    status = dependency_status()
    if args.check:
        status["ready"] = all(status[name] for name in ("funasr", "torch", "torchaudio"))
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status["ready"] else 2
    if not args.audio or not args.output:
        parser.error("audio and --output are required unless --check is used")
    if not all(status[name] for name in ("funasr", "torch", "torchaudio")):
        print(json.dumps({"ready": False, "dependencies": status}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    audio = args.audio.expanduser().resolve()
    if not audio.is_file():
        parser.error(f"audio not found: {audio}")
    from funasr import AutoModel
    model_path = resolve_cached_model(args.model)
    vad_path = resolve_cached_model(args.vad_model)
    model = AutoModel(model=model_path, vad_model=vad_path, device=args.device, disable_update=True)
    if args.segments:
        scene_data = json.loads(args.segments.expanduser().resolve().read_text(encoding="utf-8"))
        scene_segments = scene_data.get("segments") or []
        result = []
        aligned_segments = []
        with tempfile.TemporaryDirectory(prefix="sensevoice-scenes-") as temp_dir:
            for item in scene_segments:
                start, end = float(item["start_seconds"]), float(item["end_seconds"])
                chunk = Path(temp_dir) / f"scene_{int(item.get('index', len(aligned_segments) + 1)):04d}.wav"
                write_wave_segment(audio, chunk, start, end)
                chunk_result = model.generate(input=str(chunk), language=args.language, use_itn=True, batch_size_s=300)
                result.extend(chunk_result)
                raw_text = chunk_result[0].get("text", "") if chunk_result else ""
                aligned_segments.append({
                    "start_ms": round(start * 1000),
                    "end_ms": round(end * 1000),
                    "text": clean_text(raw_text),
                })
        segments = aligned_segments
        full_text = "".join(item["text"] for item in segments)
    else:
        result = model.generate(input=str(audio), language=args.language, use_itn=True, batch_size_s=300)
        first = result[0] if result else {}
        segments = []
        for item in first.get("sentence_info") or []:
            segments.append({
                "start_ms": item.get("start"),
                "end_ms": item.get("end"),
                "text": clean_text(item.get("text", "")),
            })
        full_text = clean_text(first.get("text", ""))
        if not segments and full_text:
            segments.append({"start_ms": None, "end_ms": None, "text": full_text})
    payload = {
        "engine": "FunASR", "model": args.model, "vad_model": args.vad_model,
        "device": args.device, "language": args.language, "use_itn": True,
        "text": full_text, "segments": segments, "raw": serializable(result),
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "segments": len(segments)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
