"""Gemini through its native API, as a litellm provider.

Gemini 3 ties each function call to a thought signature that has to travel back
with the conversation. The gateway serving it breaks that on both of litellm's
routes: its OpenAI-compatible endpoint drops the signatures, and its native
endpoint ignores `function_response` parts spelled the way litellm spells them.
The google-genai SDK writes requests as Gemini defines them.

Registered as the litellm provider `genai`, it serves tau2's function-calling
agent, CaveAgent and the `execute_python` arm alike, so every paradigm reaches
Gemini through one path. Responses are always fetched whole; a streaming caller
receives them as chunks cut from that one response.

Gemini has no incremental stream here, so streaming is a shape, not a promise of
latency: :func:`to_stream_chunks` cuts one whole response into the sequence a
reader of an OpenAI-style stream expects — the text, then each tool call under
its own index. Cutting per call matters, because a reader that stops at the
second call to keep a turn to one action can only see a second call if a second
chunk carries it.
"""

import base64
import json
import os
import uuid
from collections.abc import AsyncIterator

import litellm
from google import genai
from google.genai import types
from litellm.llms.custom_llm import CustomLLM, CustomLLMError
from litellm.types.llms.openai import (
    ChatCompletionToolCallChunk,
    ChatCompletionToolCallFunctionChunk,
)
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Choices,
    Function,
    GenericStreamingChunk,
    Message,
    ModelResponse,
    Usage,
)

PROVIDER = "genai"
API_KEY_ENV = "GENAI_API_KEY"   # where run.py puts the key for this provider

# A tool call's signature rides in its id, the one field every caller hands
# back untouched when it replays the conversation.
_SIGNATURE = "__thought__"


def to_request(messages: list[dict]) -> tuple[str | None, list[types.Content]]:
    """OpenAI-style chat messages as a Gemini system instruction and contents."""
    system, contents = [], []
    function_names = {}
    for message in messages:
        role = message["role"]
        if role == "system":
            system.append(message["content"])
        elif role == "tool":
            part = types.Part(function_response=types.FunctionResponse(
                name=function_names[message["tool_call_id"]],
                response=_as_response(message["content"]),
            ))
            # Responses to one turn's calls belong together in a single content.
            if contents and contents[-1].role == "user" and contents[-1].parts[-1].function_response:
                contents[-1].parts.append(part)
            else:
                contents.append(types.Content(role="user", parts=[part]))
        else:
            parts = [types.Part(text=message["content"])] if message.get("content") else []
            for call in message.get("tool_calls") or []:
                function_names[call["id"]] = call["function"]["name"]
                _, _, signature = call["id"].partition(_SIGNATURE)
                parts.append(types.Part(
                    function_call=types.FunctionCall(
                        name=call["function"]["name"], args=json.loads(call["function"]["arguments"])),
                    thought_signature=base64.b64decode(signature) if signature else None,
                ))
            contents.append(types.Content(role="model" if role == "assistant" else "user", parts=parts))
    return ("\n\n".join(system) or None), contents


def _as_response(content: str) -> dict:
    """A tool result as the object a function response has to be."""
    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return {"result": content}
    return value if isinstance(value, dict) else {"result": value}


