import json
import os
from utils import logger, async_save_json, load_json

class JSONWriter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.messages_file = os.path.join(output_dir, "messages.json")
        self.group_info_file = os.path.join(output_dir, "group_info.json")
        
    def load_existing_messages(self) -> list:
        if os.path.exists(self.messages_file):
            data = load_json(self.messages_file)
            if isinstance(data, list):
                return data
        return []
        
    async def save_messages(self, messages_data: list):
        await async_save_json(self.messages_file, messages_data)
        logger.info(f"Saved {len(messages_data)} messages to JSON.")
        
    async def save_group_info(self, info_data: dict):
        await async_save_json(self.group_info_file, info_data)
        logger.info(f"Saved group info to JSON.")
