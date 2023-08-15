import json
import re
import sqlite3

import discord
from discord.ext import bridge, commands
from loguru import logger
import requests

from main import config
from cog import Cog
from utils import get_guild_config

deepl_api_key = config['jp']['deepl_api_key']


class JP(Cog):
    con = sqlite3.connect('neurobot.db')
    con.isolation_level = None

    def __init__(self, bot: bridge.Bot):
        super().__init__(bot)
        # TABLE: jp_translations
        cur = self.con.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS jp_translations (
                message_id INTEGER NOT NULL,
                translated_message_id INTEGER,
                PRIMARY KEY (message_id)
            )
        ''')
        cur.close()

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

        # ignore messages that are only URLs
        if re.match(r'^https?://\S+$', message.content):
            return

        # ignore messages that are only mentions
        if re.match(r'^<@!?\d+>$', message.content):
            return

        cur = self.con.cursor()
        cur.execute('''
            INSERT INTO jp_translations (message_id)
            VALUES (?)
        ''', (message.id,))

        translated = self.translate(message.content)
        if translated is None:
            cur.close()
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
        embed.add_field(name='Translation', value=translated, inline=False)

        translated_message = await self.bot.get_channel(output_channel_id).send(embed=embed)

        cur.execute('''
            UPDATE jp_translations
            SET translated_message_id = ?
            WHERE message_id = ?
        ''', (translated_message.id, message.id))
        cur.close()

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return

        if before.guild is None:
            return

        guild_config = get_guild_config(before.guild.id, 'jp')
        if guild_config is None:
            return

        target_channel_id = int(guild_config['target_channel'])
        output_channel_id = int(guild_config['output_channel'])

        if before.channel.id != target_channel_id:
            return

        cur = self.con.cursor()
        cur.execute('''
            SELECT translated_message_id FROM jp_translations
            WHERE message_id = ?
        ''', (before.id,))
        row = cur.fetchone()
        cur.close()

        if row is None:
            return

        translated_message_id = row[0]

        translated_message = await self.bot.get_channel(output_channel_id).fetch_message(translated_message_id)
        if translated_message is None:
            return

        translated = self.translate(after.content)
        if translated is None:
            cur.close()
            return

        # update embed
        embed = translated_message.embeds[0]
        embed.timestamp = after.edited_at
        embed.set_field_at(0, name='', value=after.content)
        embed.set_field_at(1, name='Translation', value=translated, inline=False)
        edit_count = 0
        if embed.footer is not None:
            edit_count = int(embed.footer.text.split(' ')[1].removesuffix('x'))
        embed.set_footer(text=f'Edited {edit_count + 1}x')
        await translated_message.edit(embed=embed)

    def translate(self, text) -> str:
        body = {
            'source_lang': 'JA',
            'target_lang': 'EN-US',
            'text': [text]
        }
        body_enc = json.dumps(body)

        r = requests.post('https://api-free.deepl.com/v2/translate', data=body_enc, headers={
            'Authorization': 'DeepL-Auth-Key ' + deepl_api_key,
            'Content-Type': 'application/json',
            'Content-Length': str(len(body_enc))
        })
        if r.status_code != 200:
            logger.error('Deepl returned status code {code}', code=r.status_code)
            logger.error(r.text)
            return

        return r.json()['translations'][0]['text']


def setup(bot: bridge.Bot):
    bot.add_cog(JP(bot))
