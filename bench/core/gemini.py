"""Gemini through its native API, as a litellm provider.

Gemini 3 ties each function call to a thought signature that has to travel back
with the conversation. The gateway serving it breaks that on both of litellm's
routes: its OpenAI-compatible endpoint drops the signatures, and its native
endpoint ignores ``function_response`` parts spelled the way litellm spells them.
The google-genai SDK writes requests as Gemini defines them.

Registered as the litellm provider ``genai``, it serves every paradigm alike —
the fenced-code agents and the ``execute_python`` one — so Gemini reaches each
arm of a study through one path.

A streaming caller is served from Gemini's own stream. The gateway drops a
request that has returned nothing after about two minutes, and a reply that
writes out a few hundred table rows takes longer than that to finish: fetched
whole, every such reply ended in "Server disconnected" at 121 s, and the text
and json arms could not complete a 250-row case at all. Streamed, the first
chunk arrives in seconds and the connection stays up. :func:`to_stream` turns
that stream into the sequence a reader of an OpenAI-style stream expects — the
text as it arrives, then each tool call under its own index. Cutting per call
matters, because a reader that stops at the second call to keep a turn to one
action can only see a second call if a second chunk carries it.

Ported from the τ² revision's runner, where it was written and tested, with two
changes: a request's ``max_tokens`` is honoured, because this suite holds the
output limit fixed across models, and streaming is real rather than a whole
response cut up afterwards.
"""
import base64
import json
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
        max_output_tokens=optional_params.get("max_tokens"),
        thinking_config=types.ThinkingConfig(thinking_level=effort) if effort else None,
        tools=tools or None,
        # The caller runs the tools; the SDK must not try to.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def _tool_call(part: types.Part) -> ChatCompletionMessageToolCall:
    """A Gemini function call in litellm's shape, its thought signature in its id."""
    return ChatCompletionMessageToolCall(
        id=f"call_{uuid.uuid4().hex}" + (
            _SIGNATURE + base64.b64encode(part.thought_signature).decode()
            if part.thought_signature else ""),
        type="function",
        function=Function(name=part.function_call.name,
                          arguments=json.dumps(part.function_call.args or {})),
    )


def _token_counts(usage: types.GenerateContentResponseUsageMetadata | None) -> tuple[int, int, int]:
    """Prompt, completion and reasoning tokens; reasoning counts as completion."""
    if usage is None:
        return 0, 0, 0
    thoughts = usage.thoughts_token_count or 0
    return usage.prompt_token_count or 0, (usage.candidates_token_count or 0) + thoughts, thoughts


def _finish(reason: str, called: bool) -> str:
    return "tool_calls" if called else ("length" if reason == "MAX_TOKENS" else "stop")


def _parts_of(response: types.GenerateContentResponse) -> tuple[str, list[types.Part]]:
    """A response's finish reason and parts; an empty candidate has neither."""
    candidate = response.candidates[0] if response.candidates else None
    reason = candidate.finish_reason.name if candidate and candidate.finish_reason else ""
    parts = candidate.content.parts if candidate and candidate.content and candidate.content.parts else []
    return reason, parts


def to_model_response(response: types.GenerateContentResponse, model: str) -> ModelResponse:
    """A Gemini response in litellm's shape.

    A response with neither text nor a call — Gemini's MALFORMED_FUNCTION_CALL,
    or an empty candidate — is raised as a server error rather than returned, so
    litellm's retries take another sample, as they would for any other failure.
    """
    reason, parts = _parts_of(response)
    text = "".join(part.text for part in parts if part.text and not part.thought)
    calls = [_tool_call(part) for part in parts if part.function_call]
    if not (text or calls):
        raise CustomLLMError(
            status_code=500, message=f"Gemini returned no usable output ({reason or 'NO_CANDIDATE'})")

    prompt, completion, thoughts = _token_counts(response.usage_metadata)
    return ModelResponse(
        model=model,
        choices=[Choices(
            index=0,
            finish_reason=_finish(reason, bool(calls)),
            message=Message(role="assistant", content=text or None, tool_calls=calls or None),
        )],
        usage=Usage(prompt_tokens=prompt, completion_tokens=completion,
                    total_tokens=prompt + completion, reasoning_tokens=thoughts),
    )


async def to_stream(
    responses: AsyncIterator[types.GenerateContentResponse],
) -> AsyncIterator[GenericStreamingChunk]:
    """Gemini's stream as the chunks an OpenAI-style stream would deliver.

    Text is passed on as it arrives. Tool calls are held to the end and then
    sent one chunk each, under their own index, so that a reader keeping a turn
    to one action can stop at the second. Only the last chunk is finished and
    carries the usage: litellm's wrapper turns ``tool_use`` into the
    ``delta.tool_calls`` its consumers read, and a reader accumulates until then.

    Putting the usage on the last chunk means a reader that stops at the second
    call never receives it and falls back to its own estimate. That is what any
    real stream does — a gateway's usage block also arrives after the content it
    describes — so Gemini is counted as the other models are.

    A stream with neither text nor a call — Gemini's MALFORMED_FUNCTION_CALL, or
    an empty candidate — is raised as a server error, as the whole-response path
    raises it.
    """
    calls: list[ChatCompletionMessageToolCall] = []
    reason, usage, spoke = "", None, False
    async for response in responses:
        finished, parts = _parts_of(response)
        reason = finished or reason
        usage = response.usage_metadata or usage
        for part in parts:
            if part.text and not part.thought:
                spoke = True
                yield _chunk(text=part.text)
            if part.function_call:
                calls.append(_tool_call(part))
    if not (spoke or calls):
        raise CustomLLMError(
            status_code=500, message=f"Gemini returned no usable output ({reason or 'NO_CANDIDATE'})")

    prompt, completion, _ = _token_counts(usage)
    closing = {
        "finish_reason": _finish(reason, bool(calls)),
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion,
                  "total_tokens": prompt + completion},
    }
    uses = [
        ChatCompletionToolCallChunk(
            id=call.id, type="function", index=index,
            function=ChatCompletionToolCallFunctionChunk(
                name=call.function.name, arguments=call.function.arguments),
        )
        for index, call in enumerate(calls)
    ] or [None]
    for use in uses[:-1]:
        yield _chunk(tool_use=use)
    yield _chunk(tool_use=uses[-1], **closing)


def _chunk(text: str = "", tool_use: ChatCompletionToolCallChunk | None = None,
           finish_reason: str = "", usage: dict | None = None) -> GenericStreamingChunk:
    return GenericStreamingChunk(
        text=text, tool_use=tool_use, is_finished=bool(finish_reason),
        finish_reason=finish_reason, usage=usage, index=0,
    )


class GenaiProvider(CustomLLM):
    """litellm's entry points, each a whole generate_content call."""

    @staticmethod
    def _client(api_base: str | None, api_key: str | None, timeout) -> genai.Client:
        milliseconds = int(timeout * 1000) if isinstance(timeout, (int, float)) else None
        return genai.Client(
            api_key=api_key,
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
        client = self._client(api_base, api_key, timeout)
        responses = await client.aio.models.generate_content_stream(
            **self._arguments(model, messages, optional_params))
        async for chunk in to_stream(responses):
            yield chunk


def register() -> None:
    """Make `genai/<model>` available to litellm in this process."""
    if not any(entry["provider"] == PROVIDER for entry in litellm.custom_provider_map):
        litellm.custom_provider_map.append({"provider": PROVIDER, "custom_handler": GenaiProvider()})
