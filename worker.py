import subprocess
import shutil
import os
import logging
import requests
from celery import Celery
from database import SessionLocal
from models import BootcampMedia
from config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "video_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tehran",
)

HLS_QUALITIES = {
    '360p': {'height': 360, 'video_bitrate': '800k', 'maxrate': '856k', 'bufsize': '1200k', 'audio_bitrate': '128k'},
    '480p': {'height': 480, 'video_bitrate': '1400k', 'maxrate': '1498k', 'bufsize': '2100k', 'audio_bitrate': '128k'},
    '720p': {'height': 720, 'video_bitrate': '2800k', 'maxrate': '2996k', 'bufsize': '4200k', 'audio_bitrate': '192k'},
}

def get_video_duration(filepath):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(filepath)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except Exception:
        return None

def get_video_height(filepath):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=height', '-of', 'default=noprint_wrappers=1:nokey=1', str(filepath)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return int(result.stdout.strip())
    except Exception:
        return None

def build_hls_variants(input_path, output_dir, qualities):
    input_path = str(input_path)
    output_dir = str(output_dir)
    variants = []
    for quality_name, config in qualities.items():
        quality_dir = os.path.join(output_dir, quality_name)
        os.makedirs(quality_dir, exist_ok=True)
        playlist_path = os.path.join(quality_dir, f'{quality_name}.m3u8')
        segment_pattern = os.path.join(quality_dir, 'segment_%03d.ts')
        cmd = [
            'ffmpeg', '-y', '-i', input_path, '-vf', f'scale=-2:{config["height"]}',
            '-c:v', 'libx264', '-preset', 'fast', '-b:v', config['video_bitrate'],
            '-maxrate', config['maxrate'], '-bufsize', config['bufsize'],
            '-c:a', 'aac', '-b:a', config['audio_bitrate'], '-ac', '2',
            '-hls_time', '6', '-hls_playlist_type', 'vod',
            '-hls_segment_filename', segment_pattern, '-f', 'hls', playlist_path,
        ]
        logger.info(f'Running FFmpeg for {quality_name}: {" ".join(cmd)}')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error(f'FFmpeg failed for {quality_name}: {result.stderr}')
            raise RuntimeError(f'FFmpeg encoding failed for {quality_name}')
        variants.append((quality_name, playlist_path))
    return variants

def build_master_playlist(variants, output_dir):
    master_path = os.path.join(output_dir, 'master.m3u8')
    lines = ['#EXTM3U']
    for quality_name, playlist_path in variants:
        config = HLS_QUALITIES[quality_name]
        lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={int(config["video_bitrate"].rstrip("k")) * 1000},RESOLUTION=1280x{config["height"]},NAME="{quality_name}"')
        lines.append(f'{quality_name}/{quality_name}.m3u8')
    with open(master_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    return master_path



@celery_app.task(bind=True, max_retries=2)
def process_video_task(self, media_id):
    db = SessionLocal()
    try:
        media = db.query(BootcampMedia).filter(BootcampMedia.id == media_id).first()
        if not media:
            logger.error(f'BootcampMedia {media_id} not found')
            return
            
        media.status = "processing"
        db.commit()
        
        # Construct path correctly since media.file is relative to MEDIA_DIR, e.g., 'bootcamp/media/file.mp4'
        # On Windows, os.path.join handles both slashes correctly.
        input_path = os.path.join(settings.MEDIA_DIR, str(media.file))
        if not os.path.exists(input_path):
            raise ValueError(f"File not found: {input_path}")
            
        output_dir = os.path.join(settings.MEDIA_DIR, 'hls', str(media_id))
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        duration = get_video_duration(input_path)
        if duration is not None:
            media.duration = round(duration, 2)
            db.commit()
            
        source_height = get_video_height(input_path)
        if source_height is not None:
            active_qualities = {name: cfg for name, cfg in HLS_QUALITIES.items() if cfg['height'] <= source_height}
            if not active_qualities:
                active_qualities = {'360p': HLS_QUALITIES['360p']}
        else:
            active_qualities = HLS_QUALITIES
            
        variants = build_hls_variants(input_path, output_dir, active_qualities)
        build_master_playlist(variants, output_dir)
        
        media.hls_path = f'/media/hls/{media_id}'
        media.status = "ready"
        db.commit()

    except Exception as exc:
        logger.error(f'Video processing failed for {media_id}: {exc}')
        if 'media' in locals() and media:
            media.status = "failed"
            media.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
