import disnake
from disnake.ext import commands
from loguru import logger

from main import bot, command_guild_ids, config
from cog import Cog

silent = config['manage']['silent']


async def get_cog_names():
    return [x.lower() for x in bot.cogs]


class Manage(Cog):
    @commands.slash_command(invoke_without_command=False, guild_ids=command_guild_ids)
    @commands.has_permissions(manage_guild=True)
    async def manage(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @manage.sub_command()
    @commands.has_permissions(manage_guild=True)
    async def load(self,
                   ctx: disnake.ApplicationCommandInteraction,
                   cog: str = commands.Param(
                       name='cog',
                       description='The cog to load')):
        """
        Load a cog
        """
        cog = cog.lower()
        if cog == 'manage':
            await ctx.send('You cannot load the manage cog', ephemeral=silent)
            return
        try:
            bot.load_extension(f'cogs.{cog}')
        except Exception as e:
            logger.error(f'Could not load cog {cog}')
            logger.error(e)
            await ctx.send(f'Cog `{cog}` could not be loaded', ephemeral=silent)
            return
        await ctx.send(f'Loaded cog `{cog}`', ephemeral=silent)

    @manage.sub_command()
    @commands.has_permissions(manage_guild=True)
    async def unload(self,
                     ctx: disnake.ApplicationCommandInteraction,
                     cog: str = commands.Param(
                         name='cog',
                         description='The cog to unload')):
        """
        Unload a cog
        """
        cog = cog.lower()
        if cog == 'manage':
            await ctx.send('You cannot unload the manage cog', ephemeral=silent)
            return
        if cog not in [x.lower() for x in bot.cogs]:
            await ctx.send(f'Cog `{cog}` is not loaded', ephemeral=silent)
            return
        bot.unload_extension(f'cogs.{cog}')
        await ctx.send(f'Unloaded cog `{cog}`', ephemeral=silent)

    @manage.sub_command()
    @commands.has_permissions(manage_guild=True)
    async def reload(self,
                     ctx: disnake.ApplicationCommandInteraction,
                     cog: str = commands.Param(
                         None,
                         name='cog',
                         description='The cog to reload')):
        """
        Reload a cog or all cogs
        """
        if cog:
            if cog not in [x.lower() for x in bot.cogs]:
                await ctx.send(f'Cog `{cog}` is not loaded', ephemeral=silent)
                return
            bot.reload_extension(f'cogs.{cog}')
            await ctx.send(f'Reloaded cog `{cog}`', ephemeral=silent)
        else:
            cog_names = [x.lower() for x in bot.cogs]
            for cog in cog_names:
                bot.reload_extension(f'cogs.{cog}')
            await ctx.send('Reloaded all cogs', ephemeral=silent)

    @reload.autocomplete('cog')
    async def _reload_cog_autocomplete(self, ctx: disnake.ApplicationCommandInteraction):
        return await get_cog_names()

    @manage.sub_command()
    @commands.has_permissions(manage_guild=True)
    async def loaded(self, ctx: disnake.ApplicationCommandInteraction):
        """
        List all loaded cogs
        """
        cog_names = [x.lower() for x in bot.cogs]
        await ctx.send(f'Loaded cogs: `{"`, `".join(cog_names)}`', ephemeral=silent)


def setup(bot: commands.Bot):
    bot.add_cog(Manage(bot))
