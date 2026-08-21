import json
import os
import unittest

os.environ.setdefault("WHATSAPP_TOKEN", "test")
os.environ.setdefault("WHATSAPP_PHONE_ID", "test")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test")

from aisha.tools import TOOL_DEFINITIONS, ToolContext, execute_tool


class ToolDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_tool(self):
        ctx = ToolContext(phone="1", scheduler=None, user_tz="UTC", base_url="http://x")
        result = await execute_tool("does_not_exist", "{}", ctx)
        self.assertIn("Unknown tool", result)

    async def test_invalid_json_arguments(self):
        ctx = ToolContext(phone="1", scheduler=None, user_tz="UTC", base_url="http://x")
        result = await execute_tool("list_reminders", "{not-json", ctx)
        payload = json.loads(result)
        self.assertIn("error", payload)

    def test_required_tools_registered(self):
        names = {t.get("name") for t in TOOL_DEFINITIONS if t.get("type") == "function"}
        for required in (
            "create_reminder",
            "edit_reminder",
            "save_memory",
            "search_memory",
            "list_memories",
            "forget_memory",
            "analyze_youtube_video",
            "download_video",
            "search_x",
            "draw_radius_map",
        ):
            self.assertIn(required, names)

    def test_draw_radius_map_mentions_whatsapp_pin(self):
        tool = next(t for t in TOOL_DEFINITIONS if t.get("name") == "draw_radius_map")
        self.assertIn("WhatsApp location pins", tool["description"])


if __name__ == "__main__":
    unittest.main()
