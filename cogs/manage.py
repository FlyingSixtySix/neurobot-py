import discord
from discord.ext import commands
from loguru import logger

from main import bot, config

command_guild_ids = [int(id) for id in config['bot']['guilds']]

class Manage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    manage = discord.SlashCommandGroup('manage', 'Manage the bot', guild_ids=command_guild_ids)

    @manage.command()
    @commands.is_owner()
    async def load(self,
                     ctx: discord.ApplicationContext,
                     cog: discord.Option(str, name='cog', description='The cog to load', required=False) = None):
          if cog:
            if cog == 'manage':
                await ctx.respond('You cannot load the manage cog', ephemeral=True)
                return
            logger.info(f'Loading cog {cog}')
            bot.load_extension(f'cogs.{cog}')
            await ctx.respond(f'Loaded cog `{cog}`', ephemeral=True)

    @manage.command()
    @commands.is_owner()
    async def unload(self,
                        ctx: discord.ApplicationContext,
                        cog: discord.Option(str, name='cog', description='The cog to unload', required=False) = None):
            if cog:
                if cog == 'manage':
                    await ctx.respond('You cannot unload the manage cog', ephemeral=True)
                    return
                logger.info(f'Unloading cog {cog}')
                bot.unload_extension(f'cogs.{cog}')
                await ctx.respond(f'Unloaded cog `{cog}`', ephemeral=True)

    @manage.command()
    @commands.has_permissions(manage_messages=True)
    async def reload(self,
                     ctx: discord.ApplicationContext,
                     cog: discord.Option(str, name='cog', description='The cog to reload', required=False) = None):
        if cog:
            logger.info(f'Reloading cog {cog}')
            bot.reload_extension(f'cogs.{cog}')
            await ctx.respond(f'Reloaded cog `{cog}`', ephemeral=True)
        else:
            logger.info('Reloading all cogs')
            cog_names = [x.lower() for x in bot.cogs]
            for cog in cog_names:
                bot.reload_extension(f'cogs.{cog}')
            await ctx.respond('Reloaded all cogs', ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(Manage(bot))
