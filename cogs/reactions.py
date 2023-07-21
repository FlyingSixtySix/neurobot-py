import re
import sqlite3
import time

import discord
from discord.ext import commands
from loguru import logger

from main import bot, config

command_guild_ids = [int(id) for id in config['bot']['guilds']]
silent = config['reactions']['silent']


async def get_group_names(ctx: discord.AutocompleteContext):
    """
    Slash command autocomplete for reaction group names.
    """
    cur = Reactions.con.cursor()
    cur.execute('''
        SELECT name, builtin
        FROM reaction_groups
        WHERE guild_id = ?
    ''', (ctx.interaction.guild_id,))
    names = []
    for row in cur.fetchall():
        if ctx.options['action'] == 'add' or ctx.options['action'] == 'list':
            continue
        if ctx.options['action'] == 'edit' or ctx.options['action'] == 'remove':
            if row[1] == 1:
                continue
        name = row[0] + (' (built-in)' if row[1] == 1 else '')
        names.append(name)
    cur.close()
    return names


class Reactions(commands.Cog):
    con: sqlite3.Connection = sqlite3.connect('neurobot.db')

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # TABLE: reactions
        # removed = whether the reaction was removed; 0 = no, 1 = self/other, 2 = bot, 3 = failed
        # nth = which reaction of this type it was (first = 1, second = 2, etc.)
        cur = self.con.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS reactions (
                message_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                removed INTEGER DEFAULT 0,
                nth INTEGER NOT NULL,
                time INTEGER NOT NULL,
                hit_groups TEXT,
                PRIMARY KEY (message_id, channel_id, guild_id, emoji, time)
            );
        ''')
        # TABLE: reaction_groups
        # match_type = the type of match to perform when reaction is added; 0 = substring, 1 = exact
        cur.execute('''
            CREATE TABLE IF NOT EXISTS reaction_groups (
                guild_id INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL,
                match TEXT NOT NULL,
                match_type INTEGER NOT NULL DEFAULT 0,
                builtin INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, name)
            );
        ''')
        # Add built-in reaction groups
        for guild_id in config['bot']['guilds']:
            cur.execute('''
                INSERT OR REPLACE INTO reaction_groups (guild_id, name, match, builtin)
                VALUES (?, ?, ?, ?)
            ''', (guild_id, 'Country Flags', r'[\U0001F1E6-\U0001F1FF]', 1))
        self.con.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        emoji = str(payload.emoji)
        reactions_of_type = [r for r in message.reactions if str(r.emoji) == emoji]
        removed = 0
        nth = len(reactions_of_type)
        now = time.time_ns() // 1_000_000
        # Check if the reaction matches any reaction groups
        cur = self.con.cursor()
        cur.execute('''
            SELECT name, match, match_type, enabled
            FROM reaction_groups
            WHERE guild_id = ?
        ''', (payload.guild_id,))
        # We keep track of all hit groups even if disabled
        hit_groups = []
        for row in cur.fetchall():
            name = row[0]
            match = row[1]
            match_type = row[2]
            enabled = row[3]

            if match_type == 0:
                if bool(re.search(match, emoji, re.IGNORECASE)):
                    hit_groups.append((name, enabled))
            elif match_type == 1:
                # Exact string match
                if emoji == match or bool(re.search(match, emoji.split(':')[1])):
                    hit_groups.append((name, enabled))
        # If any hit groups are enabled, remove the reaction, and keep track of which group hit first
        first_hit_group = None
        for (name, enabled) in hit_groups:
            first_hit_group = name
            if enabled:
                try:
                    await message.remove_reaction(payload.emoji, payload.member)
                    removed = 2
                except discord.Forbidden:
                    removed = 3
                break
        hit_groups_str = ','.join((f'{name}::{enabled}' if name != first_hit_group else f'{name}::*') for (name, enabled) in hit_groups)
        self.con.execute('''
            INSERT INTO reactions (message_id, channel_id, guild_id, user_id, emoji, removed, nth, time, hit_groups)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (payload.message_id, payload.channel_id, payload.guild_id, payload.user_id, emoji, removed, nth, now, hit_groups_str))
        self.con.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        emoji = str(payload.emoji)
        self.con.execute('''
            UPDATE reactions
            SET removed = 1
            WHERE message_id = ? AND channel_id = ? AND guild_id = ? AND user_id = ? AND emoji = ? AND removed = 0
        ''', (payload.message_id, payload.channel_id, payload.guild_id, payload.user_id, emoji))
        self.con.commit()

    def _format_reaction_groups(self, groups: list[str]):
        if len(groups) == 0:
            return 'No reaction groups found.'
        return 'Reaction groups:\n```\n' + '\n'.join(groups) + '\n```'

    def _match_type_to_int(self, match_type: str):
        if match_type == 'substring':
            return 0
        elif match_type == 'exact':
            return 1
        else:
            raise ValueError(f'Invalid match type string: {match_type}')
        
    def _int_to_match_type(self, match_type: int):
        if match_type == 0:
            return 'substring'
        elif match_type == 1:
            return 'exact'
        else:
            raise ValueError(f'Invalid match type integer: {match_type}')

    def _format_reaction_group(self, name: str, match: str, match_type: str, enabled: bool, builtin: bool):
        return f'Name: `{name}`\nMatch: `{match}`\nEnabled: {"Yes" if enabled else "No"}\nBuilt-in: {"Yes" if builtin else "No"}\nType: `{self._int_to_match_type(match_type)}`'
    
    async def list(self, ctx: discord.ApplicationContext):
        """
        Slash command action to list reaction groups.
        """
        cur = self.con.cursor()
        cur.execute('''
            SELECT name, enabled, builtin
            FROM reaction_groups
            WHERE guild_id = ?
        ''', (ctx.interaction.guild_id,))
        names = []
        for row in cur.fetchall():
            name = row[0] + (' (enabled)' if row[1] else ' (disabled)') + (' (built-in)' if row[2] == 1 else '')
            names.append(name)
        cur.close()
        await ctx.respond(self._format_reaction_groups(names), ephemeral=silent)

    async def info(self, ctx: discord.ApplicationContext, name: str):
        """
        Slash command action to view information about a reaction group.
        """
        name = name.removesuffix(' (built-in)')
        cur = self.con.cursor()
        cur.execute('''
            SELECT name, match, match_type, enabled, builtin
            FROM reaction_groups
            WHERE guild_id = ? AND name = ?
        ''', (ctx.interaction.guild_id, name))
        match = cur.fetchone()
        if match is None:
            await ctx.respond(f'Reaction group `{name}` not found.', ephemeral=silent)
            return
        cur.close()
        await ctx.respond(self._format_reaction_group(match[0], match[1], match[2], match[3], match[4]), ephemeral=silent)

    async def enable(self, ctx: discord.ApplicationContext, name: str):
        """
        Slash command action to enable a reaction group.
        """
        name = name.removesuffix(' (built-in)')
        self.con.execute('''
            UPDATE reaction_groups
            SET enabled = 1
            WHERE guild_id = ? AND name = ?
        ''', (ctx.interaction.guild_id, name))
        self.con.commit()
        await ctx.respond(f'Reaction group `{name}` enabled.', ephemeral=silent)

    async def disable(self, ctx: discord.ApplicationContext, name: str):
        """
        Slash command action to disable a reaction group.
        """
        name = name.removesuffix(' (built-in)')
        self.con.execute('''
            UPDATE reaction_groups
            SET enabled = 0
            WHERE guild_id = ? AND name = ?
        ''', (ctx.interaction.guild_id, name))
        self.con.commit()
        await ctx.respond(f'Reaction group `{name}` disabled.', ephemeral=silent)

    async def add(self, ctx: discord.ApplicationContext, name: str, match: str, match_type: str):
        """
        Slash command action to add a reaction group.
        """
        name = name.removesuffix(' (built-in)')
        # Check if group exists
        cur = self.con.cursor()
        cur.execute('''
            SELECT builtin
            FROM reaction_groups
            WHERE (guild_id = ? OR builtin = 1) AND name = ?
        ''', (ctx.interaction.guild_id, name))
        group = cur.fetchone()
        if group is not None:
            await ctx.respond(f'Reaction group `{name}` already exists.', ephemeral=silent)
            return
        # Group doesn't exist; we can add
        cur.execute('''
            INSERT INTO reaction_groups (guild_id, name, match, match_type)
            VALUES (?, ?, ?, ?)
        ''', (ctx.interaction.guild_id, name, match, self._match_type_to_int(match_type)))
        self.con.commit()
        cur.close()
        await ctx.respond(f'Reaction group `{name}` added with match `{match}`.', ephemeral=silent)

    async def edit(self, ctx: discord.ApplicationContext, name: str, match: str, match_type: str):
        """
        Slash command action to edit a reaction group.
        """
        name = name.removesuffix(' (built-in)')
        cur = self.con.cursor()
        # Check if group exists and isn't built-in
        cur.execute('''
            SELECT builtin
            FROM reaction_groups
            WHERE (guild_id = ? OR builtin = 1) AND name = ?
        ''', (ctx.interaction.guild_id, name))
        group = cur.fetchone()
        if group is None:
            await ctx.respond(f'Reaction group `{name}` not found.', ephemeral=silent)
            return
        if group[0]:
            await ctx.respond(f'Cannot edit built-in reaction group `{name}`.', ephemeral=silent)
            return
        # Group exists and isn't built-in; we can edit
        cur.execute('''
            UPDATE reaction_groups
            SET match = ?, match_type = ?
            WHERE guild_id = ? AND name = ?
        ''', (match, self._match_type_to_int(match_type), ctx.interaction.guild_id, name))
        self.con.commit()
        cur.close()
        await ctx.respond(f'Reaction group `{name}` edited with new match `{match}`.', ephemeral=silent)

    async def remove(self, ctx: discord.ApplicationContext, name: str):
        """
        Slash command action to remove a reaction group.
        """
        name = name.removesuffix(' (built-in)')
        cur = self.con.cursor()
        # Check if group exists and isn't built-in
        cur.execute('''
            SELECT builtin
            FROM reaction_groups
            WHERE (guild_id = ? OR builtin = 1) AND name = ?
        ''', (ctx.interaction.guild_id, name))
        group = cur.fetchone()
        if group is None:
            await ctx.respond(f'Reaction group `{name}` not found.', ephemeral=silent)
            return
        if group[0]:
            await ctx.respond(f'Cannot remove built-in reaction group `{name}`.', ephemeral=silent)
            return
        # Group exists and isn't built-in; we can remove
        cur.execute('''
            DELETE FROM reaction_groups
            WHERE guild_id = ? AND name = ?
        ''', (ctx.interaction.guild_id, name))
        self.con.commit()
        cur.close()
        await ctx.respond(f'Reaction group `{name}` removed.', ephemeral=silent)

    @commands.slash_command(guild_ids=command_guild_ids)
    @commands.has_permissions(manage_messages=True)
    async def reactiongroups(self,
                        ctx: discord.ApplicationContext,
                        action: discord.Option(str, choices=['list', 'info', 'enable', 'disable', 'add', 'edit', 'remove']),
                        name: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_group_names)),
                        match: discord.Option(str, required=False, help='The regex to match against, only used for add/remove'),
                        match_type: discord.Option(str, choices=['substring', 'exact'], required=False, default='substring')):
        if action == 'list':
            await self.list(ctx)
        elif action == 'info':
            await self.info(ctx, name)
        elif action == 'enable':
            await self.enable(ctx, name)
        elif action == 'disable':
            await self.disable(ctx, name)
        elif action == 'add':
            await self.add(ctx, name, match, match_type)
        elif action == 'edit':
            await self.edit(ctx, name, match, match_type)
        elif action == 'remove':
            await self.remove(ctx, name)
        else:
            await ctx.respond('Invalid subcommand', ephemeral=True)
        


def setup(bot: commands.Bot):
    bot.add_cog(Reactions(bot))
