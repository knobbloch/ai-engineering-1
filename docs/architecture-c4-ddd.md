# KB Chat: C4 + DDD Diagrams

Документ показывает архитектуру без смешивания уровней:

- C4 L1: кто вокруг системы.
- C4 L2: какие контейнеры/процессы участвуют.
- C4 L3: какие компоненты есть внутри Python-приложения.
- DDD/code view: где в коде API, use case, domain, ports и adapters.
- Target cache flow: куда встраивать Redis-кэш из `TASK.md`.

Обозначения:

- Сплошные связи - текущий код.
- Пунктирные связи - целевая доработка для Redis cache.

## C4 L1: System Context

Один запрос идет от сотрудника через внешний semantic search в этот сервис. Redis нужен только для ускорения повторных LLM-ответов.

```mermaid
flowchart LR
    Employee["Bank employee"]
    Search["External Semantic Search\nchooses topic"]
    App["KB Chat\nthis repository"]
    LLM["LLM provider"]
    Redis[("Redis\nplanned response cache")]

    Employee -->|"question"| Search
    Search -->|"question + topic"| App
    App -->|"cache miss: prompt + system_prompt + model"| LLM
    App -.->|"cache get/set/invalidate"| Redis
    App -->|"answer + cached flag"| Employee

    classDef current fill:#eef6ff,stroke:#2563eb,color:#111827
    classDef external fill:#f8fafc,stroke:#64748b,color:#111827
    classDef planned fill:#fff7ed,stroke:#ea580c,stroke-dasharray: 5 5,color:#111827
    class Employee,Search,LLM external
    class App current
    class Redis planned
```

## C4 L2: Containers

В этом репозитории фактически один runtime-контейнер: FastAPI-приложение. Knowledge base и Random LLM сейчас являются Python-адаптерами внутри процесса, а Redis будет внешним контейнером.

```mermaid
flowchart TB
    Client["Semantic Search / Client"]

    subgraph Repo["KB Chat repository"]
        Api["FastAPI app\nkb_chat:create_app"]
        Domain["Domain models\nsrc/kb_chat/domain/models.py"]
        InMemory["In-memory KB adapter\ncore/knowledge_base/impl/in_memory.py"]
        RandomLLM["Random LLM adapter\ncore/llm/impl/random.py"]
    end

    Redis[("Redis\nplanned external cache")]
    RealLLM["Real LLM provider\nproduction replacement"]

    Client -->|"HTTP /api/v1/chat"| Api
    Api --> Domain
    Api --> InMemory
    Api --> RandomLLM
    RandomLLM -.->|"same port in production"| RealLLM
    Api -.->|"target cache adapter"| Redis

    classDef app fill:#eef6ff,stroke:#2563eb,color:#111827
    classDef code fill:#ecfdf5,stroke:#16a34a,color:#111827
    classDef planned fill:#fff7ed,stroke:#ea580c,stroke-dasharray: 5 5,color:#111827
    classDef external fill:#f8fafc,stroke:#64748b,color:#111827
    class Api app
    class Domain,InMemory,RandomLLM code
    class Redis planned
    class Client,RealLLM external
```

## C4 L3: Components Inside FastAPI App

Это главный уровень для понимания текущего кода. `chat.py` не должен знать про Redis напрямую: он вызывает use case. Use case зависит от портов, а реализации портов подключаются в composition root.

```mermaid
flowchart LR
    Router["API router\napi/routers/chat.py"]
    Factory["Composition root\nkb_chat/__init__.py"]

    subgraph Core["core"]
        ChatService["KnowledgeBaseChatService\ncore/chat/impl/service.py"]
        KBPort["KnowledgeBase port\ncore/knowledge_base/abc.py"]
        LLMPort["LLMClient port\ncore/llm/abc.py"]
        CachePort["ResponseCache port\nplanned: core/cache/abc.py"]
    end

    subgraph Adapters["adapters"]
        KBAdapter["InMemoryKnowledgeBase"]
        LLMAdapter["RandomLLMClient"]
        CacheAdapter["RedisResponseCache\nplanned"]
    end

    Domain["Domain models\ndomain/models.py"]
    Redis[("Redis")]

    Factory --> Router
    Factory --> ChatService
    Factory --> KBAdapter
    Factory --> LLMAdapter
    Factory -.-> CacheAdapter

    Router -->|"chat()"| ChatService
    ChatService --> KBPort
    ChatService --> LLMPort
    ChatService -.-> CachePort
    ChatService --> Domain

    KBAdapter -.->|"implements"| KBPort
    LLMAdapter -.->|"implements"| LLMPort
    CacheAdapter -.->|"implements"| CachePort
    CacheAdapter -.-> Redis

    classDef api fill:#eef6ff,stroke:#2563eb,color:#111827
    classDef core fill:#f0fdf4,stroke:#16a34a,color:#111827
    classDef adapter fill:#fefce8,stroke:#ca8a04,color:#111827
    classDef domain fill:#f5f3ff,stroke:#7c3aed,color:#111827
    classDef planned fill:#fff7ed,stroke:#ea580c,stroke-dasharray: 5 5,color:#111827
    class Router,Factory api
    class ChatService,KBPort,LLMPort core
    class KBAdapter,LLMAdapter adapter
    class Domain domain
    class CachePort,CacheAdapter,Redis planned
```

## DDD Code View

Здесь не классы ради классов, а смысловые роли файлов.

