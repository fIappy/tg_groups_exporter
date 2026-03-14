import os
import json
import pandas as pd
import asyncio
from output.json_writer import JSONWriter
from output.html_writer import HTMLWriter

async def main():
    phone_map = {}
    
    def process_df(df):
        if '账号ID' in df.columns and '手机号' in df.columns:
            for _, row in df.dropna(subset=['账号ID', '手机号']).iterrows():
                try:
                    uid = int(row['账号ID'])
                    phone = str(row['手机号']).split('.')[0].strip()
                    if phone and phone.isdigit():
                        phone_map[uid] = phone
                except Exception:
                    pass

    if os.path.exists('1.xlsx'):
        print("Reading 1.xlsx...")
        try:
            df1 = pd.read_excel('1.xlsx')
            process_df(df1)
        except Exception as e:
            print(f"Error reading 1.xlsx: {e}")

    if os.path.exists('2.xlsx'):
        print("Reading 2.xlsx...")
        try:
            df2 = pd.read_excel('2.xlsx')
            process_df(df2)
        except Exception as e:
            print(f"Error reading 2.xlsx: {e}")

    print(f"Loaded {len(phone_map)} user phone mappings.")

    output_dir = "tg_export"
    if not os.path.exists(output_dir):
        print(f"No {output_dir} directory found.")
        return
        
    for item in os.listdir(output_dir):
        group_dir = os.path.join(output_dir, item)
        if os.path.isdir(group_dir):
            info_file = os.path.join(group_dir, "group_info.json")
            messages_file = os.path.join(group_dir, "messages.json")
            
            info = {}
            if os.path.exists(info_file):
                with open(info_file, "r", encoding="utf-8") as f:
                    info = json.load(f)
                
                updated_info = False
                for admin in info.get('admins', []):
                    aid = admin.get('id')
                    if aid in phone_map:
                        admin['phone'] = phone_map[aid]
                        updated_info = True
                        
                if updated_info:
                    with open(info_file, "w", encoding="utf-8") as f:
                        json.dump(info, f, ensure_ascii=False, indent=2)

            messages = []
            if os.path.exists(messages_file):
                try:
                    with open(messages_file, "r", encoding="utf-8") as f:
                        messages = json.load(f)
                except Exception:
                    pass
                
                updated_msgs = False
                for msg in messages:
                    sender_id = msg.get('sender_id')
                    if sender_id in phone_map:
                        msg['sender_phone'] = phone_map[sender_id]
                        updated_msgs = True
                
                if updated_msgs:
                    with open(messages_file, "w", encoding="utf-8") as f:
                        json.dump(messages, f, ensure_ascii=False, indent=2)

            # Regenerate HTML
            hw = HTMLWriter(group_dir)
            await hw.save(info, messages)
            print(f"Updated and regenerated HTML for {item}")

if __name__ == "__main__":
    asyncio.run(main())
