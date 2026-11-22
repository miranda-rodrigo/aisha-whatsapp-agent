"""Private filesystem adapters used only in a playground process."""
import asyncio
import copy
import json
from collections import defaultdict
from pathlib import Path


class LocalStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.guards = defaultdict(asyncio.Lock)
        self.record = None

    async def current(self, phone, record):
        return self.record is not None and self.record["revision"] == record["revision"]

    async def update(self, phone, record):
        self.record = copy.deepcopy(record)
        self.directory.joinpath("state.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True


class LocalAssets:
    def __init__(self, directory):
        self.directory = Path(directory) / "assets"
        self.directory.mkdir(exist_ok=True)

    async def upload(self, phone, record, digest, data):
        name = digest + ".jpg"
        self.directory.joinpath(name).write_bytes(data)
        return name

    async def download(self, phone, name):
        if Path(name).name != name:
            raise ValueError("Invalid local asset name")
        return self.directory.joinpath(name).read_bytes()
