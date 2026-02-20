import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from chat.lottery import lottery_task, track_active_user
import logging
from logging.handlers import RotatingFileHandler
import asyncio

from payment.pay_out import request_payout

load_dotenv(".env")

os.makedirs('logs', exist_ok=True)
handler = RotatingFileHandler('logs/bot.log', maxBytes=5*1024*1024, backupCount=5)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[handler, logging.StreamHandler()]
)
logger = logging.getLogger('snap')
logging.getLogger('discord').setLevel(logging.WARNING)

bot = commands.Bot(command_prefix=None, intents=discord.Intents.all())


async def set_hookup():
    asyncio.create_task(request_payout(bot))
    
@bot.event
async def setup_hook():
    await bot.load_extension("commands.chat")
    
    # start the lottery background task
    bot.loop.create_task(lottery_task(bot))
    # start the background payout task
    bot.loop.create_task(request_payout(bot))
    logger.info("Extensions loaded and lottery task scheduled")

@bot.event
async def on_ready():
    logger.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    logger.info("Bot is ready in guild %s", os.getenv('GUILD_ID'))
    await bot.tree.sync()

@bot.event
async def on_message(message: discord.Message):
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Track active users for lottery
    try:
        guild_id = int(os.getenv("GUILD_ID", "0"))
        if message.guild and message.guild.id == guild_id:
            # Ignore commands
            if not (message.content.startswith("/") or message.content.startswith("\\") or message.content.startswith("!")):
                track_active_user(message.author.id)
                logger.debug("Tracked active user: %s", message.author.name)
    except (ValueError, TypeError) as e:
        logger.error("Error tracking user: %s", e)

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN not found in environment variables")
    else:
        logger.info("Starting bot...")
        bot.run(token)