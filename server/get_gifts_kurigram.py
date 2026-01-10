import asyncio
import os
import sys

# Ensure we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import API_ID, API_HASH, SESSION_STRING
from pyrogram import Client

async def main():
    print(f"Starting Kurigram Client with API_ID={API_ID}...")
    
    if not API_ID or not API_HASH or not SESSION_STRING:
        print("Error: credentials not found in config")
        return

    # User provided specific instructions for Client initialization if needed,
    # but based on standard usage for these libs:
    app = Client(
        "gift_debug_session",
        api_id=int(API_ID),
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        in_memory=True
    )

    try:
        await app.start()
        print("Client started.")
        
        me = await app.get_me()
        print(f"Logged in as: {me.first_name} (@{me.username}) ID: {me.id}")

        output_file = "giftoutput.txt"
        print(f"Fetching gifts and writing to {output_file}...")
        
        count = 0
        with open(output_file, "w", encoding="utf-8") as f:
            # Using get_chat_gifts as requested
            async for gift in app.get_chat_gifts(chat_id="me"):
                count += 1
                f.write(f"Gift #{count}:\n")
                f.write(str(gift))
                f.write("\n" + "="*50 + "\n")
                
                # Also print simple summary to console
                try:
                    title = getattr(gift, 'title', 'Unknown')
                    slug = getattr(gift, 'slug', getattr(gift, 'name', 'NoSlug'))
                    print(f"Found: {title} ({slug})")
                except:
                    pass

        print(f"Done. Processed {count} gifts.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await app.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
