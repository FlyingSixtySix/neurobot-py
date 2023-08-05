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
- `neurobot.db` is only used by the `reactions` cog at the moment. If deleted, it will be recreated on bot init.

## Contributing

Contact vanyilla on Discord before contributing any features.