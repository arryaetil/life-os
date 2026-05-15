#!/usr/bin/env python3
"""Local development only. Runs the bot in polling mode (no webhook needed)."""
import asyncio
from app.bot import create_ptb_app


async def main() -> None:
    ptb_app = create_ptb_app()
    await ptb_app.initialize()
    await ptb_app.start()
    await ptb_app.updater.start_polling()
    print("Bot running in polling mode. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await ptb_app.updater.stop()
        await ptb_app.stop()
        await ptb_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
