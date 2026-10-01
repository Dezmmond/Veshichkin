# Этап 1 — Фундамент и исполняемый каркас

Период: **1–7 октября 2026 года**  
Проект: первая версия **«Каталог + Ревизия»**

Этот документ предназначен для технического отдела.

Он определяет **что должно быть реализовано на первом этапе и какие крупные работы требуется декомпозировать для coding-агентов**. Конкретную декомпозицию на агентские задачи, последовательность исполнения, границы файлов и промпты технический отдел определяет самостоятельно.

---

## 1. Цель этапа

К концу этапа должен существовать чистый, воспроизводимый проект с рабочими:

- FastAPI backend;
- PostgreSQL;
- Alembic migrations;
- Vue 3 frontend;
- OpenAPI → TypeScript contract generation;
- production build;
- Docker Compose deployment.

Проект должен быть готов к реализации каталога на следующем этапе без переделки базового toolchain и deployment.

---

## 2. Что разрабатывается

### Project foundation

Нужно создать monorepo с отдельными backend/frontend частями и понятными командами:

- local backend development;
- local frontend development;
- migrations;
- tests;
- frontend build;
- OpenAPI client generation;
- production build/start.

### Backend foundation

Использовать зафиксированный стек:

- Python;
- FastAPI;
- Pydantic 2;
- pydantic-settings;
- SQLAlchemy 2.x;
- Psycopg 3;
- Alembic;
- PostgreSQL;
- sync DB path;
- uv;
- Ruff;
- mypy;
- pytest.

Нужны:

- application entrypoint;
- settings;
- DB Session dependency;
- migration setup;
- health/readiness endpoint;
- базовый HTTP error handling;
- vertical feature-oriented package structure.

### Initial persistence model

Нужно подготовить минимальную PostgreSQL schema, способную поддержать первую версию продукта:

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

Не вводить:

- multi-user;
- tenant;
- purchasing/replacement;
- EAV;
- event bus;
- generic workflow engine.

Технический отдел определяет конкретную структуру таблиц и relations при декомпозиции, сохраняя эти продуктовые возможности и простоту модели.

### Initial data

Нужен стартовый набор данных, позволяющий начать работу без ручного проектирования справочников:

- базовые категории;
- базовые purposes/справочные значения, если они нужны реализации;
- единая condition scale;
- climate values.

### Frontend foundation

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
- Vue Test Utils;
- npm.

Нужно подготовить:

- application shell;
- mobile-first navigation baseline;
- маршруты/заглушки основных feature;
- API client integration;
- подтвержденный frontend → backend request.

Не добавлять на этом этапе:

- Pinia;
- Nuxt;
- Tailwind;
- отдельный form framework;
- PWA/offline infrastructure.

### Deployment

Нужен Docker Compose минимум из:

```text
app
postgres
```

Production `app` должен обслуживать:

- `/api/...`;
- собранный Vue SPA.

Данные PostgreSQL должны быть persistent.

Приложение пока рассчитывает на LAN/VPN и не включает собственную auth.

### Quality baseline

Нужно обеспечить:

- backend tests;
- frontend tests;
- migration smoke test на реальном PostgreSQL;
- production build check;
- воспроизводимую генерацию OpenAPI TypeScript client;
- базовые lint/typecheck команды.

---

## 3. Что техническому отделу требуется декомпозировать для агентов

Технический отдел должен самостоятельно разложить на агентские задачи следующие крупные работы:

1. **Bootstrap monorepo и developer tooling.**
2. **Backend/FastAPI + settings + PostgreSQL/SQLAlchemy foundation.**
3. **Alembic и initial persistence schema.**
4. **Seed/reference data baseline.**
5. **Vue/Vite application shell и routing/UI foundation.**
6. **OpenAPI → generated TypeScript client pipeline.**
7. **Docker Compose и production single-app build.**
8. **Test/lint/typecheck baseline и smoke verification.**
9. **Integration pass всего этапа.**

Это перечень объектов декомпозиции, а не готовые agent tasks.

Технический отдел сам определяет:

- размер каждой задачи;
- зависимости;
- возможность параллельного запуска агентов;
- ownership файлов;
- порядок merge;
- проверки;
- критерии приемки конкретного агентского результата.

---

## 4. Инварианты этапа

При декомпозиции и реализации нельзя нарушать следующие решения:

- один monorepo;
- один deployable application;
- PostgreSQL — единственная БД;
- sync SQLAlchemy/Psycopg path;
- Alembic — единственный production migration path;
- REST/JSON;
- OpenAPI — контракт frontend/backend;
- generated TypeScript API types;
- vertical feature-based backend structure;
- без Clean Architecture/DDD ceremony;
- без отдельного Unit of Work;
- без DI-container;
- без Redis/workers;
- без auth;
- без multi-user;
- без search engine;
- без S3;
- без Kubernetes.

---

## 5. Критерии приемки этапа

Первый этап завершен только если новый разработчик может по README:

1. поднять PostgreSQL;
2. установить backend dependencies;
3. применить migrations;
4. запустить FastAPI;
5. установить frontend dependencies;
6. запустить Vite;
7. открыть приложение;
8. увидеть успешный запрос frontend → backend;
9. сгенерировать TypeScript API client из OpenAPI;
10. запустить backend tests;
11. запустить frontend tests;
12. собрать production;
13. поднять production Docker Compose;
14. открыть собранный SPA;
15. убедиться, что данные PostgreSQL переживают restart.

Также:

- пустая БД разворачивается только migrations;
- отсутствует production-зависимость от `create_all()`;
- структура проекта соответствует feature-oriented подходу;
- базовая persistence schema покрывает обязательные понятия будущих этапов;
- нет реализации функций вне scope первого этапа.

---

## 6. Не делать на первом этапе

Не тратить время на:

- полноценный Catalog CRUD UI;
- Revision UI;
- purchasing;
- statistics;
- AI/search;
- photos;
- auth;
- PWA;
- offline cache;
- visual polish;
- сложную observability;
- лишние архитектурные abstraction layers.

Первый этап должен закончиться **надежным исполняемым фундаментом**, а не частично реализованным продуктом поверх нестабильной инфраструктуры.

---

## 7. Передача в следующий этап

После приемки технический отдел должен передать в разработку этапа 2:

- рабочий repository;
- зафиксированный schema baseline;
- рабочие migrations;
- working API/frontend contract pipeline;
- working Docker Compose;
- подтвержденный production build;
- результаты smoke checks;
- список известных технических ограничений/рисков, если они остались.

Следующий этап:

> **Каталог end-to-end.**
