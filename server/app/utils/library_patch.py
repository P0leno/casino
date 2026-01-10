
import logging

logger = logging.getLogger(__name__)

def apply_pyrogram_patches():
    """
    Patches Pyrogram classes at runtime to fix known bugs.
    """
    try:
        from pyrogram.raw.types import MessageActionStarGiftUnique
        
        # Bug: MessageActionStarGiftUnique missing 'auction_acquired' attribute in some library versions
        # causing crash in Message._parse_service
        if not hasattr(MessageActionStarGiftUnique, 'auction_acquired'):
            logger.info("🔧 Patching MessageActionStarGiftUnique: adding 'auction_acquired' default")
            setattr(MessageActionStarGiftUnique, 'auction_acquired', False)
            
    except ImportError:
        logger.warning("⚠️ Could not import MessageActionStarGiftUnique for patching")
    except Exception as e:
        logger.error(f"❌ Error applying Pyrogram patches: {e}")
