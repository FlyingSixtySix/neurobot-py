import discord
from discord.ext import bridge, commands
from loguru import logger

from main import command_guild_ids
from cog import Cog
from utils import get_guild_config


class PendingRole(Cog):
    manually_processing = []

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild_config = get_guild_config(after.guild.id, 'pendingrole')
        if guild_config is None:
            return

        role_ids = guild_config['roles']
        roles = [after.guild.get_role(role_id) for role_id in role_ids]

        # if after has any of the roles in role_ids, skip
        if any(role.id in role_ids for role in after.roles):
            return

        # if the user completed rule verification (no longer pending), add the roles
        if before.pending and not after.pending and 'rules' in guild_config['triggers']:
            logger.debug(f'Adding roles {", ".join(str(x) for x in role_ids)} to {after.display_name}')
            await after.add_roles(*roles, reason='[rules] User no longer pending rule verification')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        guild_config = get_guild_config(message.guild.id, 'pendingrole')
        if guild_config is None:
            return

        role_ids = guild_config['roles']
        roles = [message.guild.get_role(role_id) for role_id in role_ids]

        member = message.author
        if not isinstance(message.author, discord.Member):
            logger.debug(f'Message author is not a member: {message.author}')
            member = await message.guild.fetch_member(message.author.id)

        # if author has any of the roles in role_ids, skip
        if any(role.id in role_ids for role in member.roles):
            return

        if 'interaction' in guild_config['triggers']:
            logger.debug(f'Adding roles {", ".join(str(x) for x in role_ids)} to {message.author.display_name}')
            await message.author.add_roles(*roles, reason='[interaction/message] User no longer pending rule verification')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild_config = get_guild_config(member.guild.id, 'pendingrole')
        if guild_config is None:
            return

        role_ids = guild_config['roles']
        roles = [member.guild.get_role(role_id) for role_id in role_ids]

        # if member has any of the roles in role_ids, skip
        if any(role.id in role_ids for role in member.roles):
            return

        if 'interaction' in guild_config['triggers']:
            logger.debug(f'Adding roles {", ".join(str(x) for x in role_ids)} to {member.display_name}')
            await member.add_roles(*roles, reason='[interaction/voice] User no longer pending rule verification')

    @bridge.bridge_group(invoke_without_command=False, aliases=['pr'], guild_ids=command_guild_ids)
    async def pendingrole(self, ctx: bridge.BridgeContext):
        pass

    @pendingrole.command()
    @bridge.has_permissions(manage_messages=True)
    async def manual(self, ctx: bridge.BridgeExtContext | discord.ApplicationContext):
        """
        Manually verifies all rule-verified users
        """
        if ctx.guild.id in self.manually_processing:
            await ctx.respond('Already processing members, please wait...', ephemeral=True)
            return

        guild_config = get_guild_config(ctx.guild.id, 'pendingrole')
        if guild_config is None:
            return

        role_ids = guild_config['roles']
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

        if isinstance(ctx, bridge.BridgeExtContext):
            await ctx.respond(f'Finished verifying members; {count} updated')
        else:
            await ctx.followup.send(f'Finished verifying members; {count} updated')

        self.manually_processing.remove(ctx.guild.id)


def setup(bot: bridge.Bot):
    bot.add_cog(PendingRole(bot))
