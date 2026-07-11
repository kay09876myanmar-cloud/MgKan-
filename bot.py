#!/usr/bin/env python3
import json, time, secrets, logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

ADMIN_ID = 8565708186
BOT_TOKEN = "8986176630:AAHmzMDtwbGO19vt5Vqqq88lgl9-Ih6hvig"
DB_FILE = "mgkan_keys.json"

logging.basicConfig(level=logging.INFO)

def load_db():
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"keys": {}, "used": []}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def generate_key(days=30):
    key = f"MGKAN-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    expiry = int(time.time()) + (days * 86400)
    return key, expiry

async def start(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    await update.message.reply_text(
        "🔥 **MgKan Key Manager**\n\n"
        "/gen <days> - Generate key\n"
        "/list - Show all keys\n"
        "/revoke <key> - Revoke key\n"
        "/stats - Show statistics"
    )

async def generate(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    days = 30
    if context.args:
        try:
            days = int(context.args[0])
            if days < 1:
                days = 1
        except:
            pass
    
    key, expiry = generate_key(days)
    db = load_db()
    db["keys"][key] = {
        "expiry": expiry,
        "created": int(time.time()),
        "days": days
    }
    save_db(db)
    
    await update.message.reply_text(
        f"✅ **MgKan Key Generated!**\n\n"
        f"🔑 `{key}`\n"
        f"📅 Expires: {days} days\n"
        f"⏰ Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        parse_mode="Markdown"
    )

async def list_keys(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    db = load_db()
    if not db["keys"]:
        await update.message.reply_text("📭 No keys found.")
        return
    msg = "📋 **Active Keys:**\n\n"
    now = int(time.time())
    for k, v in db["keys"].items():
        rem = max(0, (v["expiry"] - now) // 86400)
        status = "✅ Active" if rem > 0 else "❌ Expired"
        msg += f"🔑 `{k}` → {status} ({rem} days)\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def revoke(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❌ /revoke MGKAN-XXXX-XXXX-XXXX")
        return
    key = context.args[0].upper()
    db = load_db()
    if key in db["keys"]:
        del db["keys"][key]
        save_db(db)
        await update.message.reply_text(f"✅ Revoked: `{key}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Key not found.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gen", generate))
    app.add_handler(CommandHandler("list", list_keys))
    app.add_handler(CommandHandler("revoke", revoke))
    print("🤖 MgKan Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
