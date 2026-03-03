import os
import sys
import asyncio
from telethon import TelegramClient
from config import config

async def main():
    client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print(f"Not authorized. Sending code request to {config.PHONE}...")
        await client.send_code_request(config.PHONE)
        
        code = input("Enter the code you received on Telegram: ").strip()
            
        print(f"Read code {code}. Signing in...")
        try:
            await client.sign_in(config.PHONE, code)
            print("Signed in successfully!")
        except Exception as e:
            print(f"Failed to sign in: {e}")
            
    else:
        print("Already authorized!")
        
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
