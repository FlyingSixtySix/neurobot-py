import discord
from discord.ext import bridge
from loguru import logger

from main import bot, command_guild_ids, config
from cog import Cog

silent = config['manage']['silent']


async def get_cog_names(ctx: discord.AutocompleteContext):
    return [x.lower() for x in bot.cogs]


class Manage(Cog):
    @bridge.bridge_group(invoke_without_command=False, guild_ids=command_guild_ids)
    @bridge.has_permissions(manage_guild=True)
    async def manage(self, ctx: bridge.BridgeContext):
        pass

    @manage.command()
    @bridge.has_permissions(manage_guild=True)
    @discord.option('cog', description='The cog to load', required=True)
    async def load(self, ctx: bridge.BridgeExtContext, cog: str = None):
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
    @bridge.has_permissions(manage_guild=True)
    @discord.option('cog', description='The cog to unload', required=True, autocomplete=discord.utils.basic_autocomplete(get_cog_names))
    async def unload(self, ctx: bridge.BridgeExtContext, cog: str = None):
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
    @bridge.has_permissions(manage_guild=True)
    @discord.option('cog', description='The cog to reload', required=False, autocomplete=discord.utils.basic_autocomplete(get_cog_names))
    async def reload(self, ctx: bridge.BridgeExtContext, cog: str = None):
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
    @bridge.has_permissions(manage_guild=True)
    async def loaded(self, ctx: bridge.BridgeExtContext):
        """
        List all loaded cogs
        """
        cog_names = [x.lower() for x in bot.cogs]
        await ctx.respond(f'Loaded cogs: `{"`, `".join(cog_names)}`', ephemeral=silent)


def setup(bot: bridge.Bot):
    bot.add_cog(Manage(bot))
