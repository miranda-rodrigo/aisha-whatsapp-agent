"""Private reduced images only; no audio, ZIP or PDF persistence."""

import hashlib
import re
import time

from aisha.config import SUPABASE_URL
from aisha.supabase_http import HEADERS, get_client

BUCKET = "whatsapp-export-images"
ROOT = f"{SUPABASE_URL}/storage/v1"


def owner(phone):
    return hashlib.sha256(phone.encode()).hexdigest()


def folder(phone, record):
    from datetime import datetime

    expiry = int(datetime.fromisoformat(record["expires_at"]).timestamp())
    return f"{owner(phone)}/{expiry}-{record['revision']}"


async def upload(phone, record, digest, data):
    path = f"{folder(phone, record)}/{digest}.jpg"
    response = await get_client().post(
        f"{ROOT}/object/{BUCKET}/{path}",
        headers={**HEADERS, "Content-Type": "image/jpeg", "x-upsert": "true"},
        content=data,
    )
    response.raise_for_status()
    return path


async def download(phone, path):
    if not path.startswith(owner(phone) + "/") or not re.fullmatch(
        r"[a-f0-9]+/[0-9]+-[a-f0-9]+/[a-f0-9]+\.jpg", path
    ):
        raise ValueError("Invalid private image ownership")
    response = await get_client().get(
        f"{ROOT}/object/authenticated/{BUCKET}/{path}", headers=HEADERS
    )
    response.raise_for_status()
    if len(response.content) > 4 * 1024 * 1024:
        raise ValueError("Invalid reduced image size")
    return response.content


async def entries(prefix):
    results = []
    offset = 0
    while True:
        response = await get_client().post(
            f"{ROOT}/object/list/{BUCKET}",
            headers=HEADERS,
            json={
                "prefix": prefix,
                "limit": 100,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        page = response.json()
        results.extend(page)
        if len(page) < 100:
            return results
        offset += 100


async def remove_prefix(prefix):
    paths = []
    for entry in await entries(prefix):
        path = prefix + "/" + entry["name"] if prefix else entry["name"]
        if entry.get("id") is None:
            await remove_prefix(path)
        else:
            paths.append(path)
    for start in range(0, len(paths), 100):
        response = await get_client().request(
            "DELETE",
            f"{ROOT}/object/{BUCKET}",
            headers=HEADERS,
            json={"prefixes": paths[start : start + 100]},
        )
        response.raise_for_status()


async def cleanup():
    for account in await entries(""):
        if not re.fullmatch(r"[a-f0-9]{64}", account["name"]):
            continue
        for revision in await entries(account["name"]):
            match = re.fullmatch(r"(\d+)-[a-f0-9]{32}", revision["name"])
            if match and int(match[1]) <= time.time():
                await remove_prefix(account["name"] + "/" + revision["name"])
