from config import Config, Txt
from helper.database import DARKXSIDE78
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
import os, sys, time, asyncio, logging, datetime
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
import pytz  # If using timezones

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ADMIN_USER_ID = Config.ADMIN

# Flag to indicate if the bot is restarting
is_restarting = False

@Client.on_message(filters.private & filters.command("restart") & filters.user(ADMIN_USER_ID))
async def restart_bot(b, m):
    global is_restarting
    if not is_restarting:
        is_restarting = True
        await m.reply_text("**Restarting.....**")

        # Gracefully stop the bot's event loop
        b.stop()
        time.sleep(2)  # Adjust the delay duration based on your bot's shutdown time

        # Restart the bot process
        os.execl(sys.executable, sys.executable, *sys.argv)

@Client.on_message(filters.private & filters.command("leaderboard"))
#@Client.on_message(filters.command("leaderboard") & filters.user(Config.ADMIN))
async def show_leaderboard(bot: Client, message: Message):
    try:
        users = await DARKXSIDE78.col.find().sort("rename_count", -1).limit(10).to_list(10)
        leaderboard = ["<b>🏆 Top 10 Renamers 🏆</b>\n"]
        
        for idx, user in enumerate(users, 1):
            name = user.get('first_name', 'Unknown').strip() or "Anonymous"
            username = f"@{user['username']}" if user.get('username') else "No UN"
            count = user.get('rename_count', 0)
            leaderboard.append(
                f"<b>{idx}.</b> {name} "
                f"<i>({username})</i> ➠ "
                f"<code>{count}</code> ✨"
            )
        
        await message.reply_text("\n".join(leaderboard))
    except Exception as e:
        await message.reply_text(f"Error generating leaderboard: {e}")

@Client.on_message(filters.command("add_token") & filters.user(Config.ADMIN))
async def add_tokens(bot: Client, message: Message):
    try:
        _, amount, *user_info = message.text.split()
        user_ref = " ".join(user_info).strip()
        
        # Try to get user ID from mention or username
        if user_ref.startswith("@"):
            user = await DARKXSIDE78.col.find_one({"username": user_ref[1:]})
        else:
            user = await DARKXSIDE78.col.find_one({"_id": int(user_ref)})
        
        if not user:
            return await message.reply_text("User not found!")
        
        new_tokens = int(amount) + user.get('token', 69)
        await DARKXSIDE78.col.update_one(
            {"_id": user['_id']},
            {"$set": {"token": new_tokens}}
        )
        await message.reply_text(f"✅ Added {amount} tokens to user {user['_id']}. New balance: {new_tokens}")
    except Exception as e:
        await message.reply_text(f"Error: {e}\nUsage: /add_token <amount> @username/userid")

@Client.on_message(filters.command("remove_token") & filters.user(Config.ADMIN))
async def remove_tokens(bot: Client, message: Message):
    try:
        _, amount, *user_info = message.text.split()
        user_ref = " ".join(user_info).strip()
        
        if user_ref.startswith("@"):
            user = await DARKXSIDE78.col.find_one({"username": user_ref[1:]})
        else:
            user = await DARKXSIDE78.col.find_one({"_id": int(user_ref)})
        
        if not user:
            return await message.reply_text("User not found!")
        
        new_tokens = max(0, user.get('token', 69) - int(amount))
        await DARKXSIDE78.col.update_one(
            {"_id": user['_id']},
            {"$set": {"token": new_tokens}}
        )
        await message.reply_text(f"✅ Removed {amount} tokens from user {user['_id']}. New balance: {new_tokens}")
    except Exception as e:
        await message.reply_text(f"Error: {e}\nUsage: /remove_token <amount> @username/userid")

