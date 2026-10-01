# Homebox: техническая разведка репозитория

Исследованный коммит: `3d84c421`. Дата: 2026-10-01.

Исследование выполнено чтением исходников. Сборки и тесты не запускались: они создают файлы и другие артефакты. В ходе исследования файлы не изменялись; этот отчёт добавлен отдельным последующим запросом. Перепроектирование и предметная функциональность для гардероба не выполнялись.

## 1. Backend

### Точки входа и слои

| Область | Файл и символы |
| --- | --- |
| Запуск приложения | `backend/app/api/main.go`: `main()`, `run()` — конфигурация, база, репозитории, сервисы, HTTP-сервер. |
| HTTP-маршруты | `backend/app/api/routes.go`: `app.mountRoutes()` регистрирует маршруты Chi, включая `/api/v1/entities`, `/tags`, `/entity-types`; `notFoundHandler()` обслуживает встроенный frontend. |
| Контроллер сущностей | `backend/app/api/handlers/v1/v1_ctrl_entities.go`: `HandleEntitiesGetAll`, `HandleEntitiesCreate`, `HandleEntityGet`, `HandleEntityUpdate`, `HandleEntityPatch`, `HandleEntityDelete`. |
| Сервис сущностей | `backend/internal/core/services/service_entities.go`: `EntityService.Create`, `Duplicate`, `CsvImport`, операции с asset ID. |
| Репозиторий сущностей | `backend/internal/data/repo/repo_entities.go`: `EntityRepository`, запросы, изменения, DTO и преобразование результатов. |
| Проверка запросов | `backend/internal/web/adapters/decoders.go`: `DecodeBody()` вызывает `validate.Check()` и, при наличии, метод DTO `Validate()`. |

Цепочка controller → service → repository не обязательна: создание проходит через `EntityService.Create`, а GET, PUT, PATCH и DELETE обращаются к репозиторию напрямую.

### Модель Entity

Авторитетное описание модели: `backend/internal/data/ent/schema/entity.go`, методы `Entity.Fields()` и `Entity.Edges()`.

- Предметы и места хранения используют общую модель `Entity`. Обязательная связь с `EntityType` различает их через `is_location`.
- Сущность принадлежит группе; поддерживает родителя и детей, отдельное переопределение местоположения, теги, пользовательские поля, вложения и записи обслуживания.
- Поля включают количество, архивное состояние, asset ID, идентификационные данные, покупку, продажу, страхование и гарантию.
- `BaseMixin` задаёт UUID и временные метки, `DetailsMixin` — имя и описание: `backend/internal/data/ent/schema/mixins/base.go`.
- Сгенерированная структура хранения: `backend/internal/data/ent/entity.go`, `Entity`.
- Контракты API: `EntityCreate`, `EntityUpdate`, `EntityPatch`, `EntitySummary`, `EntityOut` в `backend/internal/data/repo/repo_entities.go`.
- Наследование местоположения: `resolveLocationOverride()` и связанные функции в `backend/internal/data/repo/repo_entity_location.go`.

### База и миграции

`backend/app/api/setup.go`, `setupDatabase()`, поддерживает SQLite и PostgreSQL, создаёт Ent-клиент и запускает `runMigrations()` → `goose.Up()` при старте.

- Настройки: `backend/internal/sys/config/conf_database.go`, `Database`.
- Встроенные миграции: `backend/internal/data/migrations/migrations.go`, `Migrations()`.
- Отдельные истории: `backend/internal/data/migrations/sqlite3/` и `backend/internal/data/migrations/postgres/`.
- Генерация Ent: директива `go:generate` в `backend/internal/data/ent/generate.go`.
- Схема для генерируемого клиента: `backend/internal/data/ent/migrate/schema.go`.

Транзакционность миграций различается. SQLite-миграция `sqlite3/20260416120001_merge_entities.go` регистрирует `Up20260402120001` через `goose.AddMigrationNoTxContext`. PostgreSQL-миграция `postgres/20260416120000_merge_entities.go` регистрирует `Up20260402120000` через `goose.AddMigrationContext` и получает `*sql.Tx`.

