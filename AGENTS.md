# Рабочий протокол Codex — Veshichkin

## Роль и границы задачи

Codex — исполнитель небольших инженерных задач в проекте **Veshichkin**. Работай по постановке технического планировщика.

Не принимай архитектурные решения самостоятельно, если постановка явно не делегирует это. Не расширяй scope задачи и не исправляй побочные проблемы без отдельного поручения; фиксируй их в отчёте.

Эти инструкции действуют для всего репозитория. Перед изменениями учитывай вложенные `AGENTS.md`, если они появятся в отдельных каталогах. Явная постановка пользователя имеет приоритет над локальными правилами.

Veshichkin — новый проект с нуля. Не переносить в него архитектуру, соглашения, зависимости или код Homebox без отдельного прямого указания.

## Текущий архитектурный baseline

Проект — один monorepo:

```text
backend/
frontend/
```

Базовые решения:

- один deployable application;
- PostgreSQL — единственная production БД;
- backend: Python, FastAPI, Pydantic 2, pydantic-settings, SQLAlchemy 2.x, Psycopg 3, Alembic;
- DB path — синхронный;
- `uv` — backend dependency manager;
- Ruff, mypy, pytest;
- frontend: Vue 3, TypeScript, Vite, Vue Router, TanStack Vue Query, PrimeVue;
- `openapi-typescript`, `openapi-fetch`;
- Vitest, Vue Test Utils;
- npm — frontend package manager;
- REST/JSON;
- OpenAPI — контракт frontend/backend;
- TypeScript API types генерируются из OpenAPI и не поддерживаются вручную;
- backend организуется по vertical feature-oriented принципу;
- production application обслуживает `/api/...` и собранный Vue SPA;
- Docker Compose первого этапа состоит как минимум из `app` и `postgres`.

Не вводить без отдельного архитектурного решения:

- Clean Architecture/DDD ceremony;
- отдельный Unit of Work;
- DI container;
- Redis;
- workers/queues;
- auth;
- multi-user/tenant;
- search engine;
- S3;
- Kubernetes;
- Pinia;
- Nuxt;
- Tailwind;
- form framework;
- PWA/offline infrastructure.

Не проектировать абстракции «на будущее», если они не нужны текущему acceptance criteria.

## Текущий product scope

Первый этап — **фундамент и исполняемый каркас**.

На этом этапе допустимы:

- monorepo/bootstrap;
- FastAPI runtime;
- settings;
- PostgreSQL/SQLAlchemy foundation;
- Alembic;
- initial persistence schema;
- seed/reference data;
- Vue/Vite application shell;
- routing/navigation baseline;
- frontend → backend integration;
- OpenAPI → TypeScript generation;
- Docker Compose;
- production build;
- targeted tests/lint/typecheck/smoke.

На первом этапе не реализовывать без прямого поручения:

- полноценный Catalog CRUD UI;
- Revision UI;
- purchasing/replacement;
- statistics;
- AI/search;
- photos;
- auth;
- PWA/offline;
- visual polish;
- сложную observability.

Если во время задачи найден полезный будущий функционал вне scope — запиши его в отчёт, но не реализовывай.

## Язык

Отчёты, reasoning summaries, результаты исследований, описания проблем и сообщения техническому планировщику пиши **на русском языке**.

Код, идентификаторы, имена файлов, commit messages и общепринятые технические термины можно оставлять на английском.

Если постановка задаёт имя Markdown-файла результата, этот файл — главный интерфейс между Codex и техническим планировщиком.

## Multi-agent

Multi-agent используй только там, где независимое параллельное выполнение реально экономит время.

По умолчанию:

- максимум **2 субагента + координатор**;
- 3 субагента допустимы только при трёх действительно независимых областях;
- 4 и более субагента не запускать без прямого указания пользователя.

Предпочтительные разделения:

- backend / frontend;
- implementation / tests;
- schema / API;
- две независимые части репозитория.

