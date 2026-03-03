import pandas as pd
import os
from utils import logger
from datetime import datetime

class ExcelWriter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.output_file = os.path.join(output_dir, "messages.xlsx")

    def save(self, messages: list):
        if not messages:
            logger.info("No messages to save to Excel.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(messages)
        
        # Format dates properly
        if 'date_local' in df.columns:
            # Try to convert to datetime
            df['date_local'] = pd.to_datetime(df['date_local'], errors='coerce')
            
        with pd.ExcelWriter(self.output_file, engine='openpyxl') as writer:
            # Sheet 1: Messages
            df.to_excel(writer, sheet_name='消息记录', index=False)
            
            # Freeze top row and add autofilter
            worksheet = writer.sheets['消息记录']
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            
            # Sheet 2: Speaker Stats
            if 'sender_name' in df.columns and 'sender_id' in df.columns:
                speaker_stats = self._generate_speaker_stats(df)
                speaker_stats.to_excel(writer, sheet_name='发言者统计', index=False)
            
            # Sheet 3: Daily Stats
            if 'date_local' in df.columns:
                daily_stats = self._generate_daily_stats(df)
                daily_stats.to_excel(writer, sheet_name='每日消息统计', index=False)
                
        logger.info(f"Saved {len(df)} messages to Excel.")

    def _generate_speaker_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        # Group by sender_id, sender_name, sender_username
        stats = []
        # Required columns: 发言者 | username | 消息数 | 图片数 | 文件数 | 最早发言 | 最近发言
        grouped = df.groupby(['sender_id', 'sender_name'])
        
        for (sender_id, sender_name), group in grouped:
            username = group['sender_username'].iloc[0] if 'sender_username' in group.columns else ""
            msg_count = len(group)
            
            photo_count = 0
            file_count = 0
            if 'media_type' in group.columns:
                photo_count = (group['media_type'] == 'photo').sum()
                file_count = group['media_type'].isin(['document', 'video', 'audio', 'voice']).sum()
                
            first_msg = group['date_local'].min()
            last_msg = group['date_local'].max()
            
            stats.append({
                '发言者': sender_name,
                'username': username,
                '消息数': msg_count,
                '图片数': photo_count,
                '文件数': file_count,
                '最早发言': first_msg,
                '最近发言': last_msg
            })
            
        return pd.DataFrame(stats).sort_values(by='消息数', ascending=False)

    def _generate_daily_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        stats = []
        
        # Ensure 'date_local' is datetime and extract just the date part for grouping
        df_copy = df.copy()
        df_copy['date_only'] = df_copy['date_local'].dt.date
        
        grouped = df_copy.groupby('date_only')
        
        for date_val, group in grouped:
            msg_count = len(group)
            
            media_count = 0
            if 'media_type' in group.columns:
                media_count = group['media_type'].notna().sum()
                
            active_users = 0
            if 'sender_id' in group.columns:
                active_users = group['sender_id'].nunique()
                
            stats.append({
                '日期': date_val,
                '消息总数': msg_count,
                '含媒体消息数': media_count,
                '活跃发言者数': active_users
            })
            
        return pd.DataFrame(stats).sort_values(by='日期')