```mermaid
flowchart TB
    subgraph Interface["Interface layer"]
        APIFile["api/routers/chat.py\nHTTP DTOs + endpoints"]
    end

    subgraph Application["Application layer"]
        UseCase["core/chat/impl/service.py\nKnowledgeBaseChatService"]
    end

    subgraph Ports["Ports"]
        ChatPort["core/chat/abc.py\nChatService"]
        KBPort["core/knowledge_base/abc.py\nKnowledgeBase"]
        LLMPort["core/llm/abc.py\nLLMClient"]
        CachePort["planned: core/cache/abc.py\nResponseCache"]
    end

    subgraph Domain["Domain layer"]
        Models["domain/models.py\nTopicContent\nLLMRequest\nLLMResponse\nChatResult"]
    end

    subgraph Infrastructure["Infrastructure layer"]
        KBImpl["core/knowledge_base/impl/in_memory.py"]
        LLMImpl["core/llm/impl/random.py"]
        CacheImpl["planned: core/cache/impl/redis.py"]
    end

    APIFile --> ChatPort
    ChatPort -.->|"implemented by"| UseCase
    UseCase --> KBPort
    UseCase --> LLMPort
    UseCase -.-> CachePort
    UseCase --> Models
    KBPort --> Models
    LLMPort --> Models

    KBImpl -.->|"implements"| KBPort
    LLMImpl -.->|"implements"| LLMPort
    CacheImpl -.->|"implements"| CachePort

    classDef interface fill:#eef6ff,stroke:#2563eb,color:#111827
    classDef app fill:#f0fdf4,stroke:#16a34a,color:#111827
    classDef port fill:#fefce8,stroke:#ca8a04,color:#111827
    classDef domain fill:#f5f3ff,stroke:#7c3aed,color:#111827
    classDef infra fill:#f8fafc,stroke:#64748b,color:#111827
    classDef planned fill:#fff7ed,stroke:#ea580c,stroke-dasharray: 5 5,color:#111827
    class APIFile interface
    class UseCase app
    class ChatPort,KBPort,LLMPort port
    class Models domain
    class KBImpl,LLMImpl infra
    class CachePort,CacheImpl planned
```

## Current Request Flow

Текущий код дважды ходит в `KnowledgeBase`: сначала router проверяет topic, потом service снова загружает topic для system prompt.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Router as chat.py router
    participant Service as KnowledgeBaseChatService
    participant KB as KnowledgeBase
    participant LLM as LLMClient

    Client->>Router: POST /api/v1/chat
    Router->>KB: get_topic_content(topic)
    KB-->>Router: TopicContent
    Router->>Service: chat(question, topic, temperature)
    Service->>KB: get_topic_content(topic)
    KB-->>Service: TopicContent
    Service->>Service: build system_prompt
    Service->>LLM: generate(LLMRequest)
    LLM-->>Service: LLMResponse
    Service-->>Router: ChatResult(cached=false)
    Router-->>Client: ChatResponse
```

## Target Request Flow With Redis Cache

Кэш должен находиться вокруг вызова LLM внутри `KnowledgeBaseChatService`: сначала строим тот же `LLMRequest`, потом проверяем Redis по ключу из `prompt + system_prompt + model`.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Router as chat.py router
    participant Service as KnowledgeBaseChatService
    participant KB as KnowledgeBase
    participant Cache as ResponseCache
    participant Redis
    participant LLM as LLMClient

    Client->>Router: POST /api/v1/chat
    Router->>Service: chat(question, topic, temperature)
    Service->>KB: get_topic_content(topic)
    KB-->>Service: TopicContent
    Service->>Service: build LLMRequest
    Service->>Cache: get(request)
    Cache->>Redis: GET llm_response:{hash}

    alt cache hit
        Redis-->>Cache: serialized LLMResponse
        Cache-->>Service: LLMResponse
        Service-->>Router: ChatResult(cached=true)
    else cache miss
        Redis-->>Cache: empty
        Cache-->>Service: None
        Service->>LLM: generate(request)
        LLM-->>Service: LLMResponse
        Service->>Cache: set(topic, request, response, ttl=300)
        Cache->>Redis: SETEX llm_response:{hash}
        Cache->>Redis: SADD topic_cache_keys:{topic}
        Service-->>Router: ChatResult(cached=false)
    end

    Router-->>Client: ChatResponse
```

## Target Cache Invalidation

Для удаления по topic Redis-адаптеру нужен индекс `topic -> response keys`.

```mermaid
flowchart LR
    Endpoint["POST /api/v1/cache/invalidate/{topic}"]
    Cache["ResponseCache.invalidate_topic(topic)"]
    Set[("topic_cache_keys:{topic}")]
    Values[("llm_response:{hash}\nllm_response:{hash}\n...")]
    Result["200 OK\ninvalidated count"]

    Endpoint --> Cache
    Cache -->|"SMEMBERS"| Set
    Set --> Values
    Cache -->|"DEL response keys"| Values
    Cache -->|"DEL topic set"| Set
    Cache --> Result

    classDef api fill:#eef6ff,stroke:#2563eb,color:#111827
    classDef cache fill:#fff7ed,stroke:#ea580c,color:#111827
    classDef redis fill:#f8fafc,stroke:#64748b,color:#111827
    class Endpoint,Result api
    class Cache cache
    class Set,Values redis
```

## What To Add For The Redis Task

Минимальный чистый DDD вариант:

1. `core/cache/abc.py` - порт `ResponseCache`.
2. `core/cache/impl/redis.py` - Redis-адаптер.
3. `KnowledgeBaseChatService(..., response_cache: ResponseCache | None = None)` - optional dependency для тестов и простого запуска.
4. `POST /api/v1/cache/invalidate/{topic}` - endpoint вызывает cache port, не Redis напрямую.
5. Cache key строится из `prompt`, `system_prompt`, `model`.
6. Кэшируются только успешные `LLMResponse`.
