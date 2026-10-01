# Технологический стек проекта

Дата фиксации: 1 октября 2026 года.

Этот документ фиксирует согласованный технологический стек проекта после решения отказаться от Homebox и разрабатывать приложение с нуля.

Основной продуктовый ориентир первой полезной версии:

> **Каталог + Ревизия**

Главные критерии выбора технологий:

1. минимальный объем разработки;
2. высокая скорость реализации;
3. простота поддержки;
4. понятность кода для разработчика и coding-агентов;
5. хороший мобильный web UX;
6. отсутствие преждевременной инфраструктурной сложности.

Стек намеренно выбирается «скучным»: новые технологии и абстракции добавляются только тогда, когда текущий набор действительно перестает решать конкретную задачу.

---

## 1. Общая форма приложения

Приложение разрабатывается как:

- один monorepo;
- один deployable application;
- отдельный SPA frontend;
- отдельный HTTP API;
- в production собранный frontend обслуживается тем же приложением, что и API.

Логическая граница frontend/backend остается явной.

Пример production-схемы:

```text
Browser
   |
   v
Application
   ├── /api/...        -> FastAPI
   └── static SPA      -> Vue build
   |
   v
PostgreSQL
```

В development frontend и backend могут запускаться отдельными dev-процессами.

Это дает:

- простой production deployment;
- нормальную API-first архитектуру;
- возможность позже подключить другой клиент, включая нативное мобильное приложение;
- отсутствие необходимости поддерживать два production-сервиса.

---

## 2. Backend

### Язык

**Python**

Причины:

- основной язык разработчика;
- высокая скорость разработки;
- хорошая поддержка агентной генерации и ревью;
- достаточно производительности для персонального self-hosted приложения.

---

## 3. Backend framework

### FastAPI

Используется как основной HTTP/API framework.

Ответственность FastAPI:

- REST endpoints;
- dependency injection на уровне request;
- OpenAPI;
- Pydantic validation;
- выдача production frontend;
- HTTP error mapping;
- будущая auth/session интеграция.

Не требуется вводить отдельный DI-container.

FastAPI dependencies достаточно для:

- DB Session;
- конфигурации;
- будущего current user;
- общих request-level dependencies.

---

## 4. API schemas и validation

### Pydantic 2

Используется для:

- request DTO;
- response DTO;
- validation входных данных;
- сериализации API;
- OpenAPI schema generation.

API-модели и SQLAlchemy ORM-модели считаются разными типами.

Не требуется пытаться объединить persistence model и внешний API DTO в одну модель.

---

## 5. Конфигурация

### pydantic-settings

Используется для:

- чтения environment variables;
- DB configuration;
- filesystem paths;
- runtime mode;
- будущих auth settings;
- прочих параметров приложения.

Конфигурация deployment не должна зашиваться в код.

---

## 6. Database

### PostgreSQL

PostgreSQL — единственная поддерживаемая СУБД.

SQLite compatibility не является требованием.

Причины:

- нет необходимости поддерживать два SQL dialect;
- надежные транзакции;
- ограничения БД;
- нормальная конкурентная запись;
- JSONB;
- полнотекстовый поиск;
- возможность использовать PostgreSQL-specific возможности без оглядки на SQLite.

Это осознанный выбор в пользу одной надежной БД вместо более сложной переносимости между СУБД.

---

## 7. PostgreSQL driver

### Psycopg 3

Используется как PostgreSQL driver для SQLAlchemy.

Основной путь работы с БД — синхронный.

Async API Psycopg не используется как архитектурная база приложения.

---

## 8. ORM

### SQLAlchemy 2.x ORM

Используется основной ORM.

Причины:

- зрелость;
- предсказуемость;
- хороший контроль транзакций;
- возможность при необходимости использовать SQLAlchemy Core;
- нет необходимости вводить дополнительный ORM-слой;
- хорошо подходит для PostgreSQL.

Не используется SQLModel.

### Подход

Основные persistence-операции выполняются через ORM.

Если конкретный сложный запрос проще и яснее выразить через SQLAlchemy Core или PostgreSQL-specific SQL, это допустимо.

Не требуется сохранять «чистоту ORM» ценой сложного кода.

---

## 9. Database migrations

### Alembic

