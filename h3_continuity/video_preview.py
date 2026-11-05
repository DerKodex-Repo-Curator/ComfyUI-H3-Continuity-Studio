"""Cached phone-compatible playback copies; original sequence videos are never modified."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import threading

import av
import folder_paths
from comfy_api.latest._input_impl.video_types import video_stream_color_space

from . import nodes as continuity

LOCK = threading.Lock()


def _cache_path(source):
    stamp = source.stat()
    key = hashlib.sha256(f'1:{source}:{stamp.st_size}:{stamp.st_mtime_ns}'.encode()).hexdigest()
    return Path(folder_paths.get_temp_directory()) / 'h3c_video_previews' / f'{key}.mp4'


def preview(query):
    filename = query.get('filename', '')
    if query.get('type') != 'output' or not filename or '/' in filename or '\\' in filename:
        raise ValueError('Choose a saved sequence MP4.')
    root = (Path(folder_paths.get_output_directory()) / 'h3_sequences').resolve()
    source = (Path(folder_paths.get_output_directory()) / query.get('subfolder', '') / filename).resolve()
    if not source.is_relative_to(root) or source.suffix.lower() != '.mp4':
        raise ValueError('Choose a saved sequence MP4.')
    target = _cache_path(source)
    if target.is_file() and target.stat().st_size:
        return str(target)
    # Cached clips/ranges stay playable while one cold conversion runs.
    with LOCK:
        snapshot = temporary = None
        try:
            # Take changes use this lock; the long encoder must not hold their original file open on Windows.
            with continuity.SEQUENCE_LOCK:
                target = _cache_path(source)
                if target.is_file() and target.stat().st_size:
                    return str(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                snapshot, temporary = target.with_suffix('.source.mp4'), target.with_suffix('.tmp.mp4')
                shutil.copyfile(source, snapshot)
            with av.open(str(snapshot)) as container:
                if not container.streams.video:
                    raise ValueError('The saved MP4 has no video stream.')
                stream = container.streams.video[0]
                ratio = min(1, 720 / max(stream.width, stream.height))
                width, height = (max(2, int(size * ratio) // 2 * 2) for size in (stream.width, stream.height))
                hdr = video_stream_color_space(stream) in ('HDR', 'HDR PQ')
            executable = shutil.which('ffmpeg')
            if not executable:
                try:
                    import imageio_ffmpeg
                    executable = imageio_ffmpeg.get_ffmpeg_exe()
                except ImportError as error:
                    raise ValueError('Compatible video playback needs FFmpeg on PATH or imageio-ffmpeg.') from error
            filters = (f'zscale=w={width}:h={height}:transfer=linear:npl=100,format=gbrpf32le,'
                       'zscale=primaries=bt709,tonemap=mobius:desat=0,'
                       'zscale=transfer=bt709:matrix=bt709:range=limited' if hdr
                       else f'scale={width}:{height}:flags=lanczos')
            result = subprocess.run([executable, '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                '-threads', '2', '-filter_threads', '2', '-i', str(snapshot), '-map', '0:v:0', '-map', '0:a:0?', '-sn', '-dn',
                '-vf', filters + ',fps=24,format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast',
                '-crf', '23', '-profile:v', 'main', '-level:v', '3.1', '-threads', '2',
                '-colorspace', 'bt709', '-color_trc', 'bt709', '-color_primaries', 'bt709',
                '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-movflags', '+faststart', str(temporary)],
                capture_output=True, timeout=180, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode:
                raise ValueError('Compatible video preview failed: ' + result.stderr.decode(errors='replace')[-800:])
            os.replace(temporary, target)
        except subprocess.TimeoutExpired as error:
            raise ValueError('Compatible video preview took too long. Try a single clip.') from error
        finally:
            for path in (snapshot, temporary):
                if path is not None:
                    path.unlink(missing_ok=True)
        return str(target)
