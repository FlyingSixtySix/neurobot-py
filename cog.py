import discord
from discord.ext import commands
from loguru import logger

class Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.debug(f'Loading cog {self.__class__.__name__}')

    def cog_unload(self):
        logger.debug(f'Unloading cog {self.__class__.__name__}')

    def cog_command_error(self, ctx: discord.ApplicationContext, error: Exception):
        return super().cog_command_error(ctx, error)
