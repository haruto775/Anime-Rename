import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from datetime import datetime, timedelta
from helper.database import DARKXSIDE78
from config import *
from config import Config
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
from urllib.parse import quote
import string
import logging
import pytz

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

@Client.on_message(filters.private & filters.command(["token", "mytokens", "bal"]))
async def check_tokens(client, message: Message):
    user_id = message.from_user.id
    user_data = await DARKXSIDE78.col.find_one({"_id": user_id})
    
    if not user_data:
        return await message.reply_text("You're not registered yet! Send /start to begin.")
    
    # Get premium status
    is_premium = user_data.get("is_premium", False)
    premium_expiry = user_data.get("premium_expiry")
    
    # Check if premium is expired
    if is_premium and premium_expiry:
        if datetime.now() > premium_expiry:
            is_premium = False
            await DARKXSIDE78.col.update_one(
                {"_id": user_id},
                {"$set": {"is_premium": False, "premium_expiry": None}}
            )

    # Prepare message
    token_count = user_data.get("token", 69)
    msg = [
        "🔑 **Your Account Status** 🔑",
        "",
        f"🏷️ **Premium Status:** {'✅ Active' if is_premium else '❌ Inactive'}"
    ]
    
    if is_premium and premium_expiry:
        msg.append(f"⏳ **Premium Expiry:** {premium_expiry.strftime('%d %b %Y %H:%M')}")
    else:
        msg.extend([
            f"🪙 **Available Tokens:** {token_count}",
            "",
            "1 token = 1 file rename",
            ""
        ])
    
    # Create buttons
    buttons = []
    if not is_premium:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Generate More Tokens", callback_data="gen_tokens")],
            [InlineKeyboardButton("💎 Get Premium", callback_data="premium_info")]
        ])
    else:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_tokens")]
        ])
    
    await message.reply_text(
        "\n".join(msg),
        reply_markup=buttons,
        disable_web_page_preview=True
    )


# Add this callback handler
@Client.on_callback_query(filters.regex(r"^(gen_tokens|premium_info|refresh_tokens)$"))
async def token_buttons_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    user_data = await DARKXSIDE78.col.find_one({"_id": user_id})
    
    if data == "gen_tokens":
        # Show token generation options
        await query.message.edit_text(
            "🔗 **You can generate tokens using /gentoken** 🔗",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Support", url="https://t.me/Bots_Nations_Support")],
                [InlineKeyboardButton("« Back", callback_data="token_back")]
            ]),
            disable_web_page_preview=True
        )
    
    elif data == "premium_info":
        # Show premium information
        await query.message.edit_text(
            Txt.PREMIUM_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Support", url="https://t.me/Bots_Nations_Support")],
                [InlineKeyboardButton("« Back", callback_data="token_back")]
            ]),
            disable_web_page_preview=True
        )
    
    elif data == "refresh_tokens":
        # Refresh token status
        await check_tokens(client, query.message)
        await query.answer("Status refreshed!")
    
    elif data == "token_back":
        # Return to main token status
        await check_tokens(client, query.message)


# Configure logging
logging.basicConfig(level=logging.INFO)

@Client.on_message(filters.command("gentoken") & filters.private)
async def generate_token(client: Client, message: Message):
    user_id = message.from_user.id
    db = DARKXSIDE78
    
    # Generate unique token ID
    token_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=Config.TOKEN_ID_LENGTH))
    
    # Create Telegram deep link
    deep_link = f"https://t.me/{Config.BOT_USERNAME}?start={token_id}"
    
    # Shorten URL with retry logic
    short_url = await shorten_url(deep_link)
    
    if not short_url:
        return await message.reply("❌ Failed to generate token link. Please try later.")
    
    # Save token link to DB
    await db.create_token_link(user_id, token_id, 100)
    
    await message.reply(
        f"🔑 **Get 100 Tokens**\n\n"
        f"Click below link and complete verification:\n{short_url}\n\n"
        "⚠️ Link valid for 24 hours | One-time use only",
        disable_web_page_preview=True
    )

