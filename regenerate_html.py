import os
import asyncio
from output.json_writer import JSONWriter
from output.html_writer import HTMLWriter
import json

async def main():
    output_dir = "tg_export"
    if not os.path.exists(output_dir):
        print(f"No {output_dir} directory found.")
        return
        
    for item in os.listdir(output_dir):
        group_dir = os.path.join(output_dir, item)
        if os.path.isdir(group_dir):
            info_file = os.path.join(group_dir, "group_info.json")
            if os.path.exists(info_file):
                jw = JSONWriter(group_dir)
                messages = jw.load_existing_messages()
                
                with open(info_file, "r", encoding="utf-8") as f:
                    info = json.load(f)
                    
                hw = HTMLWriter(group_dir)
                await hw.save(info, messages)
                print(f"Regenerated HTML for {item}")

if __name__ == "__main__":
    asyncio.run(main())
