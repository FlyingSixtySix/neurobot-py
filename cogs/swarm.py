import disnake
from disnake.ext import commands

from main import command_guild_ids, config
from cog import Cog
from utils import get_guild_config


class GuildState:
    def __init__(self):
        self.count = 0
        self.last_sticker = None


class Swarm(Cog):
    guilds = {
        x: GuildState()
        for x in command_guild_ids if str(x) in config['swarm']
    }

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot:
            return

        if message.guild is None:
            return

        guild_config = get_guild_config(message.guild.id, 'swarm')
        if guild_config is None:
            return

        target_channel_id = int(guild_config['target_channel'])

        if message.channel.id != target_channel_id:
            return

        if not message.stickers:
            return

        state = self.guilds[message.guild.id]
        sticker = message.stickers[0]

        if state.last_sticker is None:
            state.last_sticker = sticker
        if state.last_sticker == sticker:
            state.count += 1
            if state.count % 5 == 0:
                await message.channel.send(f'{state.last_sticker.name} has a streak of {state.count}!', allowed_mentions=disnake.AllowedMentions.none())
        else:
            if state.count >= 5:
                await message.channel.send(f'{message.author.mention} broke {state.last_sticker.name} streak of {state.count}!', allowed_mentions=disnake.AllowedMentions.none())
            state.last_sticker = sticker
            state.count = 1


def setup(bot: commands.Bot):
    bot.add_cog(Swarm(bot))
