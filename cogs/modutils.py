from typing import Callable

import disnake
from disnake.ext import commands
from loguru import logger

from main import command_guild_ids
from cog import Cog
from utils import get_guild_config


class ModUtils(Cog):
    @commands.slash_command(invoke_without_commands=False, guild_ids=command_guild_ids)
    @commands.has_permissions(manage_messages=True)
    async def embedban(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @embedban.sub_command()
    @commands.has_permissions(manage_messages=True)
    # @discord.option('duration', description='The duration to persist the embed ban')
    async def add(self,
                  ctx: disnake.ApplicationCommandInteraction,
                  user: str = commands.Param(
                      name='user',
                      description='The name or ID of the user to embed ban')):
        guild_config = get_guild_config(ctx.guild.id, 'modutils')
        if guild_config is None:
            await ctx.send('This guild does not have a configuration for this command.', ephemeral=True)
            return

        embedban_role_id = int(guild_config['embedban_role'])
        role = ctx.guild.get_role(embedban_role_id)

        # Parse input user ID
        if user.isnumeric():
            member = ctx.guild.get_member(int(user))
        elif user.startswith('<@') and user.endswith('>'):
            member = ctx.guild.get_member(int(user[2:-1]))
        else:
            member_lambda: Callable[[disnake.Member], bool] = (lambda m:
                                                               (user.lower() in m.name.lower()) or
                                                               (user.lower() in m.display_name.lower()))
            members = list(filter(member_lambda, ctx.guild.members))
            if len(members) == 0:
                await ctx.send('No users found by that name')
                return
            else:
                member = members[0]

        # If member is already embed banned, skip
        if role in member.roles:
            await ctx.send(f'{member} is already embed banned; to update, remove and re-issue the embed ban')
            return

        # TODO: Add duration support
        #
        # expiry_datetime = None
        #
        # if duration is not None:
        #     duration_seconds = parsetime(duration)
        #     now = datetime.now().timestamp()
        #     expiry = now + duration_seconds
        #     expiry_datetime = datetime.fromtimestamp(expiry)

        logger.debug(f'Adding embed ban role {embedban_role_id} for {member}')
        await member.add_roles(role, reason=f'Embed banned by {ctx.author}')
        await ctx.send(f'Embed ban issued for {member}')

    @embedban.sub_command()
    @commands.has_permissions(manage_messages=True)
    async def remove(self,
                     ctx: disnake.ApplicationCommandInteraction,
                     user: str = commands.Param(
                         name='user',
                         description='The name or ID of the user to remove embed ban from')):
        guild_config = get_guild_config(ctx.guild.id, 'modutils')
        if guild_config is None:
            await ctx.send('This guild does not have a configuration for this command.', ephemeral=True)
            return

        embedban_role_id = int(guild_config['embedban_role'])
        role = ctx.guild.get_role(embedban_role_id)

        # Parse input user ID
        if user.isnumeric():
            member = ctx.guild.get_member(int(user))
        elif user.startswith('<@') and user.endswith('>'):
            member = ctx.guild.get_member(int(user[2:-1]))
        else:
            member_lambda: Callable[[disnake.Member], bool] = (lambda m:
                                                               (user.lower() in m.name.lower()) or
                                                               (user.lower() in m.display_name.lower()))
            members = list(filter(member_lambda, ctx.guild.members))
            if len(members) == 0:
                await ctx.send('No users found by that name')
                return
            else:
                member = members[0]

        # If member is not embed banned, skip
        if role not in member.roles:
            await ctx.send(f'{member} is not embed banned')
            return

        logger.debug(f'Removing embed ban role {embedban_role_id} from {member}')
        await member.remove_roles(role, reason=f'Embed ban removed by {ctx.author}')
        await ctx.send(f'Embed ban removed from {member}')

    @embedban.sub_command()
    @commands.has_permissions(manage_messages=True)
    async def list(self, ctx: disnake.ApplicationCommandInteraction):
        guild_config = get_guild_config(ctx.guild.id, 'modutils')
        if guild_config is None:
            await ctx.send('This guild does not have a configuration for this command.', ephemeral=True)
            return

        embedban_role_id = int(guild_config['embedban_role'])
        role = ctx.guild.get_role(embedban_role_id)

        members = [member for member in ctx.guild.members if role in member.roles]
        if len(members) == 0:
            await ctx.send('No embed banned users')
            return

        await ctx.send(f'Embed banned users: {", ".join([f"{member.mention} (`{member.id}`)" for member in members])}')

    @commands.message_command(name='Log Information', guild_ids=command_guild_ids)
    async def log_information(self, ctx: disnake.ApplicationCommandInteraction, message: disnake.Message):
        guild_config = get_guild_config(message.guild.id, 'modutils')
        if guild_config is None:
            await ctx.respond('This guild does not have a configuration for this command.', ephemeral=True)
            return

        target_channel_id = int(guild_config['log_info_target_channel'])
        target_channel = self.bot.get_channel(target_channel_id)
        if target_channel is None:
            logger.error(f'Could not find channel with ID {target_channel_id}')
            return

        embed = disnake.Embed(
            description=message.content,
            color=0xAA8ED6
        )

        embed.set_author(name=f'{message.author} (`{message.author.id}`)', icon_url=message.author.display_avatar.url)
        embed.add_field(name='Message ID', value=f'`{message.id}`', inline=False)
        embed.add_field(name='Timestamp', value=f'<t:{int(message.created_at.timestamp())}:d> <t:{int(message.created_at.timestamp())}:T>', inline=False)

        if len(message.attachments) > 0:
            embed.add_field(name='Attachments', value='\n'.join([f'[{attachment.filename}]({attachment.url})' for attachment in message.attachments]), inline=False)

        if message.edited_at is not None:
            embed.add_field(name='Edited', value=f'<t:{int(message.edited_at.timestamp())}:d> <t:{int(message.edited_at.timestamp())}:T>', inline=False)

        try:
            await target_channel.send(f'*Message information requested by {ctx.author.mention} in {ctx.channel.mention}; [Jump to message]({message.jump_url})*', embed=embed)
        except Exception as e:
            logger.error(f'Failed to send message information to <#{target_channel_id}>')
            logger.error(e)
            await ctx.respond(f'Failed to send message information to <#{target_channel_id}>', ephemeral=True)

        await ctx.respond(f'Message information sent to <#{target_channel_id}>', ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(ModUtils(bot))