Все изменения схемы БД выполняются через Alembic.

Правила:

- migration history является источником истины для изменения схемы;
- production не использует `Base.metadata.create_all()` для эволюции БД;
- изменение ORM schema должно сопровождаться миграцией;
- migration scripts должны проверяться на реальной PostgreSQL.

---

## 10. Sync / async модель backend

Основной backend и DB path — **синхронные**.

Используются:

- обычный SQLAlchemy `Session`;
- sync Psycopg;
- обычные request/use-case операции.

Async применяется только локально, если появится конкретная операция с внешним I/O, для которой это действительно оправдано.

Примеры будущего async I/O:

- внешний HTTP API;
- независимый сетевой сервис;
- другая I/O-bound интеграция.

Async не вводится заранее для обычного CRUD.

---

## 11. Архитектура backend-кода

Используется **вертикальная feature-based структура**.

Пример:

```text
backend/
  app/
    catalog/
    categories/
    revision/
    profile/
    files/
    api/
    db/
    core/
```

Предпочтительные feature-модули первой версии:

- `catalog`
- `categories`
- `revision`
- `profile`
- `files`

Дополнительные общие модули:

- `api`
- `db`
- `core`

### Принцип

Код группируется прежде всего по бизнес-функции, а не по глобальным техническим слоям.

Не строится структура вида:

```text
controllers/
services/
repositories/
models/
adapters/
ports/
```

на весь проект.

Внутри конкретной feature при необходимости могут появляться:

- router;
- schemas;
- models;
- queries/repository helpers;
- use cases.

Но отдельный слой создается только если у него есть реальная ответственность.

---

## 12. Не используется полноценный DDD / Clean Architecture

Сознательно не вводятся заранее:

- ports/adapters на каждую зависимость;
- domain repository interfaces без реальной необходимости;
- отдельный Unit of Work abstraction;
- event bus;
- command bus;
- mediator;
- DI-container;
- сложное разделение domain/application/infrastructure для простого CRUD.

Причина:

> архитектурная церемониальность не должна превышать сложность самого продукта.

---

## 13. Транзакционные границы

Транзакцией владеет **конкретный business use-case**.

Например:

```text
complete_revision()
```

должен атомарно:

- применить подтвержденные изменения вещей;
- изменить количества;
- обновить состояния;
- скрыть отсутствующие вещи;
- завершить ревизию;
- обновить факт последней полной проверки категории.

### Правила

- repository/query helpers не делают самостоятельных `commit()`;
- use-case получает SQLAlchemy Session;
- use-case явно определяет транзакционную границу;
- внутри repository допустим `flush()`;
- `commit()` принадлежит верхнему use-case.

Пример концептуально:

```python
with session.begin():
    ...
```

Отдельный UnitOfWork класс не нужен.

---

## 14. Frontend

### Vue 3

Основной frontend framework.

### TypeScript

Frontend пишется на TypeScript.

### Vite

Используется для:

- development server;
- frontend build;
- production bundle.

### Причина выбора

Frontend должен быть:

- простым;
- типизированным;
- хорошо поддерживаемым агентами;
- достаточно зрелым;
- удобным для mobile-first SPA.

---

## 15. Routing

### Vue Router

Используется стандартный Vue Router.

Не вводится собственная routing abstraction.

---

## 16. Server state

### TanStack Vue Query

Используется для данных, принадлежащих серверу:

- каталог;
- вещи;
- категории;
- профиль;
- ревизии;
- API mutations;
- query cache;
- invalidation;
- loading/error state;
- повторные запросы.

Это позволяет не создавать собственную инфраструктуру server-state management.

---

## 17. Client state

### Pinia не используется на старте

Глобальный store заранее не вводится.

Для локального UI state используются:

- `ref`;
- `reactive`;
- `computed`;
- composables;
- при необходимости `provide/inject`.

Pinia добавляется только если появится реальное сложное client-only состояние.

Server state не должен дублироваться в Pinia.

---

## 18. UI component library

### PrimeVue

Используется как основной набор готовых UI-компонентов.

Цель:

- не писать собственный UI kit;
- сократить frontend-код;
- быстро получить:
  - buttons;
  - selects;
  - dialogs;
  - forms;
  - tables;
  - menus;
  - basic layout components.

