import os
import jinja2
from datetime import datetime
from utils import logger
import json

class HTMLWriter:
    def __init__(self, output_dir: str, template_dir: str = "templates"):
        self.output_dir = output_dir
        self.output_file = os.path.join(output_dir, "index.html")
        self.template_dir = template_dir
        
        # Setup Jinja2 environment
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.env.filters['to_json'] = lambda x: json.dumps(x, ensure_ascii=False)
        self.env.filters['get_color'] = self._get_color_for_id

    def _get_color_for_id(self, user_id: int) -> str:
        # Generate a consistent color based on user ID, similar to Telegram
        colors = ['#ff516a', '#ff8a5c', '#ffb74d', '#4db6ac', '#4fc3f7', '#7986cb', '#ba68c8']
        if not user_id:
            return colors[0]
        return colors[abs(int(user_id)) % len(colors)]

    async def save(self, group_info: dict, messages: list):
        try:
            template = self.env.get_template("index.html")
            
            # Group messages by date and calc user stats
            grouped_messages = {}
            user_stats = {}
            for msg in messages:
                date_str = msg.get('date_local', '')
                if date_str:
                    # '2024-01-01 12:00:00' -> '2024-01-01'
                    date_only = date_str.split(' ')[0]
                    if date_only not in grouped_messages:
                        grouped_messages[date_only] = []
                    grouped_messages[date_only].append(msg)
                
                sender_id = msg.get('sender_id')
                if sender_id:
                    if sender_id not in user_stats:
                        user_stats[sender_id] = {
                            "id": sender_id,
                            "name": msg.get("sender_name") or "Unknown",
                            "username": msg.get("sender_username"),
                            "phone": msg.get("sender_phone"),
                            "count": 0
                        }
                    user_stats[sender_id]["count"] += 1
            
            # Sort user_stats by count descending
            sorted_users = sorted(user_stats.values(), key=lambda x: x["count"], reverse=True)
                
            # Render template
            html_content = template.render(
                group=group_info,
                admins=group_info.get("admins", []),
                user_stats=sorted_users,
                messages_by_date=grouped_messages,
                total_messages=len(messages),
                export_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # Save to file asynchronously using standard library since write isn't too heavy
            # or with aiofiles. Here we use basic open for simplicity or import aiofiles.
            import aiofiles
            async with aiofiles.open(self.output_file, 'w', encoding='utf-8') as f:
                await f.write(html_content)
                
            logger.info(f"Saved HTML output to {self.output_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate HTML: {e}", exc_info=True)
