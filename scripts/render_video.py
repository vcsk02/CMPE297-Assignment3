"""Render a narrated code-and-execution walkthrough with actual repository snippets.

Requires FFmpeg compiled with libflite and libx264. No network or paid TTS service.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "video"
BUILD = VIDEO / "build"


def run(argv):
    if argv[0] == "ffmpeg":
        argv = [argv[0], "-xerror", *argv[1:]]
    result = subprocess.run(argv, check=True, capture_output=True, text=True)
    if result.stderr.strip():
        raise RuntimeError(result.stderr[-4000:])


def font(size, mono=False):
    name = "DejaVuSansMono.ttf" if mono else "DejaVuSans.ttf"
    for path in [
        Path("/usr/share/fonts/truetype/dejavu") / name,
        Path("C:/Windows/Fonts/consola.ttf" if mono else "C:/Windows/Fonts/arial.ttf"),
    ]:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def scene_text(scene):
    if "file" in scene:
        lines = (ROOT / scene["file"]).read_text().splitlines()
        start = 0
        if "match" in scene:
            start = next(i for i, line in enumerate(lines) if scene["match"] in line)
        count = min(scene.get("count", 20), 23)
        shown = lines[start : start + count]
        return [f"{i + start + 1:3}  {line}" for i, line in enumerate(shown)]
    if "artifact" in scene:
        value = json.loads((ROOT / scene["artifact"]).read_text())
        for key in scene.get("selector", "").split("."):
            if key:
                value = value[key]
        lines = json.dumps(value, indent=2, ensure_ascii=False).splitlines()
        if len(lines) > 23:
            lines = lines[:22] + ["... full captured output in " + scene["artifact"]]
        return lines
    return scene["text"].splitlines()


def wrap(lines, draw, selected_font, width):
    result = []
    for line in lines:
        if not line:
            result.append("")
        while line:
            end = len(line)
            while end > 1 and draw.textlength(line[:end], font=selected_font) > width:
                end -= 1
            result.append(line[:end])
            line = "    " + line[end:] if end < len(line) else ""
    return result


def draw_scene(scene, index, total, path):
    picture = Image.new("RGB", (1280, 720), "#0b1120")
    draw = ImageDraw.Draw(picture)
    draw.rectangle((0, 0, 1280, 8), fill="#38bdf8")
    draw.text((54, 32), "ADK / AGENT ENGINEERING LAB", font=font(18), fill="#7dd3fc")
    draw.text((54, 72), scene["title"], font=font(34), fill="#f8fafc")
    draw.text((56, 124), scene["subtitle"], font=font(18), fill="#94a3b8")
    draw.rounded_rectangle((50, 172, 1230, 632), radius=16, fill="#131e33", outline="#263952")
    for i, color in enumerate(["#fb7185", "#fbbf24", "#34d399"]):
        draw.ellipse((72 + i * 22, 190, 82 + i * 22, 200), fill=color)
    label = scene.get("file", scene.get("artifact", "terminal / architecture"))
    draw.text((160, 184), label, font=font(15, True), fill="#94a3b8")
    body_font = font(17 if "file" in scene or "artifact" in scene else 21, True)
    lines = wrap(scene_text(scene), draw, body_font, 1118)
    if len(lines) > 23:
        lines = lines[:22] + ["... see the complete file in the repository"]
    line_step = 17 if "file" in scene or "artifact" in scene else 27
    for i, line in enumerate(lines):
        color = "#a7f3d0" if line.lstrip().startswith(("$", "uv ", "24 passed")) else "#dbeafe"
        draw.text((74, 220 + i * line_step), line, font=body_font, fill=color)
    draw.text(
        (54, 656),
        "Actual code + captured demo evidence  |  Synthetic narration",
        font=font(16),
        fill="#94a3b8",
    )
    draw.text((1115, 656), f"{index:02}/{total:02}", font=font(18, True), fill="#7dd3fc")
    picture.save(path)


def timestamp(seconds, milliseconds=False):
    total = int(round(seconds * 1000))
    hours, rem = divmod(total, 3600000)
    minutes, rem = divmod(rem, 60000)
    secs, millis = divmod(rem, 1000)
    return (
        f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
        if milliseconds
        else (f"{hours}:{minutes:02}:{secs:02}" if hours else f"{minutes:02}:{secs:02}")
    )


def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and FFprobe are required")
    BUILD.mkdir(exist_ok=True)
    scenes = json.loads((VIDEO / "scenes.json").read_text())
    transcript, captions, chapters, segments, cursor, caption_id = [], [], [], [], 0.0, 1
    for index, scene in enumerate(scenes, 1):
        stem = BUILD / f"{index:02}"
        text_file, wav, png, mp4 = [
            stem.with_suffix(suffix) for suffix in (".txt", ".wav", ".png", ".mp4")
        ]
        text_file.write_text(scene["narration"], encoding="utf-8")
        draw_scene(scene, index, len(scenes), png)
        run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"flite=textfile='{text_file}':voice=slt",
                "-af",
                "apad=pad_dur=0.5",
                "-ar",
                "24000",
                str(wav),
            ]
        )
        duration = float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    str(wav),
                ],
                text=True,
            )
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-loop",
                "1",
                "-framerate",
                "2",
                "-i",
                str(png),
                "-i",
                str(wav),
                "-t",
                str(duration),
                "-c:v",
                "libx264",
                "-threads",
                "2",
                "-preset",
                "veryfast",
                "-tune",
                "stillimage",
                "-crf",
                "25",
                "-r",
                "10",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                "-movflags",
                "+faststart",
                str(mp4),
            ]
        )
        actual = float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    str(mp4),
                ],
                text=True,
            )
        )
        if abs(actual - duration) > 0.25:
            raise RuntimeError(f"Scene {index} duration mismatch: {actual} vs {duration}")
        segments.append(mp4)
        if scene.get("chapter"):
            chapters.append(f"{timestamp(cursor)} {scene['chapter']}")
        transcript.append(f"## {timestamp(cursor)} — {scene['title']}\n\n{scene['narration']}\n")
        sentences = re.split(r"(?<=[.!?])\s+", scene["narration"])
        weight = sum(len(sentence) for sentence in sentences)
        position = cursor
        for sentence in sentences:
            end = position + (duration - 0.5) * len(sentence) / weight
            captions.append(
                f"{caption_id}\n{timestamp(position, True)} --> {timestamp(end, True)}\n{sentence}\n"
            )
            caption_id += 1
            position = end
        cursor += actual
        print(f"Scene {index:02}/{len(scenes)}: {duration:.1f}s — {scene['title']}", flush=True)
    concat = BUILD / "concat.txt"
    concat.write_text("\n".join(f"file '{p}'" for p in segments))
    destination = VIDEO / "adk-agent-suite-walkthrough.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-af",
            "aresample=async=1:first_pts=0",
            "-b:a",
            "64k",
            "-movflags",
            "+faststart",
            str(destination),
        ]
    )
    final_duration = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(destination),
            ],
            text=True,
        )
    )
    if abs(final_duration - cursor) > 1:
        raise RuntimeError(f"Final video duration mismatch: {final_duration} vs {cursor}")
    (VIDEO / "walkthrough.srt").write_text("\n".join(captions))
    (VIDEO / "TRANSCRIPT.md").write_text(
        "# Narrated walkthrough transcript\n\n" + "\n".join(transcript)
    )
    (VIDEO / "CHAPTERS.md").write_text("# YouTube chapters\n\n" + "\n".join(chapters) + "\n")
    metadata = {
        "title": "Five End-to-End Google ADK Agents | Code, MCP, Gemini CLI, Review and Commerce",
        "description": "A detailed original implementation of five ADK agents. "
        "Includes code walkthroughs and actual offline execution evidence. Demo model replies "
        "are scripted fixtures; MCP, ADK, SQL and code checks execute for real. "
        "Synthetic narration. Live Gemini and hosted deployments are not demonstrated.\n\n"
        + "\n".join(chapters)
        + "\n\nSource: add your actual GitHub repository URL after publication.",
        "tags": ["Google ADK", "MCP", "Gemini CLI", "AI agents", "code review", "ecommerce"],
        "duration_seconds": round(cursor, 3),
        "synthetic_narration": True,
    }
    (VIDEO / "youtube-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    shutil.copyfile(BUILD / "01.png", VIDEO / "thumbnail.png")
    print(
        f"Rendered {destination.name}: {timestamp(cursor)}, {destination.stat().st_size / 1048576:.1f} MiB"
    )


if __name__ == "__main__":
    main()