Не требуется дизайнерский perfectionism первой версии.

---

## 19. CSS strategy

### Tailwind не используется на старте

Причины:

- не нужен дополнительный utility layer;
- PrimeVue уже покрывает большую часть базового UI;
- меньше технологий для агента и разработчика.

Допустим обычный scoped CSS/Vue styles там, где компонента PrimeVue недостаточно.

---

## 20. Forms

Отдельный form framework на старте не используется.

Не вводятся заранее:

- vee-validate;
- FormKit;
- другие form engines.

Используются:

- Vue state;
- PrimeVue inputs;
- простая клиентская UX validation;
- серверная validation через Pydantic.

Если формы со временем станут достаточно сложными, специализированную библиотеку можно добавить позже.

---

## 21. API contract

### REST + JSON

GraphQL не используется.

API проектируется как обычный REST/JSON HTTP API.

### OpenAPI

OpenAPI, генерируемый FastAPI, является основным машинно-читаемым контрактом между backend и frontend.

---

## 22. TypeScript API client

Используются:

- `openapi-typescript`
- `openapi-fetch`

Pipeline:

```text
FastAPI
   |
   v
OpenAPI schema
   |
   v
openapi-typescript
   |
   v
generated TypeScript types
   |
   v
openapi-fetch
   |
   v
Vue frontend
```

Цель:

- не поддерживать API DTO вручную в Python и TypeScript;
- ловить изменения API на этапе TypeScript compilation;
- сократить количество самописного API boilerplate.

---

## 23. SSR

SSR не используется.

Не используется Nuxt.

Причины:

- приложение персональное;
- SEO не требуется;
- frontend работает как SPA;
- SSR увеличивает архитектурную сложность без продуктовой выгоды.

---

## 24. PWA и offline

Полноценная PWA infrastructure не входит в первый этап.

Целевая модель:

- изменения требуют online connection;
- позже можно добавить read-only cache последнего известного каталога;
- offline mutations не нужны.

Не проектируются заранее:

- sync queues;
- conflict resolution;
- offline-first data model.

---

## 25. Native mobile client

Первый клиент — web SPA.

Backend и доменная логика не зависят от Vue.

В будущем допускается отдельный мобильный клиент.

При этом Swift/iOS не является обязательной частью текущей разработки.

Главное требование сейчас:

> API должен быть самостоятельной границей, а не внутренним механизмом конкретного frontend.

---

## 26. Authentication

### Сейчас

Собственной пользовательской auth-модели нет.

Приложение доступно только через доверенное окружение:

- localhost;
- LAN;
- VPN;
- Tailscale/WireGuard;
- другое контролируемое соединение.

Приложение без auth не публикуется напрямую в интернет.

### В итоге

Планируется:

- один локальный пользователь;
- простой login/password;
- cookie-based session.

Не планируются сейчас:

- публичная регистрация;
- multi-user;
- tenant isolation;
- роли;
- OAuth;
- OIDC;
- social login.

Желательно сохранить тонкую conceptual boundary для будущего `current_user`, но не создавать полноценную user domain заранее.

---

## 27. File storage

Фото и другие вложения хранятся в обычной директории файловой системы.

В production директория монтируется как persistent Docker volume.

PostgreSQL хранит:

- metadata;
- относительный путь;
- связи файла с предметом.

Не используются:

- S3;
- MinIO;
- object storage abstraction;
- отдельный file-storage service.

Если S3 когда-нибудь действительно понадобится, рефакторинг выполняется тогда.

---

## 28. Background jobs

Фоновой очереди нет.

Не используются:

- Redis;
- Celery;
- RQ;
- Dramatiq;
- worker container.

Операции первой версии выполняются непосредственно внутри HTTP request.

Это включает:

- создание вещи;
- редактирование вещи;
- работу с категориями;
- ревизию;
- загрузку небольших изображений.

Фоновая инфраструктура добавляется только после появления конкретной долгой или ненадежной задачи, которая действительно не должна выполняться внутри HTTP request.

---

## 29. Search

Отдельного поискового движка нет.

Используется только PostgreSQL.

Возможные средства:

- обычные SQL filters;
- indexes;
- `ILIKE`;
- PostgreSQL full-text search;
- `pg_trgm`, если понадобится fuzzy search.

