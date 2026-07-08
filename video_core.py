from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import imageio_ffmpeg


ProgressCallback = Callable[[int], None]
LogCallback = Callable[[str], None]


PRESETS = (
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
)

VIDEO_CODECS = ("libx264", "libx265")


@dataclass(frozen=True)
class VideoJob:
    operation: str
    input_path: Path
    output_path: Path

    crf: int = 24
    preset: str = "medium"
    codec: str = "libx264"

    width: int | None = None
    height: int | None = None
    fps: int | None = None

    start: str | None = None
    end: str | None = None
    duration: str | None = None

    crop_x: int = 0
    crop_y: int = 0
    crop_w: int | None = None
    crop_h: int | None = None

    audio_bitrate: str = "128k"
    no_audio: bool = False
    copy_mode: bool = False
    overwrite: bool = True


class VideoError(RuntimeError):
    pass


def get_ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def format_command(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in cmd)


def parse_time_to_seconds(value: str | None) -> float | None:
    if value is None:
        return None

    raw = value.strip()
    if not raw:
        return None

    parts = raw.split(":")

    try:
        if len(parts) == 1:
            seconds = float(parts[0])
        elif len(parts) == 2:
            seconds = int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        else:
            raise ValueError
    except ValueError as exc:
        raise VideoError(f"Некоректний час: {value}") from exc

    if seconds < 0:
        raise VideoError("Час не може бути від’ємним")

    return seconds


def seconds_to_ffmpeg_time(seconds: float) -> str:
    return f"{seconds:.3f}"


def parse_duration_from_text(text: str) -> float:
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)

    if not match:
        return 0.0

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))

    return hours * 3600 + minutes * 60 + seconds


def parse_progress_time(line: str) -> float | None:
    match = re.search(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", line)

    if not match:
        return None

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))

    return hours * 3600 + minutes * 60 + seconds


def probe_duration(input_path: Path) -> float:
    cmd = [
        get_ffmpeg(),
        "-hide_banner",
        "-i",
        str(input_path),
    ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        shell=False,
    )

    return parse_duration_from_text(proc.stderr or proc.stdout)


def add_faststart(args: list[str], output_path: Path) -> None:
    if output_path.suffix.lower() in {".mp4", ".m4v", ".mov"}:
        args.extend(["-movflags", "+faststart"])


def build_video_filters(
    *,
    width: int | None = None,
    height: int | None = None,
    fps: int | None = None,
    crop_x: int = 0,
    crop_y: int = 0,
    crop_w: int | None = None,
    crop_h: int | None = None,
    include_crop: bool = False,
    include_fps: bool = True,
) -> list[str]:
    filters: list[str] = []

    if include_crop and crop_w and crop_h:
        filters.append(f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}")

    if width and height:
        filters.append(f"scale={width}:{height}")
    elif width:
        filters.append(f"scale={width}:-2")
    elif height:
        filters.append(f"scale=-2:{height}")

    if include_fps and fps:
        filters.append(f"fps={fps}")

    return filters


def audio_codec_args(output_path: Path, bitrate: str) -> list[str]:
    suffix = output_path.suffix.lower()

    if suffix == ".wav":
        return ["-c:a", "pcm_s16le"]

    if suffix in {".m4a", ".aac"}:
        return ["-c:a", "aac", "-b:a", bitrate]

    return ["-c:a", "libmp3lame", "-b:a", bitrate]


def normalize_job(job: VideoJob) -> VideoJob:
    return VideoJob(
        operation=job.operation,
        input_path=job.input_path.expanduser().resolve(),
        output_path=job.output_path.expanduser().resolve(),
        crf=job.crf,
        preset=job.preset,
        codec=job.codec,
        width=job.width,
        height=job.height,
        fps=job.fps,
        start=job.start,
        end=job.end,
        duration=job.duration,
        crop_x=job.crop_x,
        crop_y=job.crop_y,
        crop_w=job.crop_w,
        crop_h=job.crop_h,
        audio_bitrate=job.audio_bitrate,
        no_audio=job.no_audio,
        copy_mode=job.copy_mode,
        overwrite=job.overwrite,
    )