### Транзакции создания и изменения

Методы таблицы находятся в `backend/internal/data/repo/repo_entities.go`, если не указано иное.

| Операция | Наблюдаемая граница транзакции |
| --- | --- |
| `EntityRepository.Create()` | Нет явной общей транзакции вокруг проверок, определения типа по умолчанию, сохранения и чтения результата. |
| `EntityRepository.UpdateByGroup()` | PUT не охвачен общей транзакцией: запись сущности/тегов, синхронизация местоположений детей и пользовательские поля изменяются отдельными операциями. Поздняя ошибка может возникнуть после успешных ранних записей. |
| `EntityRepository.CreateFromTemplate()` | Явные `r.db.Tx()`, commit и отложенный rollback, если commit не выполнен. |
| `EntityRepository.Patch()` | Явная транзакция для изменений и синхронизации тегов через `patchSyncTags()`. |
| `EntityRepository.Duplicate()` | Явная транзакция для сущности и связанных записей БД. |
| `EntityService.CsvImport()` | Несколько вызовов репозитория без транзакции на весь импорт; файл `backend/internal/core/services/service_entities.go`. |

Это границы на уровне приложения. Отсутствие внешней транзакции не означает, что отдельная сгенерированная Ent-операция не использует внутреннюю транзакцию.

### Тесты backend

- `backend/internal/data/repo/repo_entities_test.go`: CRUD, связи, дробные количества, запрет отрицательных и нечисловых/бесконечных количеств, поведение местоположений. Примеры: `TestEntityRepository_Create_WithFractionalQuantity`, `TestEntityRepository_Create_RejectsNonFiniteQuantity`, `TestEntityRepository_RejectsNegativeQuantity`.
- `backend/internal/data/repo/repo_entities_crosstenant_test.go`: `TestEntityRepository_UpdateByGroup_CrossTenantLeak`, `TestEntityRepository_UpdateByGroup_CrossTenantFieldWrite`.
- `backend/internal/core/services/service_entities_test.go`: `TestEntityService_CsvImport_AssetIDIdempotent`, `TestEntityService_CsvImport_AssetIDAutoIncrement`.
- `backend/internal/data/repo/main_test.go` и `backend/internal/core/services/main_test.go`: `MainNoExit()` использует SQLite в памяти и `client.Schema.Create()`. Эти тесты не проверяют производственную историю Goose-миграций.
- `backend/internal/data/search/meilisearch_test.go`: интеграционные тесты пропускаются без `TEST_MEILISEARCH_URL`.

## 2. Frontend

### Стек и структура

`frontend/package.json` фиксирует Nuxt 4.4.7, Vue 3.5.20, TypeScript, Pinia и Tailwind. `frontend/nuxt.config.ts`, `defineNuxtConfig`, отключает SSR, настраивает PWA и проксирует `/api` на порт 7745 при разработке. Скрипт `build` выполняет `nuxt generate`.

### Экраны сущностей

| Сценарий | Реализация |
| --- | --- |
| Список и поиск | `frontend/pages/search.vue`: `search()`, пагинация, сортировка, фильтры тегов, мест, типов сущностей, пользовательских полей и архива. `frontend/pages/items.vue` перенаправляет сюда. |
| Таблица и карточки | `frontend/components/Item/View/Selectable.vue`: `itemView`, `setViewPreference()`, сохранение выбранного представления. |
| Детали | `frontend/pages/item/[id]/index.vue`: данные сущности, изменение количества через PATCH, вложения, операции с дочерними предметами. |
| Создание | `frontend/components/Entity/CreateModal.vue`: `create()`, `onEntityTypeChanged()`, `handleTemplateSelected()`; обычное создание, места хранения и создание из шаблонов. |
| Редактирование | `frontend/pages/item/[id]/index/edit.vue`: `saveItem()` вызывает `api.items.update()`; количество, архив, теги, пользовательские поля и вложения. |
| Места хранения | `frontend/pages/locations.vue`, `frontend/pages/location/[id]/index/`: отдельные экраны над общим API сущностей. |

