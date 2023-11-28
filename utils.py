from main import config


def get_guild_config(guild_id: int, cog: str) -> dict or None:
    """
    Returns the config for the given guild and cog.
    """
    if cog not in config:
        return None
    if str(guild_id) not in config[cog]:
        return None
    return config[cog][str(guild_id)]


def get_dual_timestamps(timestamp: str) -> str:
    """
    Returns a string with the formatted date and long time of the given timestamp.
    """
    return f'<t:{timestamp}:d> <t:{timestamp}:T>'
