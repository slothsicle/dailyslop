from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

from dailyslop.bot import DailySlopBot
from dailyslop.db import Database


def main() -> None:
    load_dotenv()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in.")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db = Database(os.environ.get("DAILYSLOP_DB") or "data/dailyslop.db")  # "" counts as unset
    DailySlopBot(db).run(token, log_handler=None)  # we configured logging above


if __name__ == "__main__":
    main()