В `Entity/CreateModal.vue`, `create()`, фотографии загружаются отдельными запросами уже после создания сущности.

### Мобильное поведение

- `frontend/components/App/CreateModal.vue`: `isDesktop = useMediaQuery("(min-width: 768px)")`; на desktop используется Dialog, на меньших экранах — Drawer.
- Страницы деталей и редактирования используют адаптивные классы Tailwind; страница редактирования учитывает высоту мобильного заголовка.
- `frontend/composables/use-barcode-detector.ts`: `useBarcodeDetector()` запрашивает камеру через `getUserMedia` с предпочтением `facingMode: { ideal: "environment" }`.
- PWA-манифест и кэширование задаются в `frontend/nuxt.config.ts`. Наличие конфигурации не подтверждает работоспособность приложения без сети.

### API-клиент

- `frontend/lib/api/classes/items.ts`: `ItemsApi`, методы `getAll`, `get`, `create`, `update`, `patch` и методы для мест хранения обращаются к `/entities`.
- `frontend/composables/use-api.ts`: `useUserApi()` добавляет `X-Tenant` и обработку ответов, связанных с авторизацией.
- `frontend/lib/requests/requests.ts`: `Requests` оборачивает `fetch`.
- `frontend/lib/api/types/data-contracts.ts`: генерируемые контракты. Генерация описана задачами `swag` и `typescript-types` в `Taskfile.yml`.

### Локализация

`frontend/plugins/i18n.ts`: `createI18n`, `messages()`, `messageCompiler`. JSON-файлы из `frontend/locales/` загружаются заранее; английский — резервный язык; выбранный язык берётся из настроек или браузера. Используется `IntlMessageFormat`.

Локализация неполная: в `frontend/pages/item/[id]/index.vue` отображение архивного состояния использует литералы `"Yes"` и `"No"`.

## 3. Точки расширения для форка

| Область | Конкретная реализация |
| --- | --- |
| Определение Entity | `backend/internal/data/ent/schema/entity.go`, `Entity`; DTO в `repo_entities.go`; frontend-контракты в `data-contracts.ts`. |
| Хранение количества | `Entity.Fields()`: `field.Float("quantity").Default(1)`; DTO используют `float64`. |
| Проверка количества | `repo_entities.go`, `validateQuantity()`: запрет отрицательных значений, NaN и бесконечности. Вызывается при обычном и шаблонном создании, PUT и PATCH. В Ent-поле отдельное ограничение неотрицательности не объявлено. |
| Количество в UI | `Entity/CreateModal.vue`: `form.quantity = 1`, `min=0`, `step="any"`; `mainFields` на странице редактирования задаёт минимум 0. |
| Значение количества по умолчанию | `EntityRepository.Create()` явно вызывает `SetQuantity(data.Quantity)`. Поэтому пропущенное количество в обычном API-запросе становится нулём, а не значением 1 из схемы. |
| Теги | `backend/internal/data/ent/schema/tag.go`, `Tag`: иерархия и связь многие-ко-многим с сущностями. `backend/internal/data/repo/repo_tags.go`, `TagRepository`: CRUD, `checkDepth()`, `checkCycle()`. Назначение сущности через `TagIDs`, `patchSyncTags()`. Контроллер: `backend/app/api/handlers/v1/v1_ctrl_tags.go`. |
| EntityType | `backend/internal/data/ent/schema/entity_type.go`, `EntityType`: `is_location`, иконка, шаблон по умолчанию. `backend/internal/data/repo/repo_entity_types.go`, `EntityTypeRepository`; `backend/app/api/handlers/v1/v1_ctrl_entity_types.go`, методы `HandleEntityType*`. UI: `frontend/stores/entityTypes.ts`, `frontend/pages/collection/index/entity-types.vue`. |
| Архив | `Entity.Fields()`: boolean по умолчанию false. `EntityUpdate.Archived` сохраняется через `UpdateByGroup().SetArchived()`. `QueryByGroup()` исключает архивные записи, если не установлен `IncludeArchived`. В `EntityPatch` поля архива нет. |
| Транзакции | `EntityRepository.Create`, `UpdateByGroup`, `CreateFromTemplate`, `Patch`, `Duplicate` — границы описаны выше. |