async def handle_token_redemption(client: Client, message: Message, token_id: str):
    user_id = message.from_user.id
    
    try:
        # Retrieve token data from the database
        token_data = await DARKXSIDE78.get_token_link(token_id)
        
        if not token_data:
            return await message.reply("❌ Invalid or expired token link")
        
        if token_data['used']:
            return await message.reply("❌ This link has already been used")
        
        # Convert stored naive datetime to UTC-aware datetime
        expiry_utc = token_data['expiry'].replace(tzinfo=pytz.UTC)
        
        if datetime.now(pytz.UTC) > expiry_utc:
            return await message.reply("❌ Token expired")
        
        if token_data['user_id'] != user_id:
            return await message.reply("❌ This token link belongs to another user")
        
        # Atomic update of tokens in the database using update_one
        await DARKXSIDE78.col.update_one(
            {"_id": user_id},
            {"$inc": {"token": token_data['tokens']}}
        )
        
        # Mark the token as used
        await DARKXSIDE78.mark_token_used(token_id)
        
        await message.reply(f"✅ Success! {token_data['tokens']} tokens added to your account!")
    
    except Exception as e:
        logging.error(f"Error during token redemption: {e}")
        await message.reply("❌ An error occurred while processing your request. Please try again.")

@Client.on_message(filters.private & filters.command("start"))
async def start(client, message: Message):
    if len(message.command) > 1:
        token_id = message.command[1]
        await handle_token_redemption(client, message, token_id)
        return
    
    user = message.from_user
    await DARKXSIDE78.add_user(client, message)

    # Initial interactive text and sticker sequence
    m = await message.reply_text("ᴏɴᴇᴇ-ᴄʜᴀɴ!, ʜᴏᴡ ᴀʀᴇ ʏᴏᴜ \nᴡᴀɪᴛ ᴀ ᴍᴏᴍᴇɴᴛ. . .")
    await asyncio.sleep(0.4)
    await m.edit_text("🎊")
    await asyncio.sleep(0.5)
    await m.edit_text("⚡")
    await asyncio.sleep(0.5)
    await m.edit_text("ꜱᴛᴀʀᴛɪɴɢ...")
    await asyncio.sleep(0.4)
    await m.delete()

    # Send sticker after the text sequence
    await message.reply_sticker("CAACAgUAAyEFAASOHochAAICC2fLz9ooHkh3H5eOdbBszBPLap9-AAJjFAACPONhVtw8FFfxZbTyNgQ")

    # Define buttons for the start message
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data='help')
        ],
        [
            InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/Bots_Nation'),
            InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/Bots_Nation_Support')
        ],
        [
            InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about'),
            InlineKeyboardButton('sᴏᴜʀᴄᴇ •', callback_data='source')
        ]
    ])

    # Send start message with or without picture
    if Config.START_PIC:
        await message.reply_photo(
            Config.START_PIC,
            caption=Txt.START_TXT.format(user.mention),
            reply_markup=buttons
        )
    else:
        await message.reply_text(
            text=Txt.START_TXT.format(user.mention),
            reply_markup=buttons,
            disable_web_page_preview=True
        )

