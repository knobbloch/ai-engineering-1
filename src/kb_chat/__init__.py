import logging
import typing as t
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI

from kb_chat.api.routers.chat import chat_router
from kb_chat.configuration import Configuration
from kb_chat.core.chat.impl.service import KnowledgeBaseChatService
from kb_chat.core.knowledge_base.impl.in_memory import InMemoryKnowledgeBase
from kb_chat.core.llm.impl.random import RandomLLMClient

logger = logging.getLogger(__name__)


def setup_logging(log_level: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger("kb_chat")


@asynccontextmanager
async def lifespan(app: FastAPI) -> t.AsyncGenerator[None, None]:
    configuration: Configuration = app.state.configuration
    app_logger = app.state.logger

    app_logger.info(f"Starting {configuration.app_name}")
    app_logger.info(f"Using LLM model: {configuration.llm.model}")
    app_logger.info(f"Cache TTL: {configuration.cache.ttl_seconds} seconds")

    knowledge_base = InMemoryKnowledgeBase()
    llm_client = RandomLLMClient(model=configuration.llm.model)
    redis_client = redis.from_url(configuration.cache.redis_url)
    chat_service = KnowledgeBaseChatService(
        knowledge_base=knowledge_base,
        llm_client=llm_client,
        default_temperature=configuration.llm.temperature,
        redis_client=redis_client,
        ttl_seconds=configuration.cache.ttl_seconds,
    )

    app.state.knowledge_base = knowledge_base
    app.state.llm_client = llm_client
    app.state.chat_service = chat_service

    yield

    await redis_client.aclose()
    app_logger.info(f"Shutting down {configuration.app_name}")


def initialize_service(configuration: Configuration) -> FastAPI:
    app_logger = setup_logging(configuration.log_level)

    service = FastAPI(
        title=configuration.app_name,
        description="Internal knowledge base chat service for bank employees",
        version="0.1.0",
        lifespan=lifespan,
    )

    service.state.configuration = configuration
    service.state.logger = app_logger

    service.include_router(chat_router, prefix="/api/v1")

    return service


def create_app() -> FastAPI:
    configuration = Configuration()
    return initialize_service(configuration)
