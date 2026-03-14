import os
import asyncio
from datetime import datetime, timezone
import telethon
from telethon import TelegramClient
from telethon.tl.types import (
    User, Chat, Channel, Message, PeerUser, PeerChat, PeerChannel,
    MessageActionPinMessage, MessageService, ChannelParticipantsAdmins,
    MessageActionChatAddUser, MessageActionChatDeleteUser, MessageActionChatJoinedByLink
)
from telethon.errors import FloodWaitError, ChannelPrivateError
from tqdm.asyncio import tqdm

from config import config
from utils import logger, format_datetime, get_local_datetime, get_message_html, sanitize_filename
from media_handler import MediaHandler
from output.json_writer import JSONWriter
from output.excel_writer import ExcelWriter
from output.html_writer import HTMLWriter

class TelegramExporter:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.start_date = datetime.fromisoformat(config.START_DATE).replace(tzinfo=timezone.utc)
        self.media_handler = None
        self.is_cancelled = False
        
    async def get_entity_info(self, entity_link: str) -> dict:
        entity = await self.client.get_entity(entity_link)
        full_entity = await self.client(telethon.functions.channels.GetFullChannelRequest(channel=entity)) if isinstance(entity, Channel) else None
        
        group_type = "unknown"
        if isinstance(entity, Channel):
            group_type = "supergroup" if entity.megagroup else "channel"
        elif isinstance(entity, Chat):
            group_type = "group"
            
        admins = []
        if group_type in ["supergroup", "channel"]:
            try:
                async for admin in self.client.iter_participants(entity, filter=ChannelParticipantsAdmins):
                    first_name = getattr(admin, 'first_name', '') or ""
                    last_name = getattr(admin, 'last_name', '') or ""
                    name = f"{first_name} {last_name}".strip()
                    if not name:
                        name = getattr(admin, 'title', str(admin.id))
                    admins.append({
                        "id": admin.id,
                        "name": name,
                        "username": getattr(admin, 'username', None),
                        "phone": getattr(admin, 'phone', None)
                    })
            except Exception as e:
                logger.warning(f"Could not fetch admins for {entity_link}: {e}")
            
        return {
            "entity": entity,
            "group_id": entity.id,
            "group_name": getattr(entity, 'title', getattr(entity, 'username', str(entity.id))),
            "group_username": getattr(entity, 'username', None),
            "group_type": group_type,
            "group_description": full_entity.full_chat.about if full_entity else None,
            "member_count": getattr(entity, 'participants_count', None),
            "is_public": getattr(entity, 'username', None) is not None,
            "creation_date": format_datetime(getattr(entity, 'date', None)),
            "admins": admins
        }

    async def _get_sender_info(self, sender) -> dict:
        if not sender:
            return {}
        
        info = {
            "sender_id": sender.id,
            "sender_name": "",
            "sender_username": getattr(sender, 'username', None),
            "sender_is_bot": getattr(sender, 'bot', False),
            "sender_phone": getattr(sender, 'phone', None),
            "sender_is_deleted": getattr(sender, 'deleted', False),
        }
        
        if isinstance(sender, User):
            first = getattr(sender, 'first_name', '') or ""
            last = getattr(sender, 'last_name', '') or ""
            info["sender_name"] = f"{first} {last}".strip()
        else:
            info["sender_name"] = getattr(sender, 'title', str(sender.id))
            
        return info

    async def extract_message(self, msg: Message, group_dir: str, pbar_manager=None) -> dict:
        data = {
            "message_id": msg.id,
            "date": format_datetime(msg.date),
            "date_local": get_local_datetime(msg.date),
            "message_type": "text",
            "text": msg.message or "",
            "text_html": get_message_html(msg.message, getattr(msg, 'entities', [])),
            "is_pinned": msg.pinned,
            "is_edited": msg.edit_date is not None,
            "edit_date": format_datetime(msg.edit_date),
            "views": getattr(msg, 'views', None),
        }
        
        # Sender info
        sender = await msg.get_sender()
        data.update(await self._get_sender_info(sender))
        
        # Entities
        if msg.entities:
            ents = []
            for ent in msg.entities:
                ents.append({
                    "type": type(ent).__name__.replace('MessageEntity', ''),
                    "offset": getattr(ent, 'offset', 0),
                    "length": getattr(ent, 'length', 0),
                    "url": getattr(ent, 'url', None)
                })
            data["entities"] = ents
            
        # Reply
        if msg.is_reply:
            data["reply_to_message_id"] = msg.reply_to_msg_id
            try:
                reply_msg = await msg.get_reply_message()
                if reply_msg:
                    reply_sender = await reply_msg.get_sender()
                    reply_info = await self._get_sender_info(reply_sender)
                    data["reply_to_sender_name"] = reply_info.get("sender_name")
                    data["reply_to_text_preview"] = (reply_msg.message or "")[:50]
            except Exception:
                pass
                
        # Forward
        if msg.forward:
            try:
                fwd_sender = await msg.forward.get_sender()
                if fwd_sender:
                    fwd_info = await self._get_sender_info(fwd_sender)
                    data["forward_from_name"] = fwd_info.get("sender_name")
                    data["forward_from_id"] = fwd_info.get("sender_id")
            except Exception:
                if msg.forward.from_name:
                    data["forward_from_name"] = msg.forward.from_name
            data["forward_original_date"] = format_datetime(msg.forward.date)
            
        # Reactions
        if msg.reactions and hasattr(msg.reactions, 'results'):
            reactions = []
            for r in msg.reactions.results:
                emoji = getattr(r.reaction, 'emoticon', '') if hasattr(r.reaction, 'emoticon') else 'custom'
                reactions.append({"emoji": emoji, "count": r.count})
            data["reactions"] = reactions

        # Service messages
        if isinstance(msg, MessageService):
            if getattr(msg, 'action', None) and isinstance(msg.action, (MessageActionChatAddUser, MessageActionChatDeleteUser, MessageActionChatJoinedByLink)):
                return None
            data["message_type"] = "service"
            if getattr(msg, 'action', None) and isinstance(msg.action, MessageActionPinMessage):
                data["text"] = "[Pinned a message]"
            else:
                data["text"] = f"[Service message: {type(getattr(msg, 'action', None)).__name__}]"
            data["text_html"] = data["text"]
            return data

        # Media
        if msg.media:
            meta = self.media_handler.get_media_metadata(msg)
            data.update(meta)
            if data.get("media_type") and data["media_type"] != "no_media":
                data["message_type"] = data["media_type"]
                dl_res = await self.media_handler.download_media(msg, group_dir, msg.date, pbar_manager)
                data.update(dl_res)
                
        return data

    async def export_group(self, link: str):
        try:
            logger.info(f"Connecting to group: {link}")
            info = await self.get_entity_info(link)
        except ChannelPrivateError:
            logger.error(f"Cannot access {link} (Channel Private).")
            return None, "ChannelPrivateError"
        except Exception as e:
            logger.error(f"Error accessing {link}: {e}")
            return None, str(e)
            
        entity = info.pop('entity')
        safe_name = sanitize_filename(info['group_name']) or str(info['group_id'])
        group_dir_name = f"{info['group_id']}_{safe_name}"
        group_dir = os.path.join(config.OUTPUT_DIR, group_dir_name)
        os.makedirs(group_dir, exist_ok=True)
        
        self.media_handler = MediaHandler(self.client, group_dir)
        
        # We need to estimate total messages to fetch
        # Telethon doesn't easily provide msg count after a date without iteration
        # We will iterate with tqdm
        rel_dir = os.path.relpath(group_dir)
        logger.info(f"Starting export for {info['group_name']}. Output dir: {rel_dir}")
        
        messages_data = []
        msg_count = 0
        
        # Load existing messages if JSON exists to support resuming partially
        jw = None
        highest_id = 0
        lowest_id = 0
        existing_ids = set()
        if "json" in config.OUTPUT_FORMATS:
            jw = JSONWriter(group_dir)
            existing_messages = jw.load_existing_messages()
            if existing_messages:
                messages_data.extend(existing_messages)
                msg_count = len(messages_data)
                existing_ids = {m.get("message_id") for m in existing_messages if m.get("message_id")}
                if existing_ids:
                    highest_id = max(existing_ids)
                    lowest_id = min(existing_ids)
                    logger.info(f"Resuming export. Found {len(existing_ids)} existing messages.")
                    logger.info(f"Will fetch messages newer than ID {highest_id} and older than ID {lowest_id}.")
            
        # Create a progress bar that updates as we fetch messages
        pbar = tqdm(desc=f"Fetching {safe_name[:15]}", unit="msg")
        
        async def fetch_loop(kwargs_dict):
            nonlocal msg_count
            max_msgs = getattr(config, "MAX_MESSAGES_PER_GROUP", 0)
            async for msg in self.client.iter_messages(entity, **kwargs_dict):
                if self.is_cancelled:
                    logger.info("Export cancelled by user. Saving progress...")
                    break
                
                if max_msgs > 0 and msg_count >= max_msgs:
                    logger.info(f"Reached max_messages_per_group limit ({max_msgs}). Stopping.")
                    break
                    
                # Ensure msg.date is aware, then compare
                msg_date = msg.date
                if not msg_date.tzinfo:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)
                    
                if msg_date < self.start_date:
                    break
                
                if msg.id in existing_ids:
                    continue
                    
                try:
                    msg_dict = await self.extract_message(msg, group_dir, pbar)
                    if msg_dict is None:
                        continue
                    
                    messages_data.append(msg_dict)
                    existing_ids.add(msg.id)
                    msg_count += 1
                    pbar.update(1)
                    
                    if msg_count % config.BATCH_SIZE == 0:
                        logger.info(f"Progress: Fetched {msg_count} messages for {info['group_name']}...")
                        await asyncio.sleep(config.REQUEST_DELAY)
                        # Intermediate save
                        if jw:
                            await jw.save_messages(messages_data)
                        
                except FloodWaitError as e:
                    logger.warning(f"Flood wait for {e.seconds}s during message extraction")
                    await asyncio.sleep(e.seconds + 5)
                except Exception as e:
                    logger.error(f"Error extracting message {msg.id} in {link}: {e}", exc_info=True)

        try:
            if highest_id > 0:
                # Phase 1: Fetch newer messages
                await fetch_loop({"min_id": highest_id})
                # Phase 2: Fetch older messages (if not cancelled)
                if not self.is_cancelled and lowest_id > 0:
                    await fetch_loop({"offset_id": lowest_id})
            else:
                # Fresh export
                await fetch_loop({})
                
        except Exception as e:
            logger.error(f"Unexpected error during export loop: {e}", exc_info=True)
            # Make sure we still generate the results with what we have
        finally:
            pbar.close()
            # Ensure final save if interrupted
            if jw and messages_data:
                await jw.save_messages(messages_data)
            
            # Update info
            info["export_time"] = format_datetime(datetime.now())
            info["message_count_exported"] = len(messages_data)
            if messages_data:
                dates = [m['date'] for m in messages_data if m.get('date')]
                if dates:
                    info["date_range"] = f"{min(dates)} to {max(dates)}"
                else:
                    info["date_range"] = "Unknown"
            else:
                info["date_range"] = "No messages"
                
            # Output Writers
            if "json" in config.OUTPUT_FORMATS:
                jw = JSONWriter(group_dir)
                await jw.save_messages(messages_data)
                await jw.save_group_info(info)
                
            if "excel" in config.OUTPUT_FORMATS:
                ew = ExcelWriter(group_dir)
                ew.save(messages_data)
                
            if "html" in config.OUTPUT_FORMATS:
                hw = HTMLWriter(group_dir)
                await hw.save(info, messages_data)
                
            logger.info(f"Finished exporting {info['group_name']}. Total msgs: {len(messages_data)}")
            
        return info, None
