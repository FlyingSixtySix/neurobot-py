import re
import sqlite3
import time
from typing import Callable

import discord
from discord.ext import bridge, commands
from loguru import logger

from main import command_guild_ids, config
from cog import Cog

silent = config['reactions']['silent']


async def get_group_names(ctx: discord.AutocompleteContext, builtin: bool = True):
    """
    Slash command autocomplete for reaction group names
    """
    cur = Reactions.con.cursor()
    cur.execute('''
        SELECT name, builtin
        FROM reaction_groups
        WHERE guild_id = ?
    ''', (ctx.interaction.guild_id,))
    names = []
    for row in cur.fetchall():
        if not builtin and row[1] == 1:
            continue
        name = row[0] + (' (built-in)' if row[1] == 1 else '')
        names.append(name)
    cur.close()
    return names


class Reactions(Cog):
    con = sqlite3.connect('neurobot.db')
    con.isolation_level = None

    REACTION_REMOVED_SELF = 1
    REACTION_REMOVED_BOT = 2
    REACTION_REMOVED_FAILED = 3

    MATCH_TYPE_SUBSTRING = 0
    MATCH_TYPE_EXACT = 1

    def __init__(self, bot: bridge.Bot):
        super().__init__(bot)
        # TABLE: reactions
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
            ''', (guild_id, 'Country Flags', r'[\U0001F1E6-\U0001F1FF]{2}', 1))
        cur.close()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        try:
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        except discord.NotFound:
            logger.error(f'Could not find message {payload.message_id} in channel {payload.channel_id}')
            return
        emoji = str(payload.emoji)
        removed = 0

        same_reaction = [r for r in message.reactions if str(r.emoji) == emoji]

        cur = self.con.cursor()

        cur.execute('''
            SELECT nth
            FROM reactions
            WHERE message_id = ? AND channel_id = ? AND guild_id = ? AND emoji = ?
        ''', (payload.message_id, payload.channel_id, payload.guild_id, emoji))
        rows = cur.fetchall()

        # If the user spam reacts/unreacts, the message cache doesn't have the
        # reaction yet, so assume its nth based on what we already have
        if len(same_reaction) == 0:
            if len(rows) == 0:
                nth = 1
            else:
                nth = len(rows) + 1
            logger.error(f'No reactions found for {emoji} on message {message.id}; assuming nth is {nth}')
        else:
            if len(rows) == same_reaction[0].count:
                nth = len(rows) + 1
            else:
                nth = same_reaction[0].count

        now = time.time_ns() // 1_000_000

        # Check if the reaction matches any reaction groups
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

            if match_type == Reactions.MATCH_TYPE_SUBSTRING:
                if bool(re.search(match, emoji, re.IGNORECASE)):
                    hit_groups.append((name, enabled))
            elif match_type == Reactions.MATCH_TYPE_EXACT:
                # Exact string match
                emoji_name = emoji.split(':')[1] if ':' in emoji else emoji
                if emoji == match or bool(re.search(match, emoji_name, re.IGNORECASE)):
                    hit_groups.append((name, enabled))
        # If any hit groups are enabled, remove the reaction, and keep track of which group hit first
        first_hit_group = None
        for (name, enabled) in hit_groups:
            first_hit_group = name
            if enabled:
                try:
                    await message.remove_reaction(payload.emoji, payload.member)
                    removed = Reactions.REACTION_REMOVED_BOT
                except discord.Forbidden:
                    removed = Reactions.REACTION_REMOVED_FAILED
                break
        hit_groups_str = ','.join((f'{name}::{enabled}' if name != first_hit_group else f'{name}::*') for (name, enabled) in hit_groups)
        self.con.execute('''
            INSERT INTO reactions (message_id, channel_id, guild_id, user_id, emoji, removed, nth, time, hit_groups)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (payload.message_id, payload.channel_id, payload.guild_id, payload.user_id, emoji, removed, nth, now, hit_groups_str))

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        emoji = str(payload.emoji)
        self.con.execute('''
            UPDATE reactions
            SET removed = ?
            WHERE message_id = ? AND channel_id = ? AND guild_id = ? AND user_id = ? AND emoji = ? AND removed = 0
        ''', (Reactions.REACTION_REMOVED_SELF, payload.message_id, payload.channel_id, payload.guild_id, payload.user_id, emoji))

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

    @bridge.bridge_group(invoke_without_command=False, aliases=['rg'], guild_ids=command_guild_ids)
    async def reactiongroups(self, ctx: bridge.BridgeContext):
        pass

    @bridge.bridge_group(invoke_without_command=False, aliases=['r'], guild_ids=command_guild_ids)
    async def reactions(self, ctx: bridge.BridgeContext):
        pass

    @reactiongroups.command()
    @bridge.has_permissions(manage_messages=True)
    async def list(self, ctx: bridge.BridgeExtContext):
        """
        List all reaction groups
        """
        cur = self.con.cursor()
        cur.execute('''
            SELECT name, enabled, builtin
            FROM reaction_groups
            WHERE guild_id = ?
        ''', (ctx.guild.id,))
        names = []
        for row in cur.fetchall():
            name = row[0] + (' (enabled)' if row[1] else ' (disabled)') + (' (built-in)' if row[2] == 1 else '')
            names.append(name)
        cur.close()
        await ctx.respond(self._format_reaction_groups(names), ephemeral=silent)

    @reactiongroups.command()
    @bridge.has_permissions(manage_messages=True)
    @discord.option('name', description='The name of the reaction group', required=True, autocomplete=discord.utils.basic_autocomplete(get_group_names))
    async def info(self, ctx: bridge.BridgeExtContext, *, name: str):
        """
        View information about a reaction group
        """
        name = name.removesuffix(' (built-in)')
        cur = self.con.cursor()
        cur.execute('''
            SELECT name, match, match_type, enabled, builtin
            FROM reaction_groups
            WHERE guild_id = ? AND LOWER(name) = ?
        ''', (ctx.guild.id, name.lower()))
        match = cur.fetchone()
        if match is None:
            await ctx.respond(f'Reaction group `{name}` not found', ephemeral=silent)
            return
        cur.close()
        await ctx.respond(self._format_reaction_group(match[0], match[1], match[2], match[3], match[4]), ephemeral=silent)

    @reactiongroups.command()
    @bridge.has_permissions(manage_messages=True)
    @discord.option('name', description='The name of the reaction group', required=True, autocomplete=discord.utils.basic_autocomplete(get_group_names))
    async def enable(self, ctx: bridge.BridgeExtContext, *, name: str):
        """
        Enable a reaction group
        """
        name = name.removesuffix(' (built-in)')
        # Check if group exists
        cur = self.con.cursor()
        cur.execute('''
            SELECT builtin
            FROM reaction_groups
            WHERE (guild_id = ? OR builtin = 1) AND LOWER(name) = ?
        ''', (ctx.guild.id, name.lower()))
        group = cur.fetchone()
        if group is None:
            await ctx.respond(f'Reaction group `{name}` does not exist', ephemeral=silent)
            return
        # Group exists; we can enable
        self.con.execute('''
            UPDATE reaction_groups
            SET enabled = 1
            WHERE guild_id = ? AND LOWER(name) = ?
        ''', (ctx.guild.id, name.lower()))
        await ctx.respond(f'Reaction group `{name}` enabled', ephemeral=silent)

    @reactiongroups.command()
    @bridge.has_permissions(manage_messages=True)
    @discord.option('name', description='The name of the reaction group', required=True, autocomplete=discord.utils.basic_autocomplete(get_group_names))
    async def disable(self, ctx: bridge.BridgeExtContext, *, name: str):
        """
        Disable a reaction group
        """
        name = name.removesuffix(' (built-in)')
        # Check if group exists
        cur = self.con.cursor()
        cur.execute('''
            SELECT builtin
            FROM reaction_groups
            WHERE (guild_id = ? OR builtin = 1) AND LOWER(name) = ?
        ''', (ctx.guild.id, name.lower()))
        group = cur.fetchone()
        if group is None:
            await ctx.respond(f'Reaction group `{name}` does not exist', ephemeral=silent)
            return
        # Group exists; we can disable
        self.con.execute('''
            UPDATE reaction_groups
            SET enabled = 0
            WHERE guild_id = ? AND LOWER(name) = ?
        ''', (ctx.guild.id, name.lower()))
        await ctx.respond(f'Reaction group `{name}` disabled', ephemeral=silent)

    @reactiongroups.command()
    @bridge.has_permissions(manage_messages=True)
    @discord.option('name', description='The name of the reaction group', required=True)
    @discord.option('match', description='The regex to match against', required=True)
    @discord.option('match_type', description='The type of match to use', required=True, choices=['substring', 'exact'])
    async def add(self, ctx: bridge.BridgeExtContext, name: str, match: str, match_type: str):
        """
        Add a reaction group
        """
        name = name.removesuffix(' (built-in)')
        # Check if group exists
        cur = self.con.cursor()
        cur.execute('''
            SELECT builtin
            FROM reaction_groups
            WHERE (guild_id = ? OR builtin = 1) AND LOWER(name) = ?
        ''', (ctx.guild.id, name.lower()))
        group = cur.fetchone()
        if group is not None:
            await ctx.respond(f'Reaction group `{name}` already exists', ephemeral=silent)
            return
        # Group doesn't exist; we can add
        cur.execute('''
            INSERT INTO reaction_groups (guild_id, name, match, match_type)
            VALUES (?, ?, ?, ?)
        ''', (ctx.guild.id, name, match, self._match_type_to_int(match_type)))
        cur.close()
        await ctx.respond(f'Reaction group `{name}` added with match `{match}`', ephemeral=silent)

    @reactiongroups.command()
    @bridge.has_permissions(manage_messages=True)
    @discord.option('name', description='The name of the reaction group', required=True, autocomplete=discord.utils.basic_autocomplete(lambda i: get_group_names(i, False)))
    @discord.option('match', description='The regex to match against', required=True)
    @discord.option('match_type', description='The type of match to use', required=True, choices=['substring', 'exact'])
    async def edit(self, ctx: bridge.BridgeExtContext, name: str, match: str, match_type: str):
        """
        Edit a reaction group
        """
        name = name.removesuffix(' (built-in)')
        cur = self.con.cursor()
        # Check if group exists and isn't built-in
        cur.execute('''
            SELECT builtin
            FROM reaction_groups
            WHERE (guild_id = ? OR builtin = 1) AND LOWER(name) = ?
        ''', (ctx.guild.id, name.lower()))
        group = cur.fetchone()
        if group is None:
            await ctx.respond(f'Reaction group `{name}` not found', ephemeral=silent)
            return
        if group[0]:
            await ctx.respond(f'Cannot edit built-in reaction group `{name}`', ephemeral=silent)
            return
        # Group exists and isn't built-in; we can edit
        cur.execute('''
            UPDATE reaction_groups
            SET match = ?, match_type = ?
            WHERE guild_id = ? AND LOWER(name) = ?
        ''', (match, self._match_type_to_int(match_type), ctx.guild.id, name.lower()))
        cur.close()
        await ctx.respond(f'Reaction group `{name}` edited with new match `{match}`', ephemeral=silent)

    @reactiongroups.command(aliases=['delete'])
    @bridge.has_permissions(manage_messages=True)
    @discord.option('name', description='The name of the reaction group', required=True, autocomplete=discord.utils.basic_autocomplete(lambda i: get_group_names(i, False)))
    async def remove(self, ctx: bridge.BridgeExtContext, *, name: str):
        """
        Remove a reaction group
        """
        name = name.removesuffix(' (built-in)')
        cur = self.con.cursor()
        # Check if group exists and isn't built-in
        cur.execute('''
            SELECT builtin
            FROM reaction_groups
            WHERE (guild_id = ? OR builtin = 1) AND LOWER(name) = ?
        ''', (ctx.guild.id, name.lower()))
        group = cur.fetchone()
        if group is None:
            await ctx.respond(f'Reaction group `{name}` not found.', ephemeral=silent)
            return
        if group[0]:
            await ctx.respond(f'Cannot remove built-in reaction group `{name}`', ephemeral=silent)
            return
        # Group exists and isn't built-in; we can remove
        cur.execute('''
            DELETE FROM reaction_groups
            WHERE guild_id = ? AND LOWER(name) = ?
        ''', (ctx.guild.id, name.lower()))
        cur.close()
        await ctx.respond(f'Reaction group `{name}` removed', ephemeral=silent)

    @reactions.command()
    @bridge.has_permissions(manage_messages=True)
    @discord.option('message_input', description='A link or ID of the message', required=True)
    @discord.option('emoji', description='The name of the emoji to filter by', required=False)
    @discord.option('user', description='The name or ID of the user to filter by', required=False)
    async def first(self, ctx: bridge.BridgeExtContext | discord.ApplicationContext, message_input: str, filter_emoji: str = None, filter_user: str = None):
        """
        View who reacted to a message first
        """

        if 'http' in message_input:
            message_id = int(message_input.split('/')[-1])
        else:
            if not message_input.isnumeric():
                await ctx.respond('Invalid message input', ephemeral=silent)
                return
            message_id = int(message_input)

        cur = self.con.cursor()
        query = '''
            SELECT emoji, user_id, time, channel_id
            FROM reactions
            WHERE message_id = ? AND guild_id = ? AND nth = 1
        '''
        params = (message_id, ctx.guild.id)

        if filter_emoji is not None:
            query += ' AND emoji LIKE ?'
            params += ('%' + filter_emoji + '%',)

        if filter_user is not None:
            if filter_user.isnumeric():
                query += ' AND user_id = ?'
                params += (int(filter_user),)
            else:
                member_lambda: Callable[[discord.Member], bool] = (lambda m:
                                      (filter_user.lower() in m.name.lower()) or
                                      (filter_user.lower() in m.display_name.lower()))
                members = list(filter(member_lambda, ctx.guild.members))
                if len(members) == 0:
                    # members = list(filter(member_lambda, await ctx.interaction.guild.fetch_members(limit=None).flatten()))
                    # if len(members) == 0:
                    await ctx.respond('No users found by that filter', ephemeral=silent)
                    return
                elif len(members) > 1:
                    query += 'AND user_id IN ('
                    for member in members:
                        query += '?,'
                        params += (member.id,)
                    query = query.removesuffix(',') + ')'
                else:
                    query += ' AND user_id = ?'
                    params += (members[0].id,)

        query += ' ORDER BY time ASC'

        cur.execute(query, params)
        reactions = cur.fetchall()
        if len(reactions) == 0:
            await ctx.respond('No reactions found', ephemeral=silent)
            return

        # getting the channel ID from any reaction should work
        channel_id = reactions[0][3]

        title = 'First reactions'
        link_to_message = f'[Jump to message](https://discord.com/channels/{ctx.guild.id}/{channel_id}/{message_id})'
        description = f'{link_to_message}\n\n'
        color = 0xAA8ED6

        # chunks for the embed description
        buffer = ''
        # whether to use followup or send a single embed
        followup = False

        # keep track of emoji/user pairs for multiple reactions of the same
        #  type from the same user
        already_processed = []

        for row in reactions:
            emoji = row[0]
            user_id = row[1]

            if (emoji, user_id) in already_processed:
                continue

            emoji_url = None

            if '<' in emoji:
                # Custom emoji
                emoji_url = 'https://cdn.discordapp.com/emojis/' + emoji.split(':')[2].removesuffix('>')
                if emoji.startswith('<a:'):
                    emoji_url += '.gif'
                else:
                    emoji_url += '.png'

            user = await self.bot.get_or_fetch_user(user_id)

            same_reactions = list(filter(lambda r: r[0] == emoji and r[1] == user_id, reactions))
            if len(same_reactions) > 1:
                # since there's multiple of this emoji type from the same user,
                #  keep track of it so we don't process it again
                already_processed.append((same_reactions[0][0], same_reactions[0][1]))
                buffer += f'{len(same_reactions)}x '

            timestamps = list(map(lambda r: r[2] // 1000, same_reactions))

            buffer = ''

            # 01:23:45 AM
            buffer += ', '.join(f'<t:{timestamp}:T>' for timestamp in timestamps)

            if ':' in emoji:
                emoji = ('a' if emoji.startswith('<a') else '') + ':' + emoji.split(':')[1] + ':'

            if emoji_url is not None:
                buffer += f'[`{emoji}`]({emoji_url})'
            else:
                buffer += f'`{emoji}`'

            buffer += f' by {user.mention}' + (f' (**{len(same_reactions)}x**)' if len(same_reactions) > 1 else '') + '\n'

            if len(description) + len(buffer) > 4096:
                embed = discord.Embed(title=title, description=description, color=color)

                await ctx.respond(embed=embed)

                description = f'{link_to_message}\n\n'
                followup = True

            description += buffer

        embed = discord.Embed(title=title, description=description, color=color)

        if followup:
            if isinstance(ctx, bridge.BridgeExtContext):
                await ctx.send(embed=embed)
            else:
                await ctx.followup.send(embed=embed)
        else:
            await ctx.respond(embed=embed)


def setup(bot: bridge.Bot):
    bot.add_cog(Reactions(bot))
