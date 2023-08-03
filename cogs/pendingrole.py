import discord
from discord.ext import commands
from loguru import logger

from main import bot, config

command_guild_ids = [int(id) for id in config['bot']['guilds']]


class PendingRole(commands.Cog):
    pendingrole = discord.SlashCommandGroup('pendingrole', 'Manage the pending role', guild_ids=command_guild_ids)

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manually_processing = []
        logger.debug('Loaded cog PendingRole')

    def cog_unload(self):
        bot.remove_application_command('jp')
        logger.debug('Unloaded cog PendingRole')

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if str(after.guild.id) not in config['pendingrole']:
            return
        
        server_config = config['pendingrole'][str(after.guild.id)]
        role_ids = server_config['roles']

        roles = [after.guild.get_role(role_id) for role_id in role_ids]

        # if after has any of the roles in role_ids, skip
        if any(role.id in role_ids for role in after.roles):
            return

        # if the user completed rule verification (no longer pending), add the roles
        if before.pending and not after.pending:
            logger.debug(f'Adding roles {", ".join(str(x) for x in role_ids)} to {after.display_name}')
            await after.add_roles(*roles, reason='User no longer pending rule verification')

    @pendingrole.command()
    @commands.has_permissions(manage_messages=True)
    async def manual(self, ctx: discord.ApplicationContext):
        """
        Manually verifies all rule-verified users
        """
        if str(ctx.guild.id) not in config['pendingrole']:
            return
        
        if ctx.guild.id in self.manually_processing:
            await ctx.respond('Already processing members, please wait', ephemeral=True)
            return
        
        server_config = config['pendingrole'][str(ctx.guild.id)]
        role_ids = server_config['roles']

        roles = [ctx.guild.get_role(role_id) for role_id in role_ids]

        await ctx.respond('Processing verified members...')
        self.manually_processing.append(ctx.guild.id)

        members = await ctx.guild.fetch_members(limit=None).flatten()
        logger.debug(f'Processing {len(members)} members')

        count = 0

        for member in members:
            if member.pending:
                continue

            if any(role.id in role_ids for role in member.roles):
                continue

            logger.debug(f'Adding roles {", ".join(str(x) for x in role_ids)} to {member.display_name}')
            await member.add_roles(*roles, reason='[Manual] User no longer pending rule verification')
            count += 1

        await ctx.followup.send(f'Finished verifying members; {count} updated')

def setup(bot: commands.Bot):
    bot.add_cog(PendingRole(bot))
