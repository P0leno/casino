
import asyncio
import os
import sys
import inspect
from pyrogram import Client
from app.config import API_ID, API_HASH, SESSION_STRING

async def main():
    app = Client(
        "inspector",
        api_id=int(API_ID),
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        in_memory=True
    )
    
    try:
        if hasattr(app, 'transfer_gift'):
            print("method transfer_gift exists")
            sig = inspect.signature(app.transfer_gift)
            print(f"Signature: {sig}")
        else:
            print("method transfer_gift DOES NOT exist")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    asyncio.run(main())
