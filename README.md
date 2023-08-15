# NeuroBot

Discord bot for Neuro-sama Headquarters

## Running

Requirements:
- Python >=3.8
- [Pipenv](https://pipenv.pypa.io/en/latest/)

```sh
# Clone or download repo
git clone https://github.com/FlyingSixtySix/neurobot
cd neurobot

# Configure config.toml as necessary
cp config.example.toml config.toml

# Install dependencies in a Pipenv virtual environment
pipenv install

# Run from the current shell
pipenv run python main.py
# ... Or launch a virtual environment shell and run
pipenv shell
python main.py
```

## Additional

- There is no current way to disable cogs on start; simply unload after the fact with the `manage` command.
- The `jp`, `swarm`, and `pendingrole` sections in `config.toml` work based on their guild ID being in the name, like `[jp.112233445566778899]`. If you don't want those features, put `[jp]`, `[swarm]`, and `[pendingrole]` on their own lines.
- `neurobot.db` is used by the `jp` and `reactions` cogs. If deleted, it will be recreated on bot init.

## Examples
### Barebones Cog
```py
from discord.ext import bridge

from cog import Cog


class MyCog(Cog):
    pass


def setup(bot: bridge.Bot):
    bot.add_cog(MyCog(bot))

```
### Command w/ Option
```py
import discord
from discord.ext import bridge

from main import command_guild_ids
from cog import Cog


class Pinger(Cog):
    @bridge.bridge_command(guild_ids=command_guild_ids)
    @discord.option('uppercase', description='Makes the response uppercase', choices=['True', 'False'])
    async def ping(self, ctx: bridge.BridgeExtContext, uppercase: str = 'False'):
        """
        Response with "Pong!" or "PONG!"
        """
        await ctx.respond('PONG!' if uppercase == 'True' else 'Pong!')


def setup(bot: bridge.Bot):
    bot.add_cog(Pinger(bot))

```

## Contributing

Contributions are not being accepted at this time. Sorry!