Не используются:

- Elasticsearch;
- OpenSearch;
- Meilisearch;
- Algolia;
- собственный search service.

### Будущий natural-language search

Если позже появится поиск фразой, например:

> покажи хорошую обувь для холодной погоды и города

естественный язык может преобразовываться в структурированные фильтры.

Сами данные продолжают искаться в PostgreSQL.

---

## 30. Модель расширяемых характеристик

Используется гибрид:

### Нормализованные данные

В отдельные колонки/relations выносятся характеристики, которые:

- важны для системной логики;
- часто фильтруются;
- требуют constraints;
- являются базовой частью предметной модели.

Примеры:

- category;
- condition;
- quantity;
- climate;
- purposes;
- ownership/current state;
- другие ключевые поля.

### JSONB

Редкие и category-specific свойства хранятся в PostgreSQL JSONB.

Примеры:

- специализированные характеристики лыж;
- редкие параметры палатки;
- дополнительные пользовательские свойства.

Если свойство из JSONB позже становится:

- часто используемым;
- важным для поиска;
- частью системных правил;

оно мигрирует в формальную колонку или relation.

### EAV не используется

Не строится универсальная система `attribute_definition / attribute_value`.

Причина — чрезмерная сложность запросов, валидации и UI для текущего продукта.

---

## 31. Deployment

### Docker Compose

Основной production deployment — Docker Compose.

Минимальный набор сервисов:

```text
app
postgres
```

### app

Содержит:

- Python runtime;
- FastAPI backend;
- production Vue build;
- static frontend files.

### postgres

Обычный PostgreSQL container.

### volumes

Persistent volumes нужны минимум для:

- PostgreSQL data;
- uploaded files.

---

## 32. Development environment

Разработка не обязана целиком происходить внутри Docker.

Предпочтительный workflow:

```text
PostgreSQL -> Docker Compose
FastAPI    -> native dev process
Vite       -> native dev process
```

Это ускоряет development cycle.

Production при этом остается контейнеризированным.

---

## 33. Network access

### Сейчас

Приложение доступно только через:

- LAN;
- VPN;
- Tailscale/WireGuard или аналогичный закрытый канал.

Публичного HTTPS endpoint нет.

### Позже

При необходимости публичного домена:

```text
Internet
   |
   v
Caddy
   |
   v
FastAPI application
```

Caddy отвечает за:

- HTTPS;
- сертификаты;
- reverse proxy.

Nginx заранее не вводится.

---

## 34. Python tooling

### uv

Используется для:

- Python dependencies;
- virtual environment;
- lockfile;
- запусков Python tooling.

Не требуется смешивать несколько dependency managers.

---

## 35. Frontend package manager

### npm

Используется стандартный npm.

Не вводятся pnpm/yarn без реальной необходимости.

---

## 36. Backend tests

### pytest

Основной test runner backend.

При необходимости используются:

- fixtures;
- FastAPI TestClient/http client;
- реальные SQLAlchemy sessions;
- реальный PostgreSQL.

### PostgreSQL tests

Persistence и transaction behavior тестируются на настоящем PostgreSQL.

SQLite не используется как test substitute для PostgreSQL behavior.

---

## 37. Frontend tests

Используются:

- Vitest;
- Vue Test Utils.

Тестируются прежде всего:

- сложные компоненты;
- composables;
- validation behavior;
- critical state transitions.

Не требуется покрывать unit tests каждый простой UI-компонент.

---

## 38. End-to-end tests

Полноценный E2E framework не является обязательной частью первой инфраструктуры.

Он может быть добавлен позднее для небольшого набора критических пользовательских сценариев, например:

- добавить вещь;
- пройти ревизию;
- продолжить незавершенную ревизию;
- завершить ревизию.

Не требуется строить огромный browser test suite.

---

## 39. Linting и formatting

### Ruff

Используется для Python:

- formatting;
- linting;
- import cleanup;
- базовых code-quality checks.

Предпочтительно не собирать несколько Python linters там, где Ruff уже закрывает задачу.

---

## 40. Static typing Python

### mypy

Используется прагматично.

Цель:

- ловить реальные type errors;
- помогать агенту и разработчику понимать интерфейсы.

