"""Model adapters for the assistant.

Both providers run the same agentic loop — ask, run any requested tools, ask
again — over the shared tool specs. Each returns the final answer text, or
raises, in which case the caller falls back to the offline template.
"""

import json

from app.config import settings
from app.services.assistant import (
    HISTORY_LIMIT,
    detect_language,
    REQUEST_TIMEOUT_SECONDS,
    SYSTEM_PROMPT,
    TOOL_SPECS,
    ToolContext,
    run_tool,
)

#: Hard stop on the tool loop; two rounds is plenty for "where is X?".
MAX_TOOL_ROUNDS = 3


def _system_prompt(question: str) -> str:
    """The prompt plus the detected language, restated last for recency."""
    language = detect_language(question)
    return (
        SYSTEM_PROMPT.format(store_name=settings.store_name)
        + "\n\n"
        + f"The customer wrote this question in {language}. "
        + f"You MUST write your answer in {language}, and no other language."
    )


# --- OpenAI ---------------------------------------------------------------


def ask_openai(
    context: ToolContext, question: str, history: list[dict], grounding: str
) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=1
    )
    tools = [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
        for spec in TOOL_SPECS
    ]

    messages: list[dict] = [{"role": "system", "content": _system_prompt(question)}]
    messages += history[-HISTORY_LIMIT:]
    messages.append({"role": "system", "content": grounding})
    messages.append({"role": "user", "content": question})

    for _round in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=tools,
            max_tokens=220,
        )
        message = response.choices[0].message
        calls = message.tool_calls or []

        if not calls:
            return (message.content or "").strip()

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in calls
                ],
            }
        )

        for call in calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
            result = run_tool(context, call.function.name, arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise RuntimeError("OpenAI kept calling tools without answering")


# --- Anthropic ------------------------------------------------------------


def ask_anthropic(
    context: ToolContext, question: str, history: list[dict], grounding: str
) -> str:
    import anthropic

    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=1,
    )
    tools = [
        {
            "name": spec["name"],
            "description": spec["description"],
            "input_schema": spec["parameters"],
        }
        for spec in TOOL_SPECS
    ]

    messages: list[dict] = [
        *history[-HISTORY_LIMIT:],
        {"role": "user", "content": grounding + "\n\nCustomer: " + question},
    ]

    for _round in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=settings.ai_model,
            max_tokens=220,
            system=_system_prompt(question),
            tools=tools,
            messages=messages,
        )

        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            return text.strip()

        messages.append({"role": "assistant", "content": response.content})
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(
                            run_tool(context, block.name, dict(block.input)),
                            ensure_ascii=False,
                        ),
                    }
                    for block in tool_uses
                ],
            }
        )

    raise RuntimeError("Anthropic kept calling tools without answering")


ASK = {"openai": ask_openai, "anthropic": ask_anthropic}