Исторические миграции дробного количества: `sqlite3/20260314103000_item_quantity_decimals.sql` полагается на динамическую типизацию SQLite; `postgres/20260314103001_item_quantity_decimals.sql` переводит столбцы в `double precision`. Обе находятся в `backend/internal/data/migrations/`.

## 4. Команды сборки, тестирования и запуска

Команды приведены для последующего выполнения и в рамках разведки не запускались. Источники: `Taskfile.yml`, `frontend/package.json`, конфигурации тестов, `Dockerfile`, `docker-compose.yml`.

### Инструменты и сборка

- Go 1.26.0: `backend/go.mod`.
- pnpm 10.28.0: `frontend/package.json`, `packageManager`.
- Docker-сборка использует Node 22: `Dockerfile`.
- `CONTRIBUTING.md` указывает более старые минимальные версии; соответствие документации текущей сборке не подтверждено.

```bash
# Корень репозитория
task setup
task go:build                 # build/backend

# Frontend
cd frontend
pnpm install --frozen-lockfile
pnpm build                   # .output/public
```

`task setup` устанавливает генераторы и выполняет `go mod tidy` и `pnpm install`. `task generate` генерирует Ent, документацию API и TypeScript-контракты. Эти команды изменяют файлы.

### Backend-тесты и проверки

```bash
# Корень репозитория
task go:test
task go:coverage              # race + coverage
task go:test:meilisearch      # временный сервис в Docker
task go:lint
task ui:check
```

### Frontend/API-тесты

Требуется работающий backend на `127.0.0.1:7745`: `frontend/test/config.ts`, `BASE_URL`.

```bash
cd frontend
TEST_SHUTDOWN_API_SERVER= pnpm exec vitest run \
  --config ./test/vitest.config.ts --no-file-parallelism
pnpm run lint
```

`frontend/test/vitest.config.ts` включает `**/*.test.ts`: локальные тесты и тесты живого API-клиента из `frontend/lib/api/__test__/`.

### Браузерные тесты

Требуется полное приложение на порту 3000.

```bash
cd frontend
pnpm exec playwright install --with-deps
TEST_SHUTDOWN_API_SERVER= E2E_BASE_URL=http://localhost:3000 \
  pnpm exec playwright test -c ./test/playwright.config.ts
```

`frontend/test/playwright.config.ts` запускает desktop-проекты Chromium, Firefox и WebKit; `testDir` — `./e2e`.

Альтернативная оркестрация из `Taskfile.yml`: `task test:ci`, `task test:ci:postgresql`, `task test:e2e`. Для PostgreSQL требуется доступный сервер с параметрами, указанными в соответствующей задаче.

**Особенность teardown:** `frontend/test/setup.ts`, `teardown()`, и `frontend/test/playwright.teardown.ts`, `globalTeardown()`, проверяют строковую переменную `TEST_SHUTDOWN_API_SERVER` на truthiness. Строка `"false"` тоже запускает завершение процессов. Поэтому в командах выше передано пустое значение. Vitest teardown вызывает `pkill -SIGTERM api`; Playwright teardown дополнительно завершает процессы `task`.

### Тест обновления версии

`frontend/test/upgrade/upgrade-verification.spec.ts` требует заранее подготовленных данных старой версии, путь задаётся `TEST_DATA_FILE`. `.github/workflows/upgrade-test.yaml` содержит следующую команду:

```bash
cd frontend
TEST_DATA_FILE=/tmp/test-users.json \
E2E_BASE_URL=http://localhost:7745 \
pnpm exec playwright test \
  -c ./test/playwright.config.ts \
  --project=chromium \
  test/upgrade/upgrade-verification.spec.ts
```

Обнаружение этого теста не подтверждено: путь находится вне `testDir: "./e2e"` текущей конфигурации. Это не проверенная команда для полного прогона миграционных тестов.

