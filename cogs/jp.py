import json
import re

import discord
from discord.ext import bridge, commands
from loguru import logger
import requests

from main import config
from cog import Cog
from utils import get_guild_config

deepl_api_key = config['jp']['deepl_api_key']


class JP(Cog):
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild is None:
            return

        guild_config = get_guild_config(message.guild.id, 'jp')
        if guild_config is None:
            return

        target_channel_id = int(guild_config['target_channel'])
        output_channel_id = int(guild_config['output_channel'])

        if message.channel.id != target_channel_id:
            return

        # ignore messages that are only emojis
        if re.match(r'^<a?:\w+:\d+>$', message.content):
            return

        body = {
            'source_lang': 'JA',
            'target_lang': 'EN-US',
            'text': [message.content]
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

        embed.add_field(name='', value=message.content)
        embed.add_field(name='Translation', value=r.json()['translations'][0]['text'], inline=False)

        await self.bot.get_channel(output_channel_id).send(embed=embed)


def setup(bot: bridge.Bot):
    bot.add_cog(JP(bot))
