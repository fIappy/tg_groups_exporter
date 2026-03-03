import os
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import html

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tg_exporter")

def setup_file_logger(filepath: str):
    file_handler = logging.FileHandler(filepath, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.isoformat()

def get_local_datetime(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    # Convert to +8 Timezone
    tz = timezone(timedelta(hours=8))
    local_dt = dt.astimezone(tz)
    return local_dt.strftime('%Y-%m-%d %H:%M:%S')

def format_size(size_bytes: Optional[int]) -> Optional[str]:
    if not size_bytes:
        return None
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def sanitize_filename(filename: str) -> str:
    if not filename:
        return ""
    keepcharacters = (' ', '.', '_', '-')
    return "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()

def get_message_html(text: str, entities: List[Any]) -> str:
    """Reconstruct HTML text from plain text and entities.
    A simplified version. In reality, handling nested entities is complex.
    We just escape HTML and provide a basic wrapper for now if doing it manually,
    or we can rely on basic replacements.
    """
    if not text:
        return ""
    if not entities:
        return html.escape(text).replace("\\n", "<br>")
    
    # Very basic HTML reconstruction using telethon's entities
    # A complete implementation would map entities to tags and insert them from right to left
    res = list(text)
    # Sort entities by offset in reverse to insert tags without messing up previous offsets
    for ent in sorted(entities, key=lambda e: getattr(e, 'offset', 0), reverse=True):
        offset = getattr(ent, 'offset', None)
        length = getattr(ent, 'length', None)
        if offset is None or length is None:
            continue
        
        ent_type = type(ent).__name__
        start_tag = ""
        end_tag = ""
        
        if ent_type == 'MessageEntityBold':
            start_tag, end_tag = "<b>", "</b>"
        elif ent_type == 'MessageEntityItalic':
            start_tag, end_tag = "<i>", "</i>"
        elif ent_type == 'MessageEntityCode':
            start_tag, end_tag = "<code>", "</code>"
        elif ent_type == 'MessageEntityPre':
            start_tag, end_tag = "<pre>", "</pre>"
        elif ent_type == 'MessageEntityTextUrl':
            url = getattr(ent, 'url', '')
            start_tag, end_tag = f"<a href='{html.escape(url)}'>", "</a>"
        elif ent_type == 'MessageEntityUrl':
            url = "".join(res[offset:offset+length])
            start_tag, end_tag = f"<a href='{html.escape(url)}'>", "</a>"
        elif ent_type == 'MessageEntityMention':
            start_tag, end_tag = f"<span class='mention'>", "</span>"
        
        if start_tag:
            res.insert(offset + length, end_tag)
            res.insert(offset, start_tag)
            
    final_text = "".join(res)
    return final_text.replace("\n", "<br>")

def load_json(filepath: str, default: Any = None) -> Any:
    if not os.path.exists(filepath):
        return default if default is not None else {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON {filepath}: {e}")
        return default if default is not None else {}

def save_json(filepath: str, data: Any):
    try:
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save JSON {filepath}: {e}")

async def async_save_json(filepath: str, data: Any):
    import aiofiles
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error(f"Failed to async save JSON {filepath}: {e}")
