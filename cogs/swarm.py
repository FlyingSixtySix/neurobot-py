import discord
from discord.ext import commands
from loguru import logger

from main import bot, config

command_guild_ids = [int(id) for id in config['bot']['guilds']]


class Swarm(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_sticker: discord.StickerItem = None
        self.count = 0
        logger.debug('Loaded cog Swarm')

    def cog_unload(self):
        bot.remove_application_command('swarm')
        logger.debug('Unloaded cog Swarm')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.type == discord.MessageType.application_command:
            return
        
        server_config = config['swarm'][str(message.guild.id)]
        target_channel_id = int(server_config['target_channel'])

        if message.channel.id != target_channel_id:
            return
        
        if message.author.bot:
            return
        
        if message.stickers:
            if self.last_sticker is None:
                self.last_sticker = message.stickers[0]
            if self.last_sticker == message.stickers[0]:
                self.count += 1
                if self.count % 5 == 0:
                    await message.channel.send(f'{self.last_sticker.name} has a streak of {self.count}!', allowed_mentions=discord.AllowedMentions.none())
            else:
                if self.count >= 5:
                    await message.channel.send(f'{message.author.mention} broke {self.last_sticker.name} streak of {self.count}!', allowed_mentions=discord.AllowedMentions.none())
                self.last_sticker = message.stickers[0]
                self.count = 1


def setup(bot: commands.Bot):
    bot.add_cog(Swarm(bot))
