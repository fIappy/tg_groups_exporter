import os
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from tqdm import tqdm
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
    DocumentAttributeSticker,
    DocumentAttributeFilename,
    DocumentAttributeImageSize,
    MessageMediaWebPage
)
from telethon import utils as telethon_utils
from telethon.errors import FloodWaitError

from config import config
from utils import logger, format_size, sanitize_filename

class MediaHandler:
    def __init__(self, client, base_output_dir: str):
        self.client = client
        self.base_output_dir = base_output_dir
        self.max_size = config.MAX_MEDIA_SIZE_MB * 1024 * 1024
        self.allowed_types = config.MEDIA_TYPES_TO_DOWNLOAD

    def _get_media_info(self, message) -> Tuple[str, str, int, int, int]:
        """Returns: media_type, ext, size, width, height, duration"""
        media = message.media
        if not media:
            return "no_media", "", 0, 0, 0, 0
        
        media_type = "unknown"
        ext = ""
        size = 0
        width = 0
        height = 0
        duration = 0
        
        if isinstance(media, MessageMediaPhoto):
            media_type = "photo"
            ext = ".jpg"
            if hasattr(media, 'photo') and media.photo:
                # Find largest size
                for s in media.photo.sizes:
                    if hasattr(s, 'size'):
                        size = max(size, s.size)
                    if hasattr(s, 'w') and hasattr(s, 'h'):
                        width = max(width, s.w)
                        height = max(height, s.h)

        elif isinstance(media, MessageMediaDocument):
            doc = media.document
            if not doc:
                return "unknown", "", 0, 0, 0, 0
            
            size = doc.size
            ext = telethon_utils.get_extension(media) or ""
            
            # Determine specific document type from attributes
            is_video = False
            is_audio = False
            is_voice = False
            is_sticker = False
            
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeVideo):
                    is_video = True
                    duration = attr.duration
                    width = attr.w
                    height = attr.h
                elif isinstance(attr, DocumentAttributeAudio):
                    is_audio = True
                    duration = attr.duration
                    if attr.voice:
                        is_voice = True
                elif isinstance(attr, DocumentAttributeSticker):
                    is_sticker = True
                elif isinstance(attr, DocumentAttributeImageSize):
                    width = attr.w
                    height = attr.h
            
            if is_video:
                media_type = "video"
            elif is_voice:
                media_type = "voice"
            elif is_audio:
                media_type = "audio"
            elif is_sticker:
                media_type = "sticker"
            else:
                media_type = "document"

        elif isinstance(media, MessageMediaWebPage):
            return "webpage", "", 0, 0, 0, 0
            
        return media_type, ext, size, width, height, duration

    def get_media_metadata(self, message) -> Dict[str, Any]:
        if not message.media:
            return {"media_download_status": "no_media"}
            
        m_type, ext, size, w, h, dur = self._get_media_info(message)
        
        if m_type == "webpage":
            wp = message.media.webpage
            if hasattr(wp, 'url'):
                return {
                    "media_type": "webpage",
                    "webpage_url": getattr(wp, 'url', ''),
                    "webpage_title": getattr(wp, 'title', ''),
                    "webpage_description": getattr(wp, 'description', ''),
                    "media_download_status": "no_media"
                }
            return {"media_download_status": "no_media"}

        # Original filename for documents
        file_name = f"{m_type}_{message.id}{ext}"
        if isinstance(message.media, MessageMediaDocument):
            for attr in message.media.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    safe_name = sanitize_filename(attr.file_name)
                    if safe_name:
                        file_name = f"file_{message.id}_{safe_name}"
                        break
        
        mime_type = ""
        if isinstance(message.media, MessageMediaDocument):
            mime_type = message.media.document.mime_type
            
        meta = {
            "media_type": m_type,
            "media_file_name": file_name,
            "media_file_size_bytes": size,
            "media_file_size_readable": format_size(size),
            "media_mime_type": mime_type,
            "media_width": w,
            "media_height": h,
            "media_duration_seconds": dur,
        }
        
        # Sticker emoji
        if m_type == "sticker" and isinstance(message.media, MessageMediaDocument):
            for attr in message.media.document.attributes:
                if isinstance(attr, DocumentAttributeSticker):
                    meta["sticker_emoji"] = attr.alt
                    break
                    
        return meta

    async def download_media(self, message, group_dir: str, message_date: datetime, pbar_manager=None) -> Dict[str, str]:
        if not config.DOWNLOAD_MEDIA or not message.media:
            return {"media_download_status": "no_media"}
            
        meta = self.get_media_metadata(message)
        m_type = meta.get("media_type")
        
        if m_type == "webpage" or m_type == "unknown" or m_type == "no_media":
            return {"media_download_status": "no_media"}
            
        if m_type not in self.allowed_types:
            return {"media_download_status": "skipped_type"}
            
        # Check if we should only download video cover
        is_video_cover_only = False
        if m_type == "video" and getattr(config, "VIDEO_COVER_ONLY", False):
            is_video_cover_only = True
            
        size = meta.get("media_file_size_bytes", 0)
        # Skip size check for video covers since thumbnails are small
        if size > self.max_size and not is_video_cover_only:
            return {"media_download_status": "skipped_too_large"}
            
        # Determine path: media/YYYY-MM/filename
        date_str = message_date.strftime("%Y-%m")
        relative_dir = os.path.join("media", date_str)
        absolute_dir = os.path.join(group_dir, relative_dir)
        os.makedirs(absolute_dir, exist_ok=True)
        
        file_name = meta["media_file_name"]
        
        if is_video_cover_only:
            # Change extension to .jpg for the thumbnail
            base_name = os.path.splitext(file_name)[0]
            file_name = f"{base_name}_cover.jpg"
            meta["media_file_name"] = file_name # update the meta so other parts know
            
        relative_path = os.path.join(relative_dir, file_name).replace("\\", "/")
        absolute_path = os.path.join(absolute_dir, file_name)
        
        # Check if already downloaded
        if os.path.exists(absolute_path) and os.path.getsize(absolute_path) > 0:
            return {
                "media_file_name": file_name,
                "media_local_path": relative_path,
                "media_download_status": "downloaded"
            }
            
        # Download
        try:
            if is_video_cover_only:
                logger.info(f"Downloading video cover: {file_name}")
            else:
                logger.info(f"Downloading media: {file_name} ({format_size(size)})")
            # We could add a simple progress bar or rely on general progress
            # We can use telethon's download_media
            await asyncio.sleep(0.5) # Anti-ban delay
            
            if pbar_manager is not None and not is_video_cover_only:
                pbar = tqdm(total=size, desc=f"DL {file_name[:20]}", leave=False, unit='B', unit_scale=True)
                def prog_callback(current, total):
                    pbar.n = current
                    pbar.refresh()
            else:
                prog_callback = None
                pbar = None
                
            # For downloading thumbnails, Telethon accepts an integer index, or -1 for the largest thumb.
            # If thumb=True is passed, it often downloads the smallest 'stripped' thumbnail which might be a blurry black box.
            # Passing thumb=-1 ensures we get the highest quality thumbnail available.
            kwargs = {"progress_callback": prog_callback}
            if is_video_cover_only:
                kwargs["thumb"] = -1
                
            await self.client.download_media(
                message, 
                file=absolute_path, 
                **kwargs
            )
            
            if pbar is not None:
                pbar.close()
                
            logger.info(f"Successfully downloaded: {file_name}")
            return {
                "media_file_name": file_name,
                "media_local_path": relative_path,
                "media_download_status": "downloaded"
            }
        except FloodWaitError as e:
            logger.warning(f"FloodWaitError: sleeping for {e.seconds} seconds")
            if pbar_manager is not None: pbar.close()
            await asyncio.sleep(e.seconds + 5)
            return {"media_download_status": "failed"}
        except Exception as e:
            logger.error(f"Error downloading media for msg {message.id}: {e}")
            if pbar_manager is not None: pbar.close()
            return {"media_download_status": "failed"}