def to_config(optional_params: dict) -> types.GenerateContentConfig:
    """The sampling, reasoning and tool settings of a litellm call."""
    tools = [
        types.Tool(function_declarations=[types.FunctionDeclaration(
            name=tool["function"]["name"],
            description=tool["function"].get("description"),
            parameters_json_schema=tool["function"].get("parameters"),
        )])
        for tool in optional_params.get("tools") or []
    ]
    effort = optional_params.get("reasoning_effort")
    return types.GenerateContentConfig(
        temperature=optional_params.get("temperature"),
        thinking_config=types.ThinkingConfig(thinking_level=effort) if effort else None,
        tools=tools or None,
        # The caller runs the tools; the SDK must not try to.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def to_model_response(response: types.GenerateContentResponse, model: str) -> ModelResponse:
    """A Gemini response in litellm's shape.

    A response with neither text nor a call — Gemini's MALFORMED_FUNCTION_CALL,
    or an empty candidate — is raised as a server error rather than returned, so
    litellm's retries take another sample, as they would for any other failure.
    """
    candidate = response.candidates[0] if response.candidates else None
    reason = candidate.finish_reason.name if candidate and candidate.finish_reason else "NO_CANDIDATE"
    parts = candidate.content.parts if candidate and candidate.content and candidate.content.parts else []

    text = "".join(part.text for part in parts if part.text and not part.thought)
    calls = [
        ChatCompletionMessageToolCall(
            id=f"call_{uuid.uuid4().hex}" + (
                _SIGNATURE + base64.b64encode(part.thought_signature).decode()
                if part.thought_signature else ""),
            type="function",
            function=Function(name=part.function_call.name,
                              arguments=json.dumps(part.function_call.args or {})),
        )
        for part in parts if part.function_call
    ]
    if not (text or calls):
        raise CustomLLMError(status_code=500, message=f"Gemini returned no usable output ({reason})")

    usage = response.usage_metadata
    thoughts = usage.thoughts_token_count or 0
    prompt = usage.prompt_token_count or 0
    completion = (usage.candidates_token_count or 0) + thoughts
    return ModelResponse(
        model=model,
        choices=[Choices(
            index=0,
            finish_reason="tool_calls" if calls else ("length" if reason == "MAX_TOKENS" else "stop"),
            message=Message(role="assistant", content=text or None, tool_calls=calls or None),
        )],
        usage=Usage(prompt_tokens=prompt, completion_tokens=completion,
                    total_tokens=prompt + completion, reasoning_tokens=thoughts),
    )


def to_stream_chunks(response: ModelResponse) -> list[GenericStreamingChunk]:
    """One whole response as the chunks an OpenAI-style stream would deliver.

    The text comes first, then one chunk per tool call, each under its own
    index. Only the last chunk is finished and carries the usage: a reader
    accumulates until then, and litellm's wrapper turns ``tool_use`` into the
    ``delta.tool_calls`` its consumers read.

    A response with no calls yields exactly the single text chunk this provider
    has always yielded, so a caller that never asks for a tool sees no change.

    Putting the usage on the last chunk means a reader that stops at the second
    call never receives it and falls back to its own estimate. That is what a
    real stream does — a gateway's usage block also arrives after the content it
    describes — so this matches the other model channels rather than making
    Gemini the one that always reports true counts. It costs more often here
    than there: Gemini returned several calls in one message 25% of the time in
    this domain, against 8% on the gateway, so a quarter of this arm's Gemini
    turns are estimated. Reward is unaffected; the token column is not.
    """
    choice = response.choices[0]
    usage = {"prompt_tokens": response.usage.prompt_tokens,
             "completion_tokens": response.usage.completion_tokens,
             "total_tokens": response.usage.total_tokens}
    calls = choice.message.tool_calls or []
    text = choice.message.content or ""

    pieces: list[tuple[str, ChatCompletionToolCallChunk | None]] = []
    if text or not calls:
        pieces.append((text, None))
    for index, call in enumerate(calls):
        pieces.append(("", ChatCompletionToolCallChunk(
            id=call.id,
            type="function",
            function=ChatCompletionToolCallFunctionChunk(
                name=call.function.name, arguments=call.function.arguments),
            index=index,
        )))

    last = len(pieces) - 1
    return [
        GenericStreamingChunk(
            text=piece_text,
            tool_use=tool_use,
            is_finished=position == last,
            finish_reason=choice.finish_reason if position == last else "",
            usage=usage if position == last else None,
            index=0,
        )
        for position, (piece_text, tool_use) in enumerate(pieces)
    ]


class GenaiProvider(CustomLLM):
    """litellm's entry points, each a whole generate_content call."""

    @staticmethod
    def _client(api_base: str | None, api_key: str | None, timeout) -> genai.Client:
        milliseconds = int(timeout * 1000) if isinstance(timeout, (int, float)) else None
        return genai.Client(
            api_key=api_key or os.environ[API_KEY_ENV],
            http_options=types.HttpOptions(base_url=api_base, timeout=milliseconds),
        )

    @staticmethod
    def _arguments(model: str, messages: list[dict], optional_params: dict) -> dict:
        system, contents = to_request(messages)
        config = to_config(optional_params)
        config.system_instruction = system
        return {"model": model, "contents": contents, "config": config}

    def completion(self, model, messages, api_base, api_key, optional_params, timeout=None, **_):
        client = self._client(api_base, api_key, timeout)
        response = client.models.generate_content(**self._arguments(model, messages, optional_params))
        return to_model_response(response, model)

    async def acompletion(self, model, messages, api_base, api_key, optional_params, timeout=None, **_):
        client = self._client(api_base, api_key, timeout)
        response = await client.aio.models.generate_content(**self._arguments(model, messages, optional_params))
        return to_model_response(response, model)

    async def astreaming(self, model, messages, api_base, api_key, optional_params, timeout=None,
                         **_) -> AsyncIterator[GenericStreamingChunk]:
        response = await self.acompletion(model, messages, api_base, api_key, optional_params, timeout)
        for chunk in to_stream_chunks(response):
            yield chunk


def register() -> None:
    """Make `genai/<model>` available to litellm in this process."""
    if not any(entry["provider"] == PROVIDER for entry in litellm.custom_provider_map):
        litellm.custom_provider_map.append({"provider": PROVIDER, "custom_handler": GenaiProvider()})
