import discord
from discord.ext import commands
from loguru import logger

from main import bot, config

command_guild_ids = [int(id) for id in config['bot']['guilds']]

class Manage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.debug('Loaded cog Manage')

    def cog_unload(self):
        bot.remove_command('manage')
        logger.debug('Unloaded cog Manage')

    manage = discord.SlashCommandGroup('manage', 'Manage the bot', guild_ids=command_guild_ids)

    @manage.command()
    @commands.is_owner()
    async def load(self,
            ctx: discord.ApplicationContext,
            cog: discord.Option(str, name='cog', description='The cog to load', required=True) = None):
        cog = cog.lower()
        if cog == 'manage':
            await ctx.respond('You cannot load the manage cog', ephemeral=True)
            return
        logger.debug(f'Loading cog {cog}')
        try:
            bot.load_extension(f'cogs.{cog}')
        except Exception as e:
            logger.error(f'Could not load cog {cog}')
            logger.error(e)
            await ctx.respond(f'Cog `{cog}` could not be loaded', ephemeral=True)
            return
        await ctx.respond(f'Loaded cog `{cog}`', ephemeral=True)

    @manage.command()
    @commands.is_owner()
    async def unload(self,
            ctx: discord.ApplicationContext,
            cog: discord.Option(str, name='cog', description='The cog to unload', required=True) = None):
        cog = cog.lower()
        if cog == 'manage':
            await ctx.respond('You cannot unload the manage cog', ephemeral=True)
            return
        if cog not in [x.lower() for x in bot.cogs]:
            await ctx.respond(f'Cog `{cog}` is not loaded', ephemeral=True)
            return
        logger.debug(f'Unloading cog {cog}')
        bot.unload_extension(f'cogs.{cog}')
        await ctx.respond(f'Unloaded cog `{cog}`', ephemeral=True)

    @manage.command()
    @commands.has_permissions(manage_messages=True)
    async def reload(self,
            ctx: discord.ApplicationContext,
            cog: discord.Option(str, name='cog', description='The cog to reload', required=False) = None):
        if cog:
            if cog not in [x.lower() for x in bot.cogs]:
                await ctx.respond(f'Cog `{cog}` is not loaded', ephemeral=True)
                return
            logger.debug(f'Reloading cog {cog}')
            bot.reload_extension(f'cogs.{cog}')
            logger.debug(f'Reloaded cog {cog}')
            await ctx.respond(f'Reloaded cog `{cog}`', ephemeral=True)
        else:
            logger.debug('Reloading all cogs')
            cog_names = [x.lower() for x in bot.cogs]
            for cog in cog_names:
                bot.reload_extension(f'cogs.{cog}')
            logger.debug('Reloaded all cogs')
            await ctx.respond('Reloaded all cogs', ephemeral=True)

    @manage.command()
    @commands.has_permissions(manage_messages=True)
    async def loaded(self, ctx: discord.ApplicationContext):
        cog_names = [x.lower() for x in bot.cogs]
        await ctx.respond(f'Loaded cogs: `{"`, `".join(cog_names)}`', ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(Manage(bot))
