import sys
import tomllib

import disnake
from disnake.ext import commands
from loguru import logger

with open('config.toml', 'rb') as file:
    config = tomllib.load(file)

command_guild_ids = [int(id) for id in config['bot']['guilds']]

logger.remove()
logger.add(sys.stderr, level=config['bot']['log_level'].upper())

intents = disnake.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(
    intents=intents,
    command_prefix=config['bot']['prefix'],
    help_command=None,
    allowed_mentions=disnake.AllowedMentions.none())

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}#{bot.user.discriminator} ({bot.user.id})')


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.reply(f'Error: {error}')

bot.load_extensions('cogs')

sys.exit(bot.run(config['bot']['token']))
