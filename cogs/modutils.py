import discord
from discord.ext import bridge, commands
from loguru import logger

from main import command_guild_ids
from cog import Cog
from utils import get_guild_config


class ModUtils(Cog):
    @commands.message_command(name='Log Information', guild_ids=command_guild_ids)
    async def log_information(self, ctx: discord.ApplicationContext, message: discord.Message):
        guild_config = get_guild_config(message.guild.id, 'modutils')
        if guild_config is None:
            await ctx.respond('This guild does not have a configuration for this command.', ephemeral=True)
            return

        target_channel_id = int(guild_config['log_info_target_channel'])
        target_channel = self.bot.get_channel(target_channel_id)
        if target_channel is None:
            logger.error(f'Could not find channel with ID {target_channel_id}')
            return

        embed = discord.Embed(
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


def setup(bot: bridge.Bot):
    bot.add_cog(ModUtils(bot))
