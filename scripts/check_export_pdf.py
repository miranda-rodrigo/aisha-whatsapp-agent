"""Synthetic PDF smoke check. No real chats, model calls, or WhatsApp sends.

Run: python -m scripts.check_export_pdf [output-directory]
"""

import asyncio
import json
import re
import resource
import sys
import tempfile
import time
from pathlib import Path

import pymupdf

from aisha.chat_export.pdf import render_pdf


def fixture():
    messages = [
        dict(
            id="msg-system",
            date="13/11/2026",
            time="09:00",
            sender="[sistema]",
            text="Conversa de demonstração criada.",
        )
    ]
    for i in range(24):
        messages.append(
            dict(
                id=f"msg-demo-{i}",
                date="13/11/2026" if i < 12 else "14/11/2026",
                time=f"10:{i:02}",
                sender=["Ana", "Bruno", "Clara"][i % 3],
                text=f"Mensagem {i}: reunião às 14h. Ação, revisão e confirmação 😊.\nSegunda linha preservada.",
            )
        )
    messages[4]["text"] = "áudio omitido"
    messages[8]["text"] = (
        "INICIO_LONGA\n"
        + "\n".join(
            f"Linha extensa {i:03}: planejamento e revisão com todos os participantes."
            for i in range(95)
        )
        + "\nFIM_LONGA"
    )
    return messages, {
        "claims": [
            {
                "text": "O grupo discutiu uma reunião às 14h.",
                "ids": ["msg-demo-0", "msg-demo-1"],
            }
        ]
    }


async def main():
    messages, analysis = fixture()
    start = time.monotonic()
    before = set(Path(tempfile.gettempdir()).glob("aisha-pdf-*"))
    data = await render_pdf(messages, analysis, "Conversa de demonstração")
    assert set(Path(tempfile.gettempdir()).glob("aisha-pdf-*")) == before
    doc = pymupdf.open(stream=data, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    normalized = " ".join(re.sub(r"Aisha · \d+ / \d+", "", text).split())
    for message in messages:
        for field in ("id", "sender", "date", "time", "text"):
            for line in message[field].splitlines():
                assert " ".join(line.split()) in normalized, (message["id"], field)
    assert all(
        text.index(a["id"], text.index("Conversa ·"))
        < text.index(b["id"], text.index("Conversa ·"))
        for a, b in zip(messages, messages[1:])
    )
    for marker in (
        "INICIO_LONGA",
        "FIM_LONGA",
        "Linha extensa 094",
        "Mensagem 23",
        "Mídia não processada",
    ):
        assert marker in text, marker
    assert any(
        link["kind"] in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED)
        and link.get("page", -1) >= 0
        for page in doc
        for link in page.get_links()
    )
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "conversa-analisada.pdf").write_bytes(data)
        for i, page in enumerate(doc):
            page.get_pixmap(matrix=pymupdf.Matrix(1, 1)).save(out / f"page-{i + 1}.png")
    print(
        json.dumps(
            {
                "result": "PASS",
                "pages": len(doc),
                "bytes": len(data),
                "seconds": round(time.monotonic() - start, 2),
                "child_maxrss": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
