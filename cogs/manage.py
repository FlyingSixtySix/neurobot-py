import discord
from discord.ext import commands
from loguru import logger

from main import bot, command_guild_ids, config
from cog import Cog

silent = config['manage']['silent']


async def get_cog_names(ctx: discord.AutocompleteContext):
    return [x.lower() for x in bot.cogs]


class Manage(Cog):
    manage = discord.SlashCommandGroup('manage', 'Manage the bot', guild_ids=command_guild_ids)

    @manage.command()
    @commands.is_owner()
    async def load(self,
            ctx: discord.ApplicationContext,
            cog: discord.Option(str, name='cog', description='The cog to load', required=True) = None):
        """
        Load a cog
        """
        cog = cog.lower()
        if cog == 'manage':
            await ctx.respond('You cannot load the manage cog', ephemeral=silent)
            return
        try:
            bot.load_extension(f'cogs.{cog}')
        except Exception as e:
            logger.error(f'Could not load cog {cog}')
            logger.error(e)
            await ctx.respond(f'Cog `{cog}` could not be loaded', ephemeral=silent)
            return
        await ctx.respond(f'Loaded cog `{cog}`', ephemeral=silent)

    @manage.command()
    @commands.is_owner()
    async def unload(self,
            ctx: discord.ApplicationContext,
            cog: discord.Option(str, name='cog', description='The cog to unload', required=True, autocomplete=discord.utils.basic_autocomplete(get_cog_names)) = None):
        """
        Unload a cog
        """
        cog = cog.lower()
        if cog == 'manage':
            await ctx.respond('You cannot unload the manage cog', ephemeral=silent)
            return
        if cog not in [x.lower() for x in bot.cogs]:
            await ctx.respond(f'Cog `{cog}` is not loaded', ephemeral=silent)
            return
        bot.unload_extension(f'cogs.{cog}')
        await ctx.respond(f'Unloaded cog `{cog}`', ephemeral=silent)

    @manage.command()
    @commands.has_permissions(manage_messages=True)
    async def reload(self,
            ctx: discord.ApplicationContext,
            cog: discord.Option(str, name='cog', description='The cog to reload', required=False, autocomplete=discord.utils.basic_autocomplete(get_cog_names)) = None):
        """
        Reload a cog or all cogs
        """
        if cog:
            if cog not in [x.lower() for x in bot.cogs]:
                await ctx.respond(f'Cog `{cog}` is not loaded', ephemeral=silent)
                return
            bot.reload_extension(f'cogs.{cog}')
            await ctx.respond(f'Reloaded cog `{cog}`', ephemeral=silent)
        else:
            cog_names = [x.lower() for x in bot.cogs]
            for cog in cog_names:
                bot.reload_extension(f'cogs.{cog}')
            await ctx.respond('Reloaded all cogs', ephemeral=silent)

    @manage.command()
    @commands.has_permissions(manage_messages=True)
    async def loaded(self, ctx: discord.ApplicationContext):
        """
        List all loaded cogs
        """
        cog_names = [x.lower() for x in bot.cogs]
        await ctx.respond(f'Loaded cogs: `{"`, `".join(cog_names)}`', ephemeral=silent)


def setup(bot: commands.Bot):
    bot.add_cog(Manage(bot))
