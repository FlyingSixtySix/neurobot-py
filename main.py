import sys
import tomllib

import discord
from discord.ext import commands
from loguru import logger

with open('config.toml', 'rb') as file:
    config = tomllib.load(file)

command_guild_ids = [int(id) for id in config['bot']['guilds']]

logger.remove()
logger.add(sys.stderr, level=config['bot']['log_level'].upper())

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(
    intents=intents,
    help_command=commands.DefaultHelpCommand(),
    allowed_mentions=discord.AllowedMentions.none())

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}#{bot.user.discriminator} ({bot.user.id})')


bot.load_extension('cogs', recursive=True)

sys.exit(bot.run(config['bot']['token']))