Не поручай нескольким агентам одновременно менять одни и те же файлы.

Каждому субагенту задавай узкий scope, конкретный ownership файлов/каталога, конкретный результат и лимит времени.

Не заставляй нескольких агентов повторно исследовать одну и ту же область.

Простые и неделимые изменения выполняй одним агентом без искусственной параллелизации.

Координатор сводит результаты, устраняет противоречия, не повторяет уже выполненное исследование без причины и отвечает за финальный результат.

Reasoning субагентов держать минимальным. Не тратить квоту на длинные архитектурные рассуждения, если решение уже дано в постановке.

## Лимиты времени и экономия квоты

Используй `timeout` или эквивалент.

Если постановка не задаёт другой лимит:

| Действие | Лимит |
| --- | --- |
| Обычная shell-команда | 15 секунд |
| HTTP/API-запрос | 5 секунд |
| Локальный startup/readiness | 30 секунд |
| Targeted test | 60 секунд |
| Dependency resolution/install | 60 секунд |
| Targeted build/typecheck | 60 секунд |
| Исследовательский субагент | обычно 30–60 секунд |

При достижении лимита:

1. останови команду и порождённые ею процессы;
2. запиши `TIMEOUT`;
3. не повторяй автоматически;
4. продолжай с имеющимися данными.

Повтор допускается только при понятной, дешёвой и конкретной причине.

`TIMEOUT` — результат проверки, а не повод ждать ещё несколько минут.

Не запускать повторно уже успешную дорогую проверку без изменения, которое могло повлиять на её результат.

Не выполнять repo-wide исследование, если постановка или предыдущий отчёт уже указывает нужные файлы.

## Проверки

Предпочитай минимальные проверки, соответствующие изменённому scope.

Примеры:

- один Python package/module;
- один pytest-файл или конкретный test;
- один frontend component/test;
- targeted typecheck;
- один migration smoke;
- один HTTP smoke path.

Не запускать автоматически, если этого не требует acceptance criteria:

- полный backend test suite;
- полный frontend test suite;
- полный Ruff/mypy по всему проекту;
- полный frontend production build;
- Docker build;
- Docker Compose integration;
- PostgreSQL integration/smoke;
- OpenAPI regeneration;
- reinstall всех зависимостей.

Полные проверки допустимы на integration/pass задачах или когда постановка прямо этого требует.

Для документационной задачи не запускать сборки и тесты.

## Логи

Большие stdout/stderr направляй в `/tmp`, желательно в отдельный каталог задачи.

Не перечитывай длинные логи целиком. Используй `tail`, `rg`, `grep` и выборочные строки.

В итоговый отчёт включай статус, ключевую ошибку и путь к полному логу. Не вставляй большие логи в Markdown-отчёт.

## Изменения кода

Перед редактированием определи минимальный набор файлов.

Не выполняй opportunistic refactoring.

Не затрагивай посторонние изменения пользователя.

Не меняй зависимости без прямого поручения или объективной необходимости текущей задачи.

Не добавляй библиотеку, если задача решается средствами уже выбранного стека.

Не создавай generic abstraction layer до появления реальной повторяющейся потребности.

Не коммить изменения, если постановка явно этого не требует.

## Backend conventions

Backend находится в `backend/`.

Dependency manager — `uv`.

Предпочтительный layout:

```text
backend/
  pyproject.toml
  uv.lock
  src/
    veshichkin/
  tests/
```

Основные правила:

- FastAPI;
- Pydantic 2;
- pydantic-settings;
- SQLAlchemy 2.x;
- Psycopg 3;
- sync DB path;
- Alembic;
- PostgreSQL only;
- vertical feature-oriented package structure;
- без отдельного repository/service/interface слоя только ради архитектурной формы;
- без Unit of Work abstraction;
- без DI container.

DB Session dependency должна быть простой и явной.

Production schema создаётся только Alembic migrations.

