import disnake
from disnake.ext import commands
from loguru import logger

from main import command_guild_ids
from cog import Cog
from utils import get_guild_config


class PendingRole(Cog):
    manually_processing = []

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
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
    async def on_message(self, message: disnake.Message):
        if message.author.bot:
            return

        if message.guild is None:
            return

        guild_config = get_guild_config(message.guild.id, 'pendingrole')
        if guild_config is None:
            return

        role_ids = guild_config['roles']
        roles = [message.guild.get_role(role_id) for role_id in role_ids]

        member = message.author
        if not isinstance(message.author, disnake.Member):
            logger.debug(f'Message author is not a member: {message.author}')
            member = await message.guild.fetch_member(message.author.id)

        # if author has any of the roles in role_ids, skip
        if any(role.id in role_ids for role in member.roles):
            return

        if 'interaction' in guild_config['triggers']:
            logger.debug(f'Adding roles {", ".join(str(x) for x in role_ids)} to {message.author.display_name}')
            await message.author.add_roles(*roles, reason='[interaction/message] User no longer pending rule verification')

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
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

    @commands.slash_command(invoke_without_command=False, aliases=['pr'], guild_ids=command_guild_ids)
    async def pendingrole(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @pendingrole.sub_command()
    @commands.has_permissions(manage_messages=True)
    async def manual(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Manually verifies all rule-verified users
        """
        if ctx.guild.id in self.manually_processing:
            await ctx.send('Already processing members, please wait...', ephemeral=True)
            return

        guild_config = get_guild_config(ctx.guild.id, 'pendingrole')
        if guild_config is None:
            return

        role_ids = guild_config['roles']
        roles = [ctx.guild.get_role(role_id) for role_id in role_ids]

        await ctx.send('Processing verified members...')
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

        if isinstance(ctx, disnake.ApplicationCommandInteraction):
            await ctx.send(f'Finished verifying members; {count} updated')
        else:
            await ctx.followup.send(f'Finished verifying members; {count} updated')

        self.manually_processing.remove(ctx.guild.id)


def setup(bot: commands.Bot):
    bot.add_cog(PendingRole(bot))
