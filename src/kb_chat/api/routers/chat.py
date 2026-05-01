import typing as t

import pydantic
from fastapi import APIRouter, HTTPException, Request
from pydantic import Field

from kb_chat.core.chat.abc import ChatService, ChatServiceError
from kb_chat.core.chat.impl.service import KnowledgeBaseChatService

chat_router = APIRouter(tags=["Chat"])


class ChatRequest(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=1000)
    topic: str = Field(..., min_length=1, max_length=100)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class ChatResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    answer: str
    topic: str
    model: str
    cached: bool


class TopicsResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    topics: t.Sequence[str]


@chat_router.get("/topics", response_model=TopicsResponse)
async def list_topics(request: Request) -> TopicsResponse:
    knowledge_base = request.app.state.knowledge_base
    topics = await knowledge_base.list_topics()
    return TopicsResponse(topics=topics)


@chat_router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    chat_service: ChatService = request.app.state.chat_service

    try:
        result = await chat_service.chat(
            question=body.question,
            topic=body.topic,
            temperature=body.temperature,
        )
    except ChatServiceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return ChatResponse(
        answer=result.answer,
        topic=result.topic,
        model=result.model,
        cached=result.cached,
    )


@chat_router.post("/cache/invalidate/{topic}")
async def invalidate_cache(topic: str, request: Request) -> dict:
    chat_service: KnowledgeBaseChatService = request.app.state.chat_service
    await chat_service.invalidate_topic(topic)
    return {"invalidated": topic}
