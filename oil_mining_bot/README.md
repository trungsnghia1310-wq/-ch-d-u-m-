# Oil Mining Bot (Telegram)

This repository contains a starter Telegram bot (aiogram) implementing a simple oil-mining game:
- 6h cooldown mining
- Mandatory ad watching flag
- Daily check-in
- Tasks + offerwall callbacks (AyeT / AdGate)
- Referral links

## How to use
1. Set environment variable BOT_TOKEN to your Telegram bot token.
2. (Optional) DB path via DB_PATH environment variable.
3. Run locally: `python oil_mining_bot.py` or use Docker.

## Deploy to Railway / Cloud Run
- Add BOT_TOKEN to environment variables on the platform.
- Ensure persistent storage for SQLite (or use a managed DB for production).

## Note
This is a starter template. You must implement ad verification and secure callback validation for production.