Не использовать `Base.metadata.create_all()` как production migration path.

Тесты могут использовать отдельные удобные setup-механизмы только если это не маскирует обязательную проверку реальных Alembic migrations там, где она требуется.

Для Python:

- форматирование и lint — Ruff;
- type checking — mypy;
- tests — pytest.

Не отключай правило lint/typecheck глобально ради локальной ошибки без веской причины.

## Persistence и migrations

PostgreSQL — единственная БД проекта.

Не добавлять SQLite compatibility.

Каждое изменение production schema должно иметь Alembic migration.

Пустая production БД должна разворачиваться только миграциями.

Initial persistence model первого этапа должна в итоге поддержать:

- category hierarchy;
- purposes;
- individual catalog item;
- grouped catalog item / quantity;
- condition;
- climate applicability;
- базовые структурированные характеристики;
- JSONB для дополнительных характеристик;
- один профиль пользовательских замеров;
- revision session;
- сохраняемый revision progress/results;
- last completed verification state/date для категории.

Не вводить на этом этапе:

- multi-user;
- tenant;
- purchasing/replacement;
- EAV;
- event bus;
- generic workflow engine.

Конкретную структуру таблиц не придумывай заново, если она уже определена отдельным архитектурным решением или текущей постановкой.

## Frontend conventions

Frontend находится в `frontend/`.

Package manager — npm.

Использовать:

- Vue 3;
- TypeScript;
- Vite;
- Vue Router;
- TanStack Vue Query;
- PrimeVue;
- openapi-typescript;
- openapi-fetch;
- Vitest;
- Vue Test Utils.

Не добавлять без отдельного решения:

- Pinia;
- Nuxt;
- Tailwind;
- form framework;
- PWA/offline infrastructure.

Frontend state, полученный с backend, по умолчанию вести через TanStack Vue Query.

Не создавать глобальный client-state store, пока для него нет конкретной необходимости.

## OpenAPI contract

FastAPI/OpenAPI — источник контракта frontend/backend.

TypeScript API contract должен генерироваться воспроизводимо.

Не редактировать generated API types вручную.

Если backend API изменён и задача включает contract update:

1. обновить backend;
2. получить актуальную OpenAPI schema;
3. выполнить штатную генерацию;
4. проверить diff generated client/types;
5. выполнить только необходимые frontend checks.

Если генерация не входит в scope задачи — зафиксировать необходимость в отчёте, но не выполнять её самовольно.

## Deployment conventions

Цель первого этапа — один deployable application.

Docker Compose минимум:

```text
app
postgres
```

Production `app` должен обслуживать:

- `/api/...`;
- собранный Vue SPA.

PostgreSQL data должна быть persistent.

Приложение пока рассчитано на LAN/VPN.

Не добавлять собственную auth/security perimeter без отдельного архитектурного решения.

Не вводить reverse proxy, Kubernetes или дополнительные сервисы без необходимости.

## Отчётность

Если постановка задаёт имя Markdown-файла результата, этот файл — главный интерфейс между Codex и техническим планировщиком.

Отчёт должен быть кратким, на русском, фактическим, ориентированным на результат и без длинного процесса рассуждений.

Обычная структура отчёта для code task:

- `Verdict`;
- `Что изменено`;
- `Затронутые файлы`;
- `Проверки`;
- `Известные ограничения`;
- `Следующий шаг`.

Если постановка задаёт другую структуру — следуй ей.

Различай `PASS`, `FAIL`, `PARTIAL`, `SKIPPED`, `TIMEOUT`.

Не объявляй непроведённую проверку успешной.

## Финальный ответ Codex

После выполнения задачи ответ пользователю должен быть максимум 5 строк.

Указать:

- `PASS`, `FAIL` или `PARTIAL`;
- путь к result-файлу;
- какие исходники изменены;
- какие проверки выполнены;
- blocker, только если он есть.

Не пересказывай содержимое Markdown-отчёта в чате.