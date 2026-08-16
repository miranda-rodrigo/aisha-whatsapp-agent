"""Testes unitários do armazenamento de memórias."""

import sys
from types import ModuleType
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from tests.aisha_unit._helpers import async_http_client, http_response

if "openai" not in sys.modules:
    sys.modules["openai"] = ModuleType("openai")
if not hasattr(sys.modules["openai"], "AsyncOpenAI"):
    sys.modules["openai"].AsyncOpenAI = MagicMock(return_value=MagicMock())

from aisha.skills import memory_store


class CosineTests(TestCase):
    def test_cosine_handles_invalid_and_orthogonal_vectors(self):
        self.assertEqual(memory_store._cosine([], []), 0.0)
        self.assertEqual(memory_store._cosine([1], [1, 2]), 0.0)
        self.assertEqual(memory_store._cosine([0, 0], [1, 1]), 0.0)
        self.assertEqual(memory_store._cosine([1, 0], [0, 1]), 0.0)

    def test_cosine_returns_direction_similarity(self):
        self.assertAlmostEqual(
            memory_store._cosine([1, 1], [2, 2]), 1.0
        )


class MemoryStoreTests(IsolatedAsyncioTestCase):
    async def test_save_rejects_blank_memory_before_external_calls(self):
        with patch.object(memory_store, "_embed", AsyncMock()) as embed:
            with self.assertRaisesRegex(ValueError, "Memória vazia"):
                await memory_store.save_memory("5511", "   ")

        embed.assert_not_awaited()

    async def test_save_trims_content_and_posts_embedding(self):
        response = http_response(json_data=[{"id": "m1", "content": "lembrar"}])
        factory, client = async_http_client()
        client.post.return_value = response

        with (
            patch.object(memory_store, "_embed", AsyncMock(return_value=[0.1, 0.2])),
            patch.object(memory_store.httpx, "AsyncClient", factory),
        ):
            row = await memory_store.save_memory("5511", "  lembrar  ")

        self.assertEqual(row["id"], "m1")
        payload = client.post.await_args.kwargs["json"]
        self.assertEqual(payload["content"], "lembrar")
        self.assertEqual(payload["embedding"], [0.1, 0.2])
        self.assertEqual(payload["phone"], "5511")
        response.raise_for_status.assert_called_once()

    async def test_search_ranks_filters_and_removes_embeddings(self):
        rows = [
            {
                "id": "weak",
                "content": "fraco",
                "embedding": [0, 1],
                "created_at": None,
            },
            {
                "id": "best",
                "content": "forte",
                "embedding": [1, 0],
                "created_at": "today",
            },
            {
                "id": "second",
                "content": "médio",
                "embedding": [0.8, 0.6],
                "created_at": "yesterday",
            },
        ]
        response = http_response(json_data=rows)
        factory, client = async_http_client(response)

        with (
            patch.object(memory_store, "_embed", AsyncMock(return_value=[1, 0])),
            patch.object(memory_store.httpx, "AsyncClient", factory),
        ):
            results = await memory_store.search_memories("5511", " consulta ")

        self.assertEqual([row["id"] for row in results], ["best", "second"])
        self.assertEqual(results[0]["similarity"], 1.0)
        self.assertNotIn("embedding", results[0])
        self.assertEqual(client.get.await_args.kwargs["params"]["phone"], "eq.5511")

    async def test_blank_search_returns_without_embedding_or_http(self):
        factory, _ = async_http_client()
        with (
            patch.object(memory_store, "_embed", AsyncMock()) as embed,
            patch.object(memory_store.httpx, "AsyncClient", factory),
        ):
            result = await memory_store.search_memories("5511", " ")

        self.assertEqual(result, [])
        embed.assert_not_awaited()
        factory.assert_not_called()

    async def test_delete_by_query_delegates_to_matched_id(self):
        delete_by_query = memory_store.delete_memory
        with (
            patch.object(
                memory_store,
                "search_memories",
                AsyncMock(return_value=[{"id": "m7"}]),
            ) as search,
            patch.object(
                memory_store, "delete_memory", AsyncMock(return_value=1)
            ) as delete,
        ):
            result = await delete_by_query(
                "5511", content_query="preferência"
            )

        self.assertEqual(result, 1)
        search.assert_awaited_once_with("5511", "preferência", limit=1)
        delete.assert_awaited_once_with("5511", memory_id="m7")
