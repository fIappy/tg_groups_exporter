import os
import sys
import time
import asyncio
import argparse
from telethon import TelegramClient

from config import config
from utils import logger, setup_file_logger, save_json
from exporter import TelegramExporter

import signal

async def main():
    parser = argparse.ArgumentParser(description="Telegram Group Exporter")
    parser.add_argument("--links", type=str, help="Path to a txt file containing group links (one per line)")
    args = parser.parse_args()

    # Pre-checks
    if not config.API_ID or not config.API_HASH or not config.PHONE:
        logger.error("Please configure API_ID, API_HASH, and PHONE in config.yaml")
        sys.exit(1)

    group_links = []
    if args.links:
        if os.path.exists(args.links):
            with open(args.links, "r", encoding="utf-8") as f:
                group_links = [line.strip() for line in f.readlines() if line.strip()]
        else:
            logger.error(f"Links file not found: {args.links}")
            sys.exit(1)
    else:
        logger.error("Please provide a links file using --links parameter (e.g. --links groups.txt)")
        sys.exit(1)

    if not group_links:
        logger.error("No group links found in the provided file.")
        sys.exit(1)

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    setup_file_logger(os.path.join(config.OUTPUT_DIR, config.ERROR_LOG_FILE))
    
    logger.info("Initializing Telegram Client...")
    client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    
    await client.connect()
    if not await client.is_user_authorized():
        logger.info(f"Logging in with phone number: {config.PHONE}")
        await client.send_code_request(config.PHONE)
        logger.error("Interactive login required. Please run interactive_login.py first.")
        sys.exit(1)
            
    logger.info("Successfully logged in.")
    
    exporter = TelegramExporter(client)
    
    # Handle graceful shutdown in CLI
    def handle_sigint(sig, frame):
        logger.warning("\nCtrl+C detected! Gracefully stopping export and saving current progress...")
        exporter.is_cancelled = True
        
    signal.signal(signal.SIGINT, handle_sigint)
    
    summary = {
        "start_time": time.time(),
        "total_groups": len(group_links),
        "success_count": 0,
        "failed_count": 0,
        "total_messages_exported": 0,
        "groups": []
    }
    
    for link in group_links:
        try:
            info, error = await exporter.export_group(link)
            if error:
                summary["failed_count"] += 1
                summary["groups"].append({"link": link, "status": "failed", "error": error})
                logger.error(f"Failed to export {link}: {error}")
            else:
                summary["success_count"] += 1
                summary["total_messages_exported"] += info.get("message_count_exported", 0)
                summary["groups"].append({
                    "link": link,
                    "group_name": info.get("group_name"),
                    "status": "success",
                    "messages_exported": info.get("message_count_exported", 0)
                })
        except Exception as e:
            logger.error(f"Unexpected error processing {link}: {e}", exc_info=True)
            summary["failed_count"] += 1
            summary["groups"].append({"link": link, "status": "failed", "error": str(e)})
            
    # Disconnect client
    await client.disconnect()
    
    summary["end_time"] = time.time()
    summary["duration_seconds"] = summary["end_time"] - summary["start_time"]
    
    # Save summary
    summary_path = os.path.join(config.OUTPUT_DIR, config.SUMMARY_FILE)
    save_json(summary_path, summary)
    
    logger.info("="*40)
    logger.info("EXPORT COMPLETE")
    logger.info(f"Successful groups: {summary['success_count']}/{summary['total_groups']}")
    logger.info(f"Total messages exported: {summary['total_messages_exported']}")
    logger.info(f"Total time: {summary['duration_seconds']:.2f} seconds")
    logger.info(f"Summary saved to: {summary_path}")
    logger.info("="*40)

if __name__ == "__main__":
    asyncio.run(main())
