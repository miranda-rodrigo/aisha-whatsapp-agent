"""Explicit operator setup for the private reduced-image bucket (idempotent)."""

import asyncio

from aisha import supabase_http
from aisha.chat_export.assets import BUCKET, HEADERS, ROOT
from aisha.supabase_http import get_client


async def main():
    try:
        r = await get_client().get(f"{ROOT}/bucket/{BUCKET}", headers=HEADERS)
        if r.status_code in (400, 404) and r.json().get("error") in (
            "not_found",
            "Not Found",
            "Bucket not found",
        ):
            r = await get_client().post(
                f"{ROOT}/bucket",
                headers=HEADERS,
                json={
                    "id": BUCKET,
                    "name": BUCKET,
                    "public": False,
                    "file_size_limit": 4 * 1024 * 1024,
                    "allowed_mime_types": ["image/jpeg"],
                },
            )
            if not r.is_success:
                raise RuntimeError(
                    "Configure SUPABASE_STORAGE_KEY com permissão de servidor para criar e operar o bucket privado."
                )
            r.raise_for_status()
        r = await get_client().get(f"{ROOT}/bucket/{BUCKET}", headers=HEADERS)
        r.raise_for_status()
        assert r.json()["public"] is False, "Bucket must be private"
        print("PRIVATE_IMAGE_BUCKET=PASS")
    finally:
        await supabase_http.aclose()


if __name__ == "__main__":
    asyncio.run(main())
