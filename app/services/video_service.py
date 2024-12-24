import os
import subprocess
import base64
from typing import List, Dict, Optional
import tempfile
import requests
from PIL import Image
import io
import hashlib
from openai import OpenAI
from ..core.config import get_settings
from ..core.redis_client import Cache

settings = get_settings()

class VideoProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.temp_dir = tempfile.mkdtemp()
        self.cache = Cache()

    def _cleanup(self, *files):
        """Clean up temporary files"""
        for file in files:
            try:
                if file and os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                print(f"Error removing file {file}: {e}")
        try:
            if os.path.exists(self.temp_dir):
                os.rmdir(self.temp_dir)
        except Exception as e:
            print(f"Error removing temp dir {self.temp_dir}: {e}")

    def _validate_video(self, url: str) -> tuple[bool, str]:
        """Validate video before downloading"""
        try:
            # Send HEAD request to get content info
            response = requests.head(url, timeout=settings.REQUEST_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(format in content_type for format in settings.ALLOWED_VIDEO_FORMATS):
                return False, f"Invalid video format. Allowed formats: {', '.join(settings.ALLOWED_VIDEO_FORMATS)}"
            
            # Check file size
            content_length = int(response.headers.get('content-length', 0))
            if content_length > settings.MAX_VIDEO_SIZE:
                return False, f"Video size ({content_length / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({settings.MAX_VIDEO_SIZE / 1024 / 1024:.1f}MB)"
            
            return True, ""
        except requests.RequestException as e:
            return False, f"Error validating video: {str(e)}"

    def _download_video(self, video_url: str) -> str:
        """Download video and return path"""
        # Validate video first
        is_valid, error_message = self._validate_video(video_url)
        if not is_valid:
            raise ValueError(error_message)
            
        video_path = os.path.join(self.temp_dir, 'video.mp4')
        
        # Download with progress tracking and timeout
        with requests.get(video_url, stream=True, timeout=settings.REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded_size = 0
            
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        downloaded_size += len(chunk)
                        f.write(chunk)
                        # Check size during download
                        if downloaded_size > settings.MAX_VIDEO_SIZE:
                            os.remove(video_path)
                            raise ValueError(f"Video size exceeds maximum allowed size ({settings.MAX_VIDEO_SIZE / 1024 / 1024:.1f}MB)")
                            
        return video_path

    def _get_ffmpeg_path(self) -> tuple[str, str]:
        """Get ffmpeg and ffprobe paths"""
        # Try common locations
        common_paths = [
            '/usr/bin/',
            '/usr/local/bin/',
            '/opt/homebrew/bin/',
            '/usr/local/opt/ffmpeg/bin/'
        ]
        
        ffmpeg_path = None
        ffprobe_path = None
        
        # First try PATH
        try:
            ffmpeg_path = subprocess.check_output(['which', 'ffmpeg']).decode().strip()
            ffprobe_path = subprocess.check_output(['which', 'ffprobe']).decode().strip()
            return ffmpeg_path, ffprobe_path
        except:
            # Then try common locations
            for path in common_paths:
                if os.path.exists(os.path.join(path, 'ffmpeg')):
                    ffmpeg_path = os.path.join(path, 'ffmpeg')
                if os.path.exists(os.path.join(path, 'ffprobe')):
                    ffprobe_path = os.path.join(path, 'ffprobe')
                if ffmpeg_path and ffprobe_path:
                    return ffmpeg_path, ffprobe_path
            
            raise Exception("FFmpeg/FFprobe not found. Please install FFmpeg.")

    def _extract_frames(self, video_path: str, max_frames: int = 8, ffmpeg_path: str = 'ffmpeg') -> List[str]:
        """Extract frames and return list of base64 encoded images"""
        # Get video duration
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        duration = float(subprocess.check_output(duration_cmd).decode('utf-8').strip())
        
        # Calculate frame interval
        if duration <= 30:
            interval = 5
        elif duration <= 60:
            interval = 10
        else:
            interval = 20
            
        # Calculate number of frames
        num_frames = min(max_frames, int(duration / interval))
        if num_frames == 0:
            num_frames = 1
            
        frames = []
        for i in range(num_frames):
            timestamp = i * interval
            if timestamp >= duration:
                break
                
            # Extract frame
            frame_path = os.path.join(self.temp_dir, f'frame_{i}.jpg')
            extract_cmd = [
                ffmpeg_path, '-ss', str(timestamp), '-i', video_path,
                '-vframes', '1', '-q:v', '2', frame_path
            ]
            subprocess.run(extract_cmd, check=True, capture_output=True)
            
            # Convert to base64
            with Image.open(frame_path) as img:
                # Resize if needed
                if img.size[0] > 800 or img.size[1] > 800:
                    img.thumbnail((800, 800))
                    
                # Convert to JPEG and optimize
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=70, optimize=True)
                img_str = base64.b64encode(buffer.getvalue()).decode()
                frames.append(img_str)
                
            # Cleanup frame
            os.remove(frame_path)
            
        return frames

    def _extract_audio(self, video_path: str, ffmpeg_path: str = 'ffmpeg') -> str:
        """Extract audio and return path"""
        audio_path = os.path.join(self.temp_dir, 'audio.mp3')
        extract_cmd = [
            ffmpeg_path, '-i', video_path, '-q:a', '0', '-map', 'a', audio_path
        ]
        subprocess.run(extract_cmd, check=True, capture_output=True)
        return audio_path

    def _get_transcription(self, audio_path: str) -> str:
        """Get audio transcription"""
        with open(audio_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"  # Явно вказуємо англійську мову
            )
        return transcription.text

    def _get_description(self, frames: List[str], transcription: str, system_prompt: Optional[str] = None) -> str:
        """Get video description using OpenAI"""
        if not system_prompt:
            system_prompt = """As a video Assistant, your goal is to describe a video with a focus on context that will be useful for bloggers, noting details that can be used as ideas for content: Plot, Key points, Atmosphere, Style, Visual look, Gestures, or anything else that could attract attention.

Also describe what exactly is happening in the video: The place depicted, the actions performed by people or objects, their interaction."""

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    "Here is the audio transcription from the video:",
                    transcription,
                    "And here are the frames from the video:",
                    *[{
                        "type": "image_url",
                        "image_url": {
                            "url": frame,
                            "detail": "low"
                        }
                    } for frame in frames]
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=2048
        )
        return response.choices[0].message.content

    def _get_cache_key(self, video_url: str, system_prompt: Optional[str] = None) -> str:
        """Generate unique cache key based on video URL and system prompt"""
        key_data = f"{video_url}:{system_prompt or ''}"
        return f"video_processing:{hashlib.md5(key_data.encode()).hexdigest()}"

    def process_video(self, video_url: str, system_prompt: Optional[str] = None) -> Dict:
        """Process video and return results"""
        video_path = None
        audio_path = None
        
        try:
            # Get FFmpeg paths
            ffmpeg_path, ffprobe_path = self._get_ffmpeg_path()
            
            # Validate video first
            is_valid, error = self._validate_video(video_url)
            if not is_valid:
                return {
                    'status': 'error',
                    'message': error
                }

            # Check cache first
            if settings.CACHE_ENABLED:
                cache_key = self._get_cache_key(video_url, system_prompt)
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    return cached_result

            # Download video
            video_path = self._download_video(video_url)
            
            # Get video duration
            duration_cmd = [
                ffprobe_path, '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', video_path
            ]
            duration = float(subprocess.check_output(duration_cmd).decode('utf-8').strip())
            
            if duration < settings.MIN_DURATION:
                result = {
                    'status': 'error',
                    'message': f'Video duration ({duration:.1f}s) is less than minimum required duration ({settings.MIN_DURATION}s)'
                }
                return result

            # Extract frames and audio using full paths
            frames = self._extract_frames(video_path, settings.MAX_FRAMES, ffmpeg_path)
            audio_path = self._extract_audio(video_path, ffmpeg_path)
            
            # Get transcription
            transcription = self._get_transcription(audio_path)
            word_count = len(transcription.split())
            
            if word_count < settings.MIN_WORDS:
                result = {
                    'status': 'error',
                    'message': f'Transcription word count ({word_count}) is less than minimum required words ({settings.MIN_WORDS})'
                }
                return result
            
            # Get description
            description = self._get_description(frames, transcription, system_prompt)
            
            result = {
                'status': 'success',
                'transcription': transcription,
                'description': description,
                'word_count': word_count
            }

            # Cache successful results
            if settings.CACHE_ENABLED and result['status'] == 'success':
                cache_key = self._get_cache_key(video_url, system_prompt)
                self.cache.set(cache_key, result, settings.CACHE_EXPIRE_TIME)
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
        finally:
            # Cleanup temporary files if they exist
            try:
                if video_path:
                    self._cleanup(video_path)
                if audio_path:
                    self._cleanup(audio_path)
                if os.path.exists(self.temp_dir):
                    os.rmdir(self.temp_dir)
            except Exception as cleanup_error:
                print(f"Error during cleanup: {cleanup_error}")
