import json
import re

import discord
from discord.ext import commands
from loguru import logger
import requests

from main import bot, config

command_guild_ids = [int(id) for id in config['bot']['guilds']]
deepl_api_key = config['jp']['deepl_api_key']


class JP(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.debug('Loaded cog JP')

    def cog_unload(self):
        logger.debug('Unloaded cog JP')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.type == discord.MessageType.application_command:
            return
        
        if message.guild is None:
            return
        
        if str(message.guild.id) not in config['jp']:
            return
        
        server_config = config['jp'][str(message.guild.id)]
        target_channel_id = int(server_config['target_channel'])
        output_channel_id = int(server_config['output_channel'])

        if message.channel.id != target_channel_id:
            return
        
        if message.author.bot:
            return
        
        content = message.content.strip()

        # ignore messages that are only emojis
        if re.match(r'^<a?:\w+:\d+>$', content):
            return
        
        body = {
            'source_lang': 'JA',
            'target_lang': 'EN-US',
            'text': [content]
        }
        body_enc = json.dumps(body)
        
        # send to deepl
        r = requests.post('https://api-free.deepl.com/v2/translate', data=body_enc, headers={
            'Authorization': 'DeepL-Auth-Key ' + deepl_api_key,
            'Content-Type': 'application/json',
            'Content-Length': str(len(body_enc))
        })
        if r.status_code != 200:
            logger.error('Deepl returned status code {code}', code=r.status_code)
            logger.error(r.text)
            return
        
        description = 'via DeepL | [Jump to message](' + message.jump_url + ')'

        embed = discord.Embed(
            description=description,
            color=0xAA8ED6,
            timestamp=message.created_at
        )

        name = message.author.name + ('#' + message.author.discriminator if message.author.discriminator != '0' else '')
        embed.set_author(name=name, icon_url=message.author.display_avatar.url)

        embed.add_field(name='', value=content)
        embed.add_field(name='Translation', value=r.json()['translations'][0]['text'], inline=False)
        
        await self.bot.get_channel(output_channel_id).send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(JP(bot))
