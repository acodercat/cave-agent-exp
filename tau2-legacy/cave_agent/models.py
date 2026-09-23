from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, AsyncIterator
import asyncio

class Model(ABC):
    """
    Abstract base class for language model engines.
    Defines interface for interacting with different LLM providers.
    """

    @abstractmethod
    async def call(self, messages: List[Dict[str, str]]) -> str:
        """Generate response from message history asynchronously."""
        pass
    
    @abstractmethod
    async def stream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Stream response tokens from message history asynchronously."""
        pass

class OpenAIServerModel(Model):
    """
    OpenAI-compatible LLM engine implementation.
    Supports OpenAI API and compatible endpoints.
    """
    
    def __init__(
            self, 
            model_id: str,
            base_url: Optional[str] = None,
            api_key: Optional[str] = None,
            organization: Optional[str] = None,
            project: Optional[str] = None,
            **kwargs
        ):
        """Initialize OpenAI LLM engine.
        
        Args:
            model_id: Model identifier
            api_key: API authentication key
            base_url: Optional API endpoint URL
            organization: Optional organization ID
            project: Optional project ID
            **kwargs: Additional parameters to pass to the OpenAI API
        """
        try:
            import openai
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "Please install 'openai' extra to use OpenAIServerModel: `pip install 'cave_agent[openai]'`"
            )

        self.kwargs = kwargs
        self.model_id = model_id
        self.client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            organization=organization,
            project=project,
        )
    
    def _prepare_params(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Prepare parameters for OpenAI API call."""
        params = {
            "model": self.model_id,
            "messages": messages,
            # "tool_choice": "none",
            **self.kwargs,
        }
            
        return params

    async def call(self, messages: List[Dict[str, str]]) -> str:
        """Generate response using OpenAI API asynchronously."""
        max_retries = 5
        last_response = None

        for attempt in range(max_retries):
            response = await self.client.chat.completions.create(
                **self._prepare_params(messages),
                # reasoning_effort="none",
                stream=False
            )
            last_response = response
            if hasattr(response, "choices") and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content and content.strip():
                    print("model response content", content)
                    return content
                else:
                    print(f"Attempt {attempt + 1}/{max_retries}: Empty content, retrying...")
                    continue

        # All retries exhausted
        print(f"No valid content after {max_retries} attempts", last_response)
        raise Exception(f"No valid content after {max_retries} attempts")
    
    async def stream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Stream response tokens using OpenAI API."""
        response = await self.client.chat.completions.create(
            **self._prepare_params(messages),
            stream=True
        )
        
        async for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

class GPT5Model(Model):
    """
    OpenAI-compatible LLM engine implementation.
    Supports OpenAI API and compatible endpoints.
    """
    
    def __init__(
            self, 
            model_id: str,
            base_url: Optional[str] = None,
            api_key: Optional[str] = None,
            organization: Optional[str] = None,
            project: Optional[str] = None,
            **kwargs
        ):
        """Initialize OpenAI LLM engine.
        
        Args:
            model_id: Model identifier
            api_key: API authentication key
            base_url: Optional API endpoint URL
            organization: Optional organization ID
            project: Optional project ID
            **kwargs: Additional parameters to pass to the OpenAI API
        """
        try:
            import openai
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "Please install 'openai' extra to use OpenAIServerModel: `pip install 'cave_agent[openai]'`"
            )

        self.kwargs = kwargs
        self.model_id = model_id
        self.client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            organization=organization,
            project=project,
        )
    
    def _prepare_params(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Prepare parameters for OpenAI API call."""
        params = {
            "model": self.model_id,
            "messages": messages,
            **self.kwargs,
        }
            
        return params

    async def call(self, messages: List[Dict[str, str]]) -> str:
        """Generate response using OpenAI API asynchronously."""
        # await asyncio.sleep(30)
        response = await self.client.chat.completions.create(
            **self._prepare_params(messages),
            reasoning_effort="none",
            stream=False
        )
        if hasattr(response, "choices") and len(response.choices) > 0:
            print("model response content:", response.choices[0].message.content)
            return response.choices[0].message.content
    
    async def stream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Stream response tokens using OpenAI API."""
        response = await self.client.chat.completions.create(
            **self._prepare_params(messages),
            stream=True
        )
        
        async for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

class LiteLLMModel(Model):
    """
    LiteLLM model implementation that provides a unified interface to hundreds of LLM providers.
    
    LiteLLM is a library that standardizes the API for different LLM providers, allowing you to
    easily switch between OpenAI, Anthropic, Google, Azure, and many other providers with a
    consistent interface. This model acts as a gateway to access any LLM supported by LiteLLM.
    
    See https://www.litellm.ai/ for more information about supported providers and models.
    """
    
    def __init__(
            self, 
            model_id: str,
            base_url: Optional[str] = None,
            api_key: Optional[str] = None,
            **kwargs
        ):
        """Initialize OpenAI LLM engine.
        
        Args:
            model_id: Model identifier
            api_key: API authentication key
            base_url: Optional API endpoint URL
            **kwargs: Additional parameters to pass to the API
        """
        try:
            import litellm
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "Please install 'litellm' extra to use LiteLLMModel: `pip install 'cave_agent[litellm]'`"
            )
        self.kwargs = kwargs
        self.model_id = model_id
        self.base_url = base_url
        self.api_key = api_key

    def _prepare_params(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Prepare parameters for API call"""
        params = {
            "model": self.model_id,
            "api_base": self.base_url,
            "api_key": self.api_key,
            "messages": messages,
            **self.kwargs,
        }
        
        return params

    async def call(self, messages: List[Dict[str, str]]) -> str:
        """Generate response."""
        import litellm
        response = await litellm.acompletion(**self._prepare_params(messages), stream=False)
        # print(response)

        if hasattr(response, "choices") and len(response.choices) > 0:
            return response.choices[0].message.content
    
    async def stream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Stream response tokens"""
        import litellm
        response = await litellm.acompletion(**self._prepare_params(messages), stream=True)
        
        async for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

class GeminiModel(Model):
    """
    LiteLLM model implementation that provides a unified interface to hundreds of LLM providers.
    
    LiteLLM is a library that standardizes the API for different LLM providers, allowing you to
    easily switch between OpenAI, Anthropic, Google, Azure, and many other providers with a
    consistent interface. This model acts as a gateway to access any LLM supported by LiteLLM.
    
    See https://www.litellm.ai/ for more information about supported providers and models.
    """
    
    def __init__(
            self, 
            model_id: str,
            base_url: Optional[str] = None,
            api_key: Optional[str] = None,
            **kwargs
        ):
        """Initialize OpenAI LLM engine.
        
        Args:
            model_id: Model identifier
            api_key: API authentication key
            base_url: Optional API endpoint URL
            **kwargs: Additional parameters to pass to the API
        """
        try:
            import litellm
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "Please install 'litellm' extra to use LiteLLMModel: `pip install 'cave_agent[litellm]'`"
            )
        self.kwargs = kwargs
        self.model_id = model_id
        self.base_url = base_url
        self.api_key = api_key

    async def _prepare_params(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Prepare parameters for API call"""
        from google.genai import types
        
        # Extract system instruction if present
        system_instruction = None
        genai_messages = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_instruction = content
            elif role == "assistant":
                genai_messages.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
            elif role == "user":
                genai_messages.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
        
        # Build config
        config_dict = {
            "max_output_tokens": 20000,
            "temperature": self.kwargs.get("temperature", 1.0),
        }
        
        if system_instruction:
            config_dict["system_instruction"] = system_instruction
        
        # DISABLE THINKING - Add this line
        config_dict["thinking_config"] = types.ThinkingConfig(
            # include_thoughts=False,
            thinking_level="low"
        )
        
        params = {
            "contents": genai_messages,
            "config": types.GenerateContentConfig(**config_dict)
        }
        
        return params

    async def call(self, messages: List[Dict[str, str]]) -> str:
        """Generate response with retry logic for malformed responses."""
        from google import genai

        # Initialize client
        client = genai.Client(api_key=self.api_key)

        # Prepare parameters
        params = await self._prepare_params(messages)

        # Retry logic for handling MALFORMED_FUNCTION_CALL
        max_retries = 5
        last_response = None

        for attempt in range(max_retries):
            # Make async API call
            response = await client.aio.models.generate_content(
                model=self.model_id,
                **params
            )

            last_response = response

            if attempt == 0:
                print(response)

            # Check finish reason
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason

                # If malformed function call, retry
                if finish_reason and "MALFORMED_FUNCTION_CALL" in str(finish_reason):
                    print(f"Attempt {attempt + 1}/{max_retries}: MALFORMED_FUNCTION_CALL detected, retrying...")
                    continue

                # Extract content from response
                if candidate.content and candidate.content.parts:
                    content = candidate.content.parts[0].text
                    if content and content.strip():  # Ensure not empty/whitespace
                        return content
                    else:
                        print(f"Attempt {attempt + 1}/{max_retries}: Empty content, retrying...")
                        continue

        # All retries exhausted
        print(f"No valid content after {max_retries} attempts", last_response)
        raise Exception("No valid content after {max_retries} attempts")
        return "I apologize, but I encountered an error while processing your request. Please try rephrasing your question."
    
    async def stream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Stream response tokens"""
        import litellm
        response = await litellm.acompletion(**self._prepare_params(messages), stream=True)
        
        async for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content


class AnthropicModel(Model):
    """
    LiteLLM model implementation that provides a unified interface to hundreds of LLM providers.
    
    LiteLLM is a library that standardizes the API for different LLM providers, allowing you to
    easily switch between OpenAI, Anthropic, Google, Azure, and many other providers with a
    consistent interface. This model acts as a gateway to access any LLM supported by LiteLLM.
    
    See https://www.litellm.ai/ for more information about supported providers and models.
    """
    
    def __init__(
            self, 
            model_id: str,
            base_url: Optional[str] = None,
            api_key: Optional[str] = None,
            **kwargs
        ):
        """Initialize OpenAI LLM engine.
        
        Args:
            model_id: Model identifier
            api_key: API authentication key
            base_url: Optional API endpoint URL
            **kwargs: Additional parameters to pass to the API
        """
        try:
            import litellm
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "Please install 'litellm' extra to use LiteLLMModel: `pip install 'cave_agent[litellm]'`"
            )
        self.kwargs = kwargs
        self.model_id = model_id
        self.base_url = base_url
        self.api_key = api_key

    def _prepare_params(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Prepare parameters for API call with Anthropic message format"""
        
        transformed_messages = []
        system_contents = []
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "system":
                # Collect all system message contents
                if isinstance(content, str):
                    system_contents.append({
                        "type": "text",
                        "text": content
                    })
                else:
                    # If already a list of content blocks
                    system_contents.extend(content if isinstance(content, list) else [content])
            else:
                # For non-system messages, process normally
                if isinstance(content, str):
                    transformed_msg = {
                        "role": role,
                        "content": content  # Keep user messages as simple strings
                    }
                else:
                    transformed_msg = {
                        "role": role,
                        "content": content
                    }
                transformed_messages.append(transformed_msg)
        
        # Add cache control to the last system content block
        if system_contents:
            system_contents[-1]["cache_control"] = {"type": "ephemeral", "ttl": '1h'}
            
            # Insert combined system message at the beginning
            transformed_messages.insert(0, {
                "role": "system",
                "content": system_contents
            })
        
        
        params = {
            "model": self.model_id,
            "api_base": self.base_url,
            "api_key": self.api_key,
            "messages": transformed_messages,
            **self.kwargs,
        }
        
        return params

    async def call(self, messages: List[Dict[str, str]]) -> str:
        """Generate response."""
        # import litellm
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        system_messages = []
        conversation_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = {
                    "type": "text",
                    "text": msg["content"],
                    # Automatically enable ephemeral caching for all system prompts
                    "cache_control": {"type": "ephemeral", "ttl": "1h"}
                }
                system_messages.append(system_msg)
            else:
                conversation_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        request_params = {
            "model": self.model_id,
            "messages": conversation_messages,
            "temperature": self.kwargs.get("temperature", 0.2),
            "max_tokens": self.kwargs.get("max_tokens", 12000),  # Anthropic requires max_tokens
        }

        # Add system messages if present
        if system_messages:
            request_params["system"] = system_messages
        
        response = await client.messages.create(
            **request_params
        )
        
        return response.content[0].text
        

        # print(self._prepare_params(messages))
        # response = await litellm.acompletion(**self._prepare_params(messages), stream=False)

        # if hasattr(response, "choices") and len(response.choices) > 0:
        #     return response.choices[0].message.content
    
    async def stream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Stream response tokens"""
        import litellm
        response = await litellm.acompletion(**self._prepare_params(messages), stream=True)
        
        async for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content