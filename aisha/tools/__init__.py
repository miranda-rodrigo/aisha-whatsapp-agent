"""Tool definitions and dispatcher for the Aisha agentic loop.

Each tool is a thin wrapper around the existing skill functions in aisha/skills/.
The TOOL_DEFINITIONS list provides the JSON schemas that the OpenAI Responses API
expects, and execute_tool dispatches a tool call to the correct wrapper.
"""

import json
import logging
from dataclasses import dataclass

from aisha.tools.reminder import (
    tool_create_reminder,
    tool_list_reminders,
    tool_cancel_reminder,
)
from aisha.tools.scheduled_task import (
    tool_create_scheduled_task,
    tool_list_scheduled_tasks,
    tool_cancel_scheduled_task,
)
from aisha.tools.youtube import tool_analyze_youtube_video
from aisha.tools.webpage import tool_read_webpage
from aisha.tools.video_download import tool_download_video
from aisha.tools.profile import (
    tool_set_personal_context,
    tool_set_language,
    tool_get_my_profile,
)

log = logging.getLogger(__name__)


@dataclass
class ToolContext:
    """Runtime context passed to every tool execution."""
    phone: str
    scheduler: object  # AsyncScheduler
    user_tz: str
    base_url: str


TOOL_DEFINITIONS: list[dict] = [
    {"type": "web_search"},
    {"type": "image_generation"},
    {
        "type": "function",
        "name": "create_reminder",
        "description": (
            "Create a reminder for the user. The reminder will fire at the specified "
            "time with advance notice. Supports one-time and recurring reminders. "
            "Use this when the user asks to be reminded of something."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Short description of the reminder, e.g. 'Reunião com João'",
                },
                "datetime_iso": {
                    "type": "string",
                    "description": (
                        "When the event happens in ISO 8601 (YYYY-MM-DDTHH:MM:SS) "
                        "in the user's local timezone. Leave empty for recurring-only reminders."
                    ),
                },
                "is_recurring": {
                    "type": "boolean",
                    "description": "True if the reminder repeats on a schedule",
                },
                "cron_expression": {
                    "type": "string",
                    "description": (
                        "5-field cron expression for recurring reminders "
                        "(minute hour day-of-month month day-of-week). "
                        "Only required when is_recurring is true."
                    ),
                },
                "lead_minutes": {
                    "type": "integer",
                    "description": "Minutes of advance notice before the event (default: 15)",
                },
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_reminders",
        "description": "List all active reminders for the user.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "cancel_reminder",
        "description": "Cancel an active reminder by its number in the list.",
        "parameters": {
            "type": "object",
            "properties": {
                "reminder_number": {
                    "type": "integer",
                    "description": "1-based index of the reminder to cancel (from the list)",
                },
            },
            "required": ["reminder_number"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "create_scheduled_task",
        "description": (
            "Create a recurring scheduled task that runs automatically on a cron schedule. "
            "Each execution performs a web search and sends the AI-generated result to the user. "
            "Use this for periodic reports, news summaries, market updates, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Short name for the task, e.g. 'Relatório Irã'",
                },
                "prompt": {
                    "type": "string",
                    "description": (
                        "Full instruction for the AI agent to execute each time. "
                        "Should be self-contained with all context (topic, format, language)."
                    ),
                },
                "cron_expression": {
                    "type": "string",
                    "description": (
                        "5-field cron expression (minute hour day-of-month month day-of-week). "
                        "E.g. '0 9 * * 1' for every Monday at 09:00."
                    ),
                },
            },
            "required": ["name", "prompt", "cron_expression"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_scheduled_tasks",
        "description": "List all active scheduled tasks for the user.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "cancel_scheduled_task",
        "description": "Cancel a scheduled task by its number in the list.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_number": {
                    "type": "integer",
                    "description": "1-based index of the task to cancel (from the list)",
                },
            },
            "required": ["task_number"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "analyze_youtube_video",
        "description": (
            "Analyze a YouTube video: summarize, transcribe, extract key points, etc. "
            "Use this when the user sends a YouTube URL or asks about a YouTube video."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full YouTube URL",
                },
                "instruction": {
                    "type": "string",
                    "description": (
                        "What to do with the video: 'resume', 'transcreve', "
                        "'quais os pontos principais?', etc."
                    ),
                },
            },
            "required": ["url", "instruction"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "read_webpage",
        "description": (
            "Read and process the content of any public webpage. "
            "Use this when the user sends a non-YouTube URL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL of the webpage",
                },
                "instruction": {
                    "type": "string",
                    "description": (
                        "What to do with the page content: 'resume', 'traduz para inglês', "
                        "'extrai os dados', etc. If empty, a summary will be generated."
                    ),
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "download_video",
        "description": (
            "Download a video from YouTube or X/Twitter and generate a temporary download link. "
            "The link expires in 30 minutes. Max resolution: 720p."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "YouTube or X/Twitter video URL",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "set_personal_context",
        "description": (
            "Save personal context the user shares about themselves (name, job, preferences, "
            "personality instructions). This is remembered permanently across all conversations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "The personal context to save, e.g. 'Sou programador Python, moro em Fortaleza'",
                },
            },
            "required": ["context"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "set_language",
        "description": "Change the user's preferred conversation language.",
        "parameters": {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "Language name, e.g. 'english', 'português', 'español'",
                },
            },
            "required": ["language"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_my_profile",
        "description": (
            "Retrieve the user's full profile: personal context, preferred language, timezone, "
            "active reminders, scheduled tasks, and usage statistics."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
]

_FUNCTION_TOOLS = [t for t in TOOL_DEFINITIONS if t.get("type") == "function"]

_DISPATCH = {
    "create_reminder": tool_create_reminder,
    "list_reminders": tool_list_reminders,
    "cancel_reminder": tool_cancel_reminder,
    "create_scheduled_task": tool_create_scheduled_task,
    "list_scheduled_tasks": tool_list_scheduled_tasks,
    "cancel_scheduled_task": tool_cancel_scheduled_task,
    "analyze_youtube_video": tool_analyze_youtube_video,
    "read_webpage": tool_read_webpage,
    "download_video": tool_download_video,
    "set_personal_context": tool_set_personal_context,
    "set_language": tool_set_language,
    "get_my_profile": tool_get_my_profile,
}


async def execute_tool(name: str, arguments_json: str, ctx: ToolContext) -> str:
    """Execute a tool by name and return the result as a string for the model."""
    handler = _DISPATCH.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        args = json.loads(arguments_json) if arguments_json else {}
        result = await handler(args, ctx)
        log.info(f"Tool {name} executed successfully")
        return result
    except Exception as e:
        log.exception(f"Tool {name} failed")
        return json.dumps({"error": str(e)})