def validate_job(job: VideoJob) -> VideoJob:
    job = normalize_job(job)

    if not job.input_path.is_file():
        raise VideoError(f"Вхідний файл не знайдено: {job.input_path}")

    if job.input_path == job.output_path:
        raise VideoError("Вхідний і вихідний файл не можуть бути однаковими")

    if job.operation not in {
        "compress",
        "trim",
        "resize",
        "crop",
        "convert",
        "extract_audio",
        "mute",
        "thumbnail",
    }:
        raise VideoError(f"Невідома операція: {job.operation}")

    if not 0 <= job.crf <= 51:
        raise VideoError("CRF має бути від 0 до 51")

    if job.codec not in VIDEO_CODECS:
        raise VideoError(f"Непідтримуваний кодек: {job.codec}")

    if job.preset not in PRESETS:
        raise VideoError(f"Непідтримуваний preset: {job.preset}")

    if job.width is not None and job.width <= 0:
        raise VideoError("Width має бути більше 0")

    if job.height is not None and job.height <= 0:
        raise VideoError("Height має бути більше 0")

    if job.fps is not None and job.fps <= 0:
        raise VideoError("FPS має бути більше 0")

    if job.crop_x < 0 or job.crop_y < 0:
        raise VideoError("Crop X/Y не можуть бути від’ємними")

    if job.crop_w is not None and job.crop_w <= 0:
        raise VideoError("Crop W має бути більше 0")

    if job.crop_h is not None and job.crop_h <= 0:
        raise VideoError("Crop H має бути більше 0")

    if not re.fullmatch(r"\d+[kKmM]?", job.audio_bitrate.strip()):
        raise VideoError("Audio bitrate має бути типу 128k, 192k, 1M")

    parse_time_to_seconds(job.start)
    parse_time_to_seconds(job.end)
    parse_time_to_seconds(job.duration)

    if job.operation == "resize":
        if job.width is None and job.height is None and job.fps is None:
            raise VideoError("Resize потребує Width, Height або FPS")

    if job.operation == "crop":
        if job.crop_w is None or job.crop_h is None:
            raise VideoError("Crop потребує Crop W і Crop H")

    if job.operation == "trim":
        start = parse_time_to_seconds(job.start) or 0.0
        end = parse_time_to_seconds(job.end)
        duration = parse_time_to_seconds(job.duration)

        if end is not None and duration is not None:
            raise VideoError("Використовуй або End, або Duration, не обидва разом")

        if end is not None and end <= start:
            raise VideoError("End має бути більшим за Start")

        if duration is not None and duration <= 0:
            raise VideoError("Duration має бути більше 0")

    if job.operation == "extract_audio":
        suffix = job.output_path.suffix.lower()
        if suffix not in {".mp3", ".m4a", ".aac", ".wav"}:
            raise VideoError("Для аудіо вихід має бути .mp3, .m4a, .aac або .wav")

    if job.operation == "thumbnail":
        suffix = job.output_path.suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise VideoError("Для кадру вихід має бути .jpg, .png або .webp")

    if job.copy_mode and job.operation not in {"trim", "convert"}:
        raise VideoError("Copy mode доступний тільки для trim і convert")

    job.output_path.parent.mkdir(parents=True, exist_ok=True)

    if job.output_path.exists() and not job.overwrite:
        raise VideoError("Вихідний файл уже існує")

    return job


