
import asyncio
import os
import sys

# Ensure we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import API_ID, API_HASH, SESSION_STRING
from pyrogram import Client

from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler

# Target User ID to listen for
TARGET_USER_ID = 1056148947
# Gift Message ID to transfer
OWNED_GIFT_ID = 16368

async def transfer_trigger(client, message):
    user = message.from_user
    if not user or user.id != TARGET_USER_ID:
        return

    print(f"✅ Received message from target user: {user.first_name} (ID: {user.id})")
    print("User cache should now be populated. Attempting transfer...")

    try:
        result = await client.transfer_gift(
            message_id=OWNED_GIFT_ID,
            to_chat_id=TARGET_USER_ID
        )
        print("🎉 Transfer successful!")
        print(f"Result: {result}")
        await message.reply_text("✅ Gift transferred successfully!")
        
        # Optional: Stop after success
        # await client.stop() 
        # sys.exit(0)
        
    except Exception as e:
        print(f"❌ Error transferring gift: {e}")
        import traceback
        traceback.print_exc()
        await message.reply_text(f"❌ Transfer failed: {e}")

async def main():
    print(f"Starting Kurigram Client in LISTENER mode...")
    
    if not API_ID or not API_HASH or not SESSION_STRING:
        print("Error: credentials not found in config")
        return

    app = Client(
        "transfer_listener_session",
        api_id=int(API_ID),
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        in_memory=True
    )

    # Add handler
    app.add_handler(MessageHandler(transfer_trigger, filters.private))

    try:
        await app.start()
        me = await app.get_me()
        print(f"Logged in as: {me.first_name} (@{me.username}) ID: {me.id}")
        
        print(f"👂 Listening for messages from User ID {TARGET_USER_ID}...")
        print("Please send any message to this account from that user to trigger the transfer.")
        
        await idle()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            await app.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