Не цель:

- добиться абсолютной типовой чистоты любой ценой;
- писать сложные type gymnastics ради удовлетворения checker.

Если конкретная библиотека создает непропорциональное количество type noise, допустимы локальные exclusions/ignores.

---

## 41. Logging

На первом этапе достаточно обычных application logs.

Предпочтительно использовать структурированные поля там, где это удобно.

Не вводятся заранее:

- ELK;
- Loki;
- Grafana stack;
- distributed tracing.

---

## 42. Metrics и observability

В первую версию не входят:

- Prometheus;
- OpenTelemetry;
- tracing backend;
- отдельная observability platform.

Они добавляются только если эксплуатация продукта покажет реальную необходимость.

---

## 43. Error tracking

Sentry или аналогичный внешний error tracking не является обязательным компонентом первой версии.

Локальный/self-hosted продукт сначала опирается на:

- exception logs;
- HTTP errors;
- тесты.

Позже error tracking можно добавить независимо.

---

## 44. Backup

Backup — инфраструктурная задача.

Для первой версии достаточно backup PostgreSQL.

Также следует резервировать директорию загруженных файлов, если используются фотографии.

Отдельный пользовательский export/import workflow сейчас не требуется.

---

## 45. Что сознательно отсутствует в стеке

На первой версии **не используются**:

- Homebox;
- Django;
- Go backend;
- SQLModel;
- SQLite;
- GraphQL;
- Redis;
- Celery/RQ/Dramatiq;
- Kafka/RabbitMQ;
- Elasticsearch/OpenSearch/Meilisearch;
- Kubernetes;
- S3/MinIO;
- event bus;
- CQRS;
- full DDD;
- Clean Architecture ceremony;
- отдельный UnitOfWork framework;
- DI-container;
- Pinia;
- Nuxt;
- SSR;
- Tailwind;
- сложный form framework;
- full offline-first;
- native iOS application;
- multi-user;
- SaaS infrastructure.

Отсутствие этих технологий является осознанным способом ограничить сложность, а не техническим недостатком.

---

## 46. Принцип для coding-агентов

Архитектура должна быть простой для локального понимания задачи.

Coding-agent должен иметь возможность работать над одной feature, не загружая в контекст весь проект.

Предпочтительный характер задач:

```text
catalog/
revision/
categories/
profile/
```

а не изменение пяти глобальных архитектурных слоев для одной функциональности.

Следует избегать:

- глубоких цепочек абстракций;
- скрытой магии;
- чрезмерного числа интерфейсов;
- архитектурных паттернов без конкретного использования;
- глобального state;
- сложной инфраструктуры.

Код должен быть настолько прямым, насколько позволяет сохранение корректных транзакционных и доменных инвариантов.

---

## 47. Итоговый стек

```text
LANGUAGE
  Python
  TypeScript

BACKEND
  FastAPI
  Pydantic 2
  pydantic-settings

DATABASE
  PostgreSQL
  Psycopg 3
  SQLAlchemy 2.x ORM
  Alembic
  JSONB where appropriate

FRONTEND
  Vue 3
  TypeScript
  Vite
  Vue Router
  TanStack Vue Query
  PrimeVue

API
  REST / JSON
  OpenAPI
  openapi-typescript
  openapi-fetch

TESTING
  pytest
  real PostgreSQL
  Vitest
  Vue Test Utils

PYTHON TOOLING
  uv
  Ruff
  mypy

FRONTEND TOOLING
  npm

FILES
  local filesystem
  persistent Docker volume

DEPLOYMENT
  Docker Compose
    app
    postgres

NETWORK NOW
  LAN / VPN

NETWORK LATER
  Caddy
  HTTPS
  public domain if needed

AUTH NOW
  none inside application

AUTH LATER
  one local user
  password
  cookie session

SEARCH
  PostgreSQL only

BACKGROUND JOBS
  none
```

---

## 48. Архитектурная формула стека

> Один Python backend, один Vue SPA, один PostgreSQL, один Docker Compose и минимум вспомогательной инфраструктуры.

Если новая технология не решает существующую проблему, она не добавляется.

Следующий архитектурный этап после фиксации этого документа:

> **предметная модель первой версии «Каталог + Ревизия».**