def build_command(job: VideoJob) -> list[str]:
    job = validate_job(job)

    base = [
        get_ffmpeg(),
        "-hide_banner",
        "-y" if job.overwrite else "-n",
    ]

    if job.operation == "compress":
        args = [
            "-i",
            str(job.input_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
        ]

        filters = build_video_filters(
            width=job.width,
            height=job.height,
            fps=job.fps,
            include_fps=True,
        )

        if filters:
            args.extend(["-vf", ",".join(filters)])

        args.extend(
            [
                "-c:v",
                job.codec,
                "-preset",
                job.preset,
                "-crf",
                str(job.crf),
                "-pix_fmt",
                "yuv420p",
            ]
        )

        if job.no_audio:
            args.append("-an")
        else:
            args.extend(["-c:a", "aac", "-b:a", job.audio_bitrate])

        add_faststart(args, job.output_path)
        args.append(str(job.output_path))
        return base + args

    if job.operation == "trim":
        start = parse_time_to_seconds(job.start) or 0.0
        end = parse_time_to_seconds(job.end)
        duration = parse_time_to_seconds(job.duration)

        if end is not None:
            duration = end - start

        args: list[str] = []

        if job.copy_mode:
            args.extend(["-ss", seconds_to_ffmpeg_time(start), "-i", str(job.input_path)])

            if duration is not None:
                args.extend(["-t", seconds_to_ffmpeg_time(duration)])

            args.extend(["-map", "0", "-c", "copy", "-avoid_negative_ts", "make_zero"])
        else:
            args.extend(["-i", str(job.input_path), "-ss", seconds_to_ffmpeg_time(start)])

            if duration is not None:
                args.extend(["-t", seconds_to_ffmpeg_time(duration)])

            args.extend(
                [
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                    "-c:v",
                    job.codec,
                    "-preset",
                    job.preset,
                    "-crf",
                    str(job.crf),
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    job.audio_bitrate,
                ]
            )

        add_faststart(args, job.output_path)
        args.append(str(job.output_path))
        return base + args

    if job.operation == "resize":
        filters = build_video_filters(
            width=job.width,
            height=job.height,
            fps=job.fps,
            include_fps=True,
        )

        args = [
            "-i",
            str(job.input_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            ",".join(filters),
            "-c:v",
            job.codec,
            "-preset",
            job.preset,
            "-crf",
            str(job.crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            job.audio_bitrate,
        ]

        add_faststart(args, job.output_path)
        args.append(str(job.output_path))
        return base + args

    if job.operation == "crop":
        filters = build_video_filters(
            width=job.width,
            height=job.height,
            crop_x=job.crop_x,
            crop_y=job.crop_y,
            crop_w=job.crop_w,
            crop_h=job.crop_h,
            include_crop=True,
            include_fps=False,
        )

        args = [
            "-i",
            str(job.input_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            ",".join(filters),
            "-c:v",
            job.codec,
            "-preset",
            job.preset,
            "-crf",
            str(job.crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            job.audio_bitrate,
        ]

        add_faststart(args, job.output_path)
        args.append(str(job.output_path))
        return base + args

    if job.operation == "convert":
        args = [
            "-i",
            str(job.input_path),
            "-map",
            "0",
        ]

        if job.copy_mode:
            args.extend(["-c", "copy"])
        else:
            args.extend(
                [
                    "-c:v",
                    job.codec,
                    "-preset",
                    job.preset,
                    "-crf",
                    str(job.crf),
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    job.audio_bitrate,
                ]
            )

        add_faststart(args, job.output_path)
        args.append(str(job.output_path))
        return base + args

    if job.operation == "extract_audio":
        args = []

        start = parse_time_to_seconds(job.start)
        duration = parse_time_to_seconds(job.duration)

        if start is not None:
            args.extend(["-ss", seconds_to_ffmpeg_time(start)])

        args.extend(["-i", str(job.input_path)])

        if duration is not None:
            args.extend(["-t", seconds_to_ffmpeg_time(duration)])

        args.extend(["-vn", *audio_codec_args(job.output_path, job.audio_bitrate)])
        args.append(str(job.output_path))
        return base + args

    if job.operation == "mute":
        args = [
            "-i",
            str(job.input_path),
            "-map",
            "0:v:0",
            "-c:v",
            "copy",
            "-an",
        ]

        add_faststart(args, job.output_path)
        args.append(str(job.output_path))
        return base + args

    if job.operation == "thumbnail":
        start = parse_time_to_seconds(job.start) or 0.0

        return base + [
            "-ss",
            seconds_to_ffmpeg_time(start),
            "-i",
            str(job.input_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(job.output_path),
        ]

    raise VideoError(f"Невідома операція: {job.operation}")


def build_preview_command(job: VideoJob, preview_path: Path, preview_time: str | None = None) -> list[str]:
    job = normalize_job(job)

    if not job.input_path.is_file():
        raise VideoError("Вибери коректний вхідний файл для прев’ю")

    time_value = preview_time or job.start or "0"
    start = parse_time_to_seconds(time_value) or 0.0

    filters: list[str] = []

    if job.operation == "crop":
        filters.extend(
            build_video_filters(
                width=job.width,
                height=job.height,
                crop_x=job.crop_x,
                crop_y=job.crop_y,
                crop_w=job.crop_w,
                crop_h=job.crop_h,
                include_crop=True,
                include_fps=False,
            )
        )
    elif job.operation in {"compress", "resize"}:
        filters.extend(
            build_video_filters(
                width=job.width,
                height=job.height,
                include_fps=False,
            )
        )

    args = [
        get_ffmpeg(),
        "-hide_banner",
        "-y",
        "-ss",
        seconds_to_ffmpeg_time(start),
        "-i",
        str(job.input_path),
    ]

    if filters:
        args.extend(["-vf", ",".join(filters)])

    args.extend(
        [
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(preview_path),
        ]
    )

    return args


def render_preview_frame(job: VideoJob, preview_path: Path, preview_time: str | None = None) -> None:
    cmd = build_preview_command(job, preview_path, preview_time)

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        shell=False,
    )

    if proc.returncode != 0:
        raise VideoError(proc.stderr.strip() or "Не вдалося створити прев’ю")


class VideoRunner:
    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

        if self._process and self._process.poll() is None:
            self._process.terminate()

    def run(
        self,
        job: VideoJob,
        *,
        on_progress: ProgressCallback | None = None,
        on_log: LogCallback | None = None,
    ) -> None:
        job = validate_job(job)
        duration = probe_duration(job.input_path)
        cmd = build_command(job)

        if on_log:
            on_log("Command:")
            on_log(format_command(cmd))
            on_log("")

        self._cancelled = False

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )

        assert self._process.stderr is not None

        last_progress = -1

        for line in self._process.stderr:
            line = line.rstrip()

            if on_log and line:
                on_log(line)

            if duration > 0 and on_progress:
                current = parse_progress_time(line)

                if current is not None:
                    progress = int(min(100, max(0, current / duration * 100)))

                    if progress != last_progress:
                        last_progress = progress
                        on_progress(progress)

        code = self._process.wait()

        if self._cancelled:
            raise VideoError("Операцію скасовано")

        if code != 0:
            raise VideoError(f"FFmpeg завершився з кодом {code}")

        if on_progress:
            on_progress(100)

        if on_log:
            on_log("")
            on_log(f"Saved: {job.output_path}")