### Локальный запуск полного приложения

```bash
# Терминал 1, корень репозитория
task go:run

# Терминал 2, корень репозитория
task ui:dev
```

Frontend: `http://localhost:3000`, API: `http://localhost:7745`. Задача `go:run` запускает генерацию, включает demo-режим и отключает хеширование паролей для разработки.

Альтернатива:

```bash
docker compose up --build
```

`docker-compose.yml` собирает обе части и публикует приложение на `http://localhost:3100`. `Dockerfile` копирует результат frontend-сборки в `backend/app/api/static/public` перед компиляцией backend. Сам по себе `task go:build` frontend не собирает.

## 5. Карта репозитория

```text
backend/
  app/api/                 Запуск, HTTP-контроллеры, встроенный UI и документация API
  app/tools/typegen/       Обработка генерируемых TypeScript-контрактов
  internal/core/services/ Сервисы, импорт и экспорт
  internal/data/
    ent/schema/            Авторитетные описания моделей
    ent/                   Генерируемый код хранения
    repo/                  Запросы, изменения, DTO
    migrations/            Истории миграций SQLite и PostgreSQL
    search/                Поиск через БД и Meilisearch
  internal/sys/            Конфигурация, валидация, инфраструктура
  internal/web/            HTTP-адаптеры и middleware
  pkgs/                    Общие утилиты
frontend/
  pages/                   Маршруты Nuxt
  components/              Формы, представления сущностей, UI
  composables/, stores/    Общая логика и состояние
  lib/api/, lib/requests/ Контракты, API-клиенты и транспорт
  locales/, plugins/      Переводы и плагины приложения
  test/                    Vitest, браузерные тесты и тесты обновления
docs/                      Документация проекта
Taskfile.yml               Команды разработки
Dockerfile                 Общая сборка frontend/backend
docker-compose.yml         Локальный запуск контейнера
```

## 6. Основные файлы для дальнейшей работы

1. `backend/app/api/main.go`, `setup.go`, `routes.go` — запуск, БД, маршруты.
2. `backend/internal/data/ent/schema/entity.go`, `entity_type.go`, `tag.go` — модель.
3. `backend/internal/data/repo/repo_entities.go` — DTO, запросы, изменения, транзакции.
4. `backend/internal/data/repo/repo_entity_location.go` — иерархия и местоположения.
5. `backend/internal/core/services/service_entities.go` — создание, импорт и asset ID.
6. `backend/app/api/handlers/v1/v1_ctrl_entities.go` — HTTP-контракт сущностей.
7. `backend/internal/data/migrations/migrations.go` и каталоги обоих диалектов — миграции.
8. `frontend/components/Entity/CreateModal.vue` — создание.
9. `frontend/pages/item/[id]/index.vue`, `index/edit.vue` — детали и редактирование.
10. `frontend/pages/search.vue` — поиск и список.
11. `frontend/lib/api/classes/items.ts`, `types/data-contracts.ts` — клиент и типы API.
12. `frontend/plugins/i18n.ts`, `frontend/locales/` — локализация.
13. `Taskfile.yml`, `frontend/package.json`, `frontend/test/*.ts` — рабочие команды и тестовые harness.

## 7. Открытые технические вопросы

1. **Фактическое состояние сборки и тестов.** Совместимость объявленного toolchain и зависимостей не проверена запуском.
2. **Конкурентное назначение asset ID.** `EntityService.Create()` читает максимальный ID до создания; поведение уникальности при конкурентных запросах не установлено.
3. **Восстановление после частичного PUT.** `UpdateByGroup()` не имеет общей транзакции; ожидаемая обработка частично выполненных изменений в изученном коде не документирована.
4. **Надёжность миграций.** Истории Goose не прогонялись; тесты репозиториев с `Schema.Create()` их обходят.
5. **Обнаружение upgrade-тестов.** Работает ли указанный workflow при текущем `testDir` Playwright?
6. **Мобильные сценарии и работа без сети.** Камера и PWA не проверены в браузере; конфигурация Playwright содержит desktop-проекты.
