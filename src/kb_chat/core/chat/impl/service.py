import hashlib
import logging
import textwrap
from typing import Any

from kb_chat.core.chat.abc import ChatService, ChatServiceError
from kb_chat.core.knowledge_base.abc import KnowledgeBase
from kb_chat.core.llm.abc import LLMClient
from kb_chat.domain.models import ChatResult, LLMRequest, TopicContent

logger = logging.getLogger(__name__)


class KnowledgeBaseChatService(ChatService):
    """
    Chat service that uses knowledge base content to answer questions.
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        llm_client: LLMClient,
        default_temperature: float = 0.7,
        redis_client: Any = None,
        ttl_seconds: int = 300,
    ) -> None:
        self.__knowledge_base = knowledge_base
        self.__llm_client = llm_client
        self.__default_temperature = default_temperature
        self.__redis = redis_client
        self.__ttl = ttl_seconds

    async def chat(
        self,
        question: str,
        topic: str,
        temperature: float | None = None,
    ) -> ChatResult:
        topic_content = await self.__knowledge_base.get_topic_content(topic)
        if topic_content is None:
            raise ChatServiceError(f"Topic '{topic}' not found")

        system_prompt = self.__build_system_prompt(topic_content)
        effective_temperature = temperature if temperature is not None else self.__default_temperature

        redis_key = hashlib.md5((question + system_prompt + self.__llm_client.model).encode()).hexdigest()
        if self.__redis is not None:
            answer = await self.__redis.get(redis_key)
            if answer is not None:
                return ChatResult(
                    answer=answer.decode(),
                    topic=topic,
                    model=self.__llm_client.model,
                    cached=True,
                )

        request = LLMRequest(
            prompt=question,
            system_prompt=system_prompt,
            model=self.__llm_client.model,
            temperature=effective_temperature,
        )

        response = await self.__llm_client.generate(request)

        if self.__redis is not None:
            await self.__redis.setex(redis_key, self.__ttl, response.content)
            await self.__redis.sadd(f"topic:{topic}", redis_key)
            await self.__redis.expire(f"topic:{topic}", self.__ttl)

        return ChatResult(
            answer=response.content,
            topic=topic,
            model=response.model,
            cached=False,
        )

    async def invalidate_topic(self, topic: str) -> None:
        if self.__redis is None:
            return
        keys = await self.__redis.smembers(f"topic:{topic}")
        if keys:
            await self.__redis.delete(*keys)
        await self.__redis.delete(f"topic:{topic}")

    @property
    def llm_client(self) -> LLMClient:
        return self.__llm_client

    @property
    def knowledge_base(self) -> KnowledgeBase:
        return self.__knowledge_base

    def __build_system_prompt(self, topic_content: TopicContent) -> str:
        return textwrap.dedent(f"""\
            You are a helpful assistant for bank employees.
            Answer questions based on the following knowledge base content.
            Be concise and accurate. If you don't know the answer, say so.

            Knowledge Base Content:
            {topic_content.content}

            Always be professional and helpful.""")