# Shorten URL function with retry logic and fallback mechanism
async def shorten_url(deep_link: str) -> str:
    api_url = f"https://droplink.co/api?api={Config.TOKEN_API}&url={quote(deep_link)}&format=text"
    try:
        async with aiohttp.ClientSession() as session:
            max_retries = 3
            for attempt in range(max_retries):
                async with session.get(api_url, ssl=True) as response:
                    if response.status == 200:
                        return (await response.text()).strip()
                    logging.error(f"API Error: {response.status}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    except Exception as e:
        logging.error(f"Connection Error: {e}")
    # Fallback to original deep link if API fails
    logging.warning("Shorten URL API failed. Using original deep link.")
    return deep_link

# Callback Query Handler
@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    print(f"Callback data received: {data}")  # Debugging line

    if data == "home":
        await query.message.edit_text(
            text=Txt.START_TXT.format(query.from_user.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data='help')],
                [InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/Bots_Nation'), InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/Bots_Nation_Support')],
                [InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about'), InlineKeyboardButton('sᴏᴜʀᴄᴇ •', callback_data='source')]
            ])
        )
    elif data == "caption":
        await query.message.edit_text(
            text=Txt.CAPTION_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/Bots_Nation_Support'), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )

    elif data == "help":
        await query.message.edit_text(
            text=Txt.HELP_TXT.format(client.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')],
                [InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'), InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')],
                [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'), InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')],
                [InlineKeyboardButton('• ʜᴏᴍᴇ', callback_data='home')]
            ])
        )

    elif data == "meta":
        await query.message.edit_text(  # Change edit_caption to edit_text
            text=Txt.SEND_METADATA,  # Changed from caption to text
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "donate":
        await query.message.edit_text(
            text=Txt.DONATE_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("ᴏᴡɴᴇʀ •", url='https://t.me/DARKXSIDE78')]
            ])
        )
    elif data == "file_names":
        format_template = await DARKXSIDE78.get_format_template(user_id)
        await query.message.edit_text(
            text=Txt.FILE_NAME_TXT.format(format_template=format_template),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "thumbnail":
        await query.message.edit_caption(
            caption=Txt.THUMBNAIL_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "metadatax":
        await query.message.edit_caption(
            caption=Txt.SEND_METADATA,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "source":
        await query.message.edit_caption(
            caption=Txt.SOURCE_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="home")]
            ])
        )
    elif data == "premiumx":
        await query.message.edit_caption(
            caption=Txt.PREMIUM_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/Bots_Nation_Support')]
            ])
        )
    elif data == "plans":
        await query.message.edit_caption(
            caption=Txt.PREPLANS_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/Bots_Nation_Support')]
            ])
        )
    elif data == "about":
        await query.message.edit_text(
            text=Txt.ABOUT_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/Bots_Nation_Support'), InlineKeyboardButton("ᴄᴏᴍᴍᴀɴᴅs •", callback_data="help")],
                [InlineKeyboardButton("• ᴅᴇᴠᴇʟᴏᴘᴇʀ", url='https://t.me/DARKXSIDE78'), InlineKeyboardButton("ɴᴇᴛᴡᴏʀᴋ •", url='https://t.me/Bots_Nation')],
                [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="home")]
            ])
        )
    elif data == "close":
        try:
            await query.message.delete()
            await query.message.reply_to_message.delete()
            await query.message.continue_propagation()
        except:
            await query.message.delete()
            await query.message.continue_propagation()

# Donation Command Handler
@Client.on_message(filters.command("donate"))
async def donation(client, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="ʙᴀᴄᴋ", callback_data="help"), InlineKeyboardButton(text="ᴏᴡɴᴇʀ", url='https://t.me/DARKXSIDE78')]
    ])
    yt = await message.reply_photo(photo='https://graph.org/file/1919fe077848bd0783d4c.jpg', caption=Txt.DONATE_TXT, reply_markup=buttons)
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

# Premium Command Handler
@Client.on_message(filters.command("premium"))
async def getpremium(bot, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴏᴡɴᴇʀ", url="https://t.me/DARKXSIDE78"), InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]
    ])
    yt = await message.reply_photo(photo='https://graph.org/file/feebef43bbdf76e796b1b.jpg', caption=Txt.PREMIUM_TXT, reply_markup=buttons)
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

# Plan Command Handler
@Client.on_message(filters.command("plan"))
async def premium(bot, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("sᴇɴᴅ ss", url="https://t.me/Bots_Nation_Support"), InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]
    ])
    yt = await message.reply_photo(photo='https://graph.org/file/8b50e21db819f296661b7.jpg', caption=Txt.PREPLANS_TXT, reply_markup=buttons)
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

# Bought Command Handler
@Client.on_message(filters.command("bought") & filters.private)
async def bought(client, message):
    msg = await message.reply('Wait im checking...')
    replied = message.reply_to_message

    if not replied:
        await msg.edit("<b>Please reply with the screenshot of your payment for the premium purchase to proceed.\n\nFor example, first upload your screenshot, then reply to it using the '/bought' command</b>")
    elif replied.photo:
        await client.send_photo(
            chat_id=LOG_CHANNEL,
            photo=replied.photo.file_id,
            caption=f'<b>User - {message.from_user.mention}\nUser id - <code>{message.from_user.id}</code>\nUsername - <code>{message.from_user.username}</code>\nName - <code>{message.from_user.first_name}</code></b>',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Close", callback_data="close_data")]
            ])
        )
        await msg.edit_text('<b>Your screenshot has been sent to Admins</b>')

@Client.on_message(filters.private & filters.command("help"))
async def help_command(client, message):
    # Await get_me to get the bot's user object
    bot = await client.get_me()
    mention = bot.mention

    # Send the help message with inline buttons
    await message.reply_text(
        text=Txt.HELP_TXT.format(mention=mention),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')],
            [InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'), InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')],
            [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'), InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')],
            [InlineKeyboardButton('• ʜᴏᴍᴇ', callback_data='home')]
        ])
    )