@Client.on_message(filters.command("add_premium") & filters.user(Config.ADMIN))
async def add_premium(bot: Client, message: Message):
    try:
        cmd, user_ref, duration = message.text.split(maxsplit=2)
        duration = duration.lower()
        
        # Get user
        if user_ref.startswith("@"):
            user = await DARKXSIDE78.col.find_one({"username": user_ref[1:]})
        else:
            user = await DARKXSIDE78.col.find_one({"_id": int(user_ref)})
        
        if not user:
            return await message.reply_text("User not found!")
        
        # Calculate expiration
        if duration == "lifetime":
            expiry = datetime(9999, 12, 31)
        else:
            num, unit = duration[:-1], duration[-1]
            unit_map = {
                'h': 'hours',
                'd': 'days',
                'm': 'months',
                'y': 'years'
            }
            delta = timedelta(**{unit_map[unit]: int(num)})
            expiry = datetime.now() + delta
        
        await DARKXSIDE78.col.update_one(
            {"_id": user['_id']},
            {"$set": {
                "is_premium": True,
                "premium_expiry": expiry
            }}
        )
        await message.reply_text(f"✅ Premium added until {expiry}")
    except Exception as e:
        await message.reply_text(f"Error: {e}\nUsage: /add_premium @username/userid 1d (1h/1m/1y/lifetime)")

@Client.on_message(filters.command("remove_premium") & filters.user(Config.ADMIN))
async def remove_premium(bot: Client, message: Message):
    try:
        _, user_ref = message.text.split(maxsplit=1)
        
        if user_ref.startswith("@"):
            user = await DARKXSIDE78.col.find_one({"username": user_ref[1:]})
        else:
            user = await DARKXSIDE78.col.find_one({"_id": int(user_ref)})
        
        if not user:
            return await message.reply_text("User not found!")
        
        await DARKXSIDE78.col.update_one(
            {"_id": user['_id']},
            {"$set": {
                "is_premium": False,
                "premium_expiry": None
            }}
        )
        await message.reply_text("✅ Premium access removed")
    except Exception as e:
        await message.reply_text(f"Error: {e}\nUsage: /remove_premium @username/userid")


@Client.on_message(filters.private & filters.command("tutorial"))
async def tutorial(bot: Client, message: Message):
    user_id = message.from_user.id
    format_template = await DARKXSIDE78.get_format_template(user_id)
    await message.reply_text(
        text=Txt.FILE_NAME_TXT.format(format_template=format_template),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴏᴡɴᴇʀ", url="https://t.me/darkxside78"),
             InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ", url="https://t.me/+xp9acqFgosQ5NjNl")]
        ])
    )


@Client.on_message(filters.command(["stats", "status"]) & filters.user(Config.ADMIN))
async def get_stats(bot, message):
    total_users = await DARKXSIDE78.total_users_count()
    uptime = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - bot.uptime))    
    start_t = time.time()
    st = await message.reply('**Accessing The Details.....**')    
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await st.edit(text=f"**--Bot Status--** \n\n**⌚️ Bot Uptime :** {uptime} \n**🐌 Current Ping :** `{time_taken_s:.3f} ms` \n**👭 Total Users :** `{total_users}`")

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN) & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    await bot.send_message(Config.LOG_CHANNEL, f"{m.from_user.mention} or {m.from_user.id} Is Started The Broadcast......")
    all_users = await DARKXSIDE78.get_all_users()
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("Broadcast Started..!") 
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    total_users = await DARKXSIDE78.total_users_count()
    async for user in all_users:
        sts = await send_msg(user['_id'], broadcast_msg)
        if sts == 200:
           success += 1
        else:
           failed += 1
        if sts == 400:
           await DARKXSIDE78.delete_user(user['_id'])
        done += 1
        if not done % 20:
           await sts_msg.edit(f"Broadcast In Progress: \n\nTotal Users {total_users} \nCompleted : {done} / {total_users}\nSuccess : {success}\nFailed : {failed}")
    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts_msg.edit(f"Bʀᴏᴀᴅᴄᴀꜱᴛ Cᴏᴍᴩʟᴇᴛᴇᴅ: \nCᴏᴍᴩʟᴇᴛᴇᴅ Iɴ `{completed_in}`.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}")
           
async def send_msg(user_id, message):
    try:
        await message.copy(chat_id=int(user_id))
        return 200
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return send_msg(user_id, message)
    except InputUserDeactivated:
        logger.info(f"{user_id} : Deactivated")
        return 400
    except UserIsBlocked:
        logger.info(f"{user_id} : Blocked The Bot")
        return 400
    except PeerIdInvalid:
        logger.info(f"{user_id} : User ID Invalid")
        return 400
    except Exception as e:
        logger.error(f"{user_id} : {e}")
        return 500
