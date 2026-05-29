# Engram — Roadmap развития продукта

Живой документ направления продукта и **рабочая инструкция для будущих сессий**. Источник
приоритетов — исходная спека (`ENGRAM_project_spec_for_Claude_Codex_ru.md`), а не «по наитию».

- Исходная спека (зачем проект, ценность §6, DoD MVP §16): `ENGRAM_project_spec_for_Claude_Codex_ru.md`
- Утверждённый план MVP/переработок: `C:\Users\PC\.claude\plans\cryptic-sniffing-russell.md`
- Состояние: **MVP пройден** (M0–M6 + платформенный UI + R1 + двухслойный документ с rich-text
  телом), всё на ветке `main`. LLM — детерминированный mock.

Слой-карта бэкенда (соблюдать при правках): `api/` (роутеры) → `services/` (логика) →
`repositories/` (доступ к данным) → `models/` (ORM). LLM/эмбеддинги — только за адаптерами
`llm/base.py::LLMProvider` и `embeddings/base.py`.

---

## Принципы приоритезации (якорь — спека)

> Чтобы не стать «ещё одним Notion/Confluence», каждый приоритет сверяется со спекой §6.1.

- **Моат:** связанность документов + их **постоянно актуальное состояние**. Ценность (§6.1) =
  связанные артефакты → активные версии → подбор минимального контекста → анализ влияния. Спека §6.2:
  ценность **НЕ** в тексте/markdown/редакторе.
- **Тест на «не-Confluence»** для фичи: усиливает петлю связанной памяти (подбор → связи → влияние →
  согласованность) или только украшает авторинг? Второе — table stakes.
- **Платная LLM — осознанно:** включается только по явному решению. Mock — дефолт для офлайна и
  детерминированных тестов; не звать платные API без спроса.
- **Не делать лишнего** (спека §17.4, §20): без полного SDLC, обязательной UML, тяжёлой агентной
  иерархии.

---

## Что уже работает (реализовано)

- **Документная модель:** артефакты-документы по типам (project_brief / requirement / user_story /
  task / test_case / change_request), внутри — структурированные **Items** (R1, T1…: key/title/text/
  feature/refs); версии (`ArtifactVersion`, ровно одна `is_active`), журнал (`ChangeLog`),
  типизированные связи (7 типов в `enums.py::LinkType`).
- **Двухслойный документ:** rich-text **тело** (`content` = Tiptap JSON) + **Items** (machine-
  readable слой). Конверсия — `services/artifact_service.py::content_to_text` / `text_to_doc`
  (фронт-зеркало — `apps/web/src/lib/editor/content.ts`). Редактор: `apps/web/src/components/editor/`.
- **Воркфлоу** (`orchestration/engine.py::ProceduralWorkflowEngine`): `formalize` (описание → brief +
  4 документа + связи), `analyze_change` (CR → подбор контекста → ревизии → `changes`-связи).
- **Память/поиск:** `services/context_service.py::select_context` (pgvector → keyword fallback →
  обход графа на N hops); эндпоинт `/api/search/context`.
- **Согласованность:** `services/consistency_service.py` + `/api/consistency` — **7 из 7** правил §10.1.
- **UI** (Next.js): сайдбар-дерево, страницы документов (Content/Links/History), граф, формы
  formalize/change-request, отчёт согласованности, ручное создание/редактирование.
- **Тесты:** 30 pytest, включая `apps/api/tests/test_e2e_scenario.py`; демо — `scripts/seed_demo.py`.
- Баги аудита Codex **устранены** (см. ниже).

---

## Текущий план исполнения (поэтапно)

### Этап 1 — Зафиксировать и протестировать MVP (baseline) · ✅ завершён 2026-05-29

> **Итог:** pytest/ruff/eslint/`next build` зелёные; живой API с чистым consistency; регрессия
> Tiptap-round-trip проверена; найден и починен runtime-баг `flushSync` в редакторе
> (`RichTextEditor.tsx` — `setContent` отложен в microtask); браузерный проход DoD §16 — ок.

**Что:** доказать, что реализованный MVP работает сквозняком по DoD §16, закрыть регрессии.

**Как:**
1. Окружение: `docker compose -f infra/docker-compose.yml up -d`; `cd apps/api && uv sync &&
   uv run alembic upgrade head`. (DB на порту **5433**; в `.env` использовать `127.0.0.1`, не
   `localhost` — иначе WinError 10013 на IPv6.)
2. Backend-тесты: `uv run pytest` (создаёт/чистит отдельную БД `engram_test`). Должно быть 26 зелёных.
3. Засеять и пройти UI: `uv run python scripts/seed_demo.py`; `pnpm install && pnpm web:dev` →
   http://localhost:3000. Пройти все 8 пунктов §16: formalize → артефакты/связи/граф →
   change-request → затронутые + новые версии → отчёт согласованности.
4. **Зона регрессии:** change-request поверх Tiptap-контента. Цепочка: `mock.py::analyze_change_request`
   делает `content_to_text(item.content)` → append → `engine.py` оборачивает `text_to_doc(...)`.
   Проверить именно в браузере, что ревизованный документ рендерится текстом, а не сырым JSON.
   Создать документ в редакторе руками, затем прогнать CR, который его задевает.
5. Чистота: `uv run ruff check . && uv run ruff format .`; `pnpm --filter @engram/web lint`;
   `pnpm web:build`.

**DoD этапа:** 8 пунктов §16 воспроизводятся в браузере; pytest/ruff/lint/build зелёные; найденные
регрессии устранены.

### Этап 2 — Довести MVP до буквы спеки + тесты · ✅ завершён 2026-05-29

> **Итог:** правила §10.1 доведены до **7 из 7** (добавлены #1 `approved_requirement_without_source`,
> #4 `requirement_without_user_story`, #6 `archived_used_as_active`, #7 `approved_cr_without_new_version`);
> тест на каждое новое правило; **30 pytest зелёных**, ruff чисто.

**Что:** правила согласованности §10.1 с 3 до **7 из 7**; тесты на правила и оба workflow (§12.10).

**Как** (всё в `services/consistency_service.py`, добавлять `ConsistencyIssue(severity, code,
message, artifact_id, artifact_title, item_key)` в список `issues`; коды — строки):
- **#1 `approved_requirement_without_source`** (severity `error`): по артефактам
  `type==requirement and status==approved` без `source_ref` → issue. (После formalize у requirement-
  документа `source_ref == brief.id`, так что ловит в основном ручные.)
- **#4 `requirement_without_user_story`** (`warning`): построить `story_refs: set[(req_doc_id, key)]`
  из refs артефактов `type==user_story` (по образцу уже существующих `task_refs`/`test_refs` в этом
  файле), затем для каждого requirement-item проверить наличие в `story_refs`.
- **#6 `archived_used_as_active`** (`warning`): для каждого ref, чья цель-артефакт
  `status==archived`, флагнуть ссылающийся артефакт (активный документ не должен опираться на
  архивный как на актуальный).
- **#7 `approved_cr_without_new_version`** (`error`): для каждого `change_request` со статусом
  `applied`/`approved` взять его `changes`-связи (см. как считаются `changes_sources` в этом же
  файле) → цели; флагнуть, если цель не получила новую версию. Надёжный признак: у цели
  `current_version > 1` (после ревизии `update_artifact` инкрементит версию). Точнее — проверить
  `ChangeLog`/`ArtifactVersion.reason`, но это связывание по тексту — хрупко; начать с `current_version`.
- **Тесты:** `apps/api/tests/test_consistency_rules.py` — фикстуры, поднимающие/снимающие каждое
  правило; плюс убедиться, что у `formalize` и `analyze_change` есть отдельные тесты.

**DoD этапа:** §10.1 7/7, каждое правило и оба workflow покрыты тестом, pytest зелёный.

### Этап 3+ — Поэтапное наращивание · **следующий, по одному инкременту** (детали — в «Направлениях» ниже)

Порядок по ценности §6.1: реальная LLM → точечный impact → авто-починка/AI-связи → DecisionRecord →
context-UI.

---

## Архитектура документа: двухслойная (тело + Items)

> **Решение зафиксировано, тело реализовано.** Тело — свободный rich-text (Tiptap JSON в `content`).
> Items (R1, T1…) — machine-readable слой, фундамент consistency/impact/поиска. Items не исчезают.

- **Два пути создания.** LLM-путь: модель генерирует тело и Items. Human-путь: человек пишет тело,
  при следующей LLM-операции Items синхронизируются с телом.
- **Синхронизация Items — только явно** (ручная правка `items[]` через `ArtifactUpdate.items`, либо
  LLM-операция formalize/change/«Sync items»). Без фонового переписывания авторского текста.
- **Не сделано:** LLM-операция `extract_items_from_content(body) → items[]` для Human-пути (новый
  метод в `LLMProvider` + кнопка «Sync items» + эндпоинт). `content` уже rich-text; поле `items`
  без изменений.

---

## Направления развития (с детализацией «Что / Как»)

### 1. Реальная LLM — качество вывода
**Что:** заменить шаблонный mock на настоящую модель за тем же интерфейсом. Меняется качество текста,
структура — нет. ⚠️ платные токены, включать по решению пользователя.

**Как:**
- Новый `apps/api/src/engram/llm/anthropic.py`: класс `AnthropicLLMProvider(LLMProvider)` реализует
  два метода интерфейса (`llm/base.py`):
  - `formalize_project(description) -> FormalizedProject` — промпт просит вернуть JSON: `brief` +
    списки `requirements/user_stories/tasks/test_cases`, каждый item = `{key,title,text,feature,refs}`.
    Ключи стабильные (`R1..`, `US1..`, `T1..`, `TC1..`); `refs` в stories/tasks/tests — ключи
    requirements. Распарсить → собрать `GenItem`/`FormalizedProject`.
  - `analyze_change_request(change_text, context: list[ContextItem]) -> ChangeAnalysis` — в промпт
    отдать `context` (id/type/title/content), попросить `summary` + `proposals[{artifact_id,
    proposed_content, rationale}]`. **Важно:** `proposed_content` — plain text (engine обернёт через
    `text_to_doc`); не возвращать Tiptap JSON.
- `llm/factory.py::get_llm_provider`: добавить ветку `if name == "anthropic": return
  AnthropicLLMProvider()` (сейчас она кидает `ValueError`).
- `config.py`: добавить `llm_api_key: str | None = None`, `llm_model: str = "claude-..."`.
  `.env.example`: `ENGRAM_LLM_PROVIDER`, `ENGRAM_LLM_API_KEY`, `ENGRAM_LLM_MODEL`.
- Зависимость: `uv add anthropic` в `apps/api`. Кэширование промптов (`cache_control` на статичной
  system-части) — см. skill `claude-api`. Бюджеты/батчи — позже.
- **Тесты:** дефолт остаётся mock (детерминизм), поэтому путь реальной LLM не покрывается unit-тестами;
  добавить smoke-тест, помеченный skip без `ENGRAM_LLM_API_KEY`.

### 2. Умная память — дифференциаторы (моат)
**Что:** то, чего нет у Confluence/Notion. Делать после стабильного MVP, по одному.

**Точечный анализ влияния (§2.4) — приоритетный дифференциатор.**
- *Что:* change-request бьёт по конкретным пунктам (R3, R5), а не по всему документу.
- *Как:* расширить `ChangeProposal` (`llm/base.py`) до уровня пункта: добавить `item_key: str` и
  `proposed_text` (ревизия текста пункта), либо список затронутых ключей. В
  `engine.py::analyze_change` вместо перезаписи всего `content` — найти item по `key` в `target.items`,
  заменить его `text`, и вызвать `update_artifact(items=...)` (версия по-прежнему на уровне документа —
  item-level versioning см. §8). Обновить `mock.py` (выдавать per-item предложения, напр. по совпадению
  `feature`/ключевых слов) и `schemas/workflow.py::ImpactedArtifact` (добавить затронутые ключи). UI
  change-request — показать, какие пункты изменились.

**AI-подсказки связей (`suggest-links`).**
- *Что:* система предлагает тип связи между артефактами; человек принимает.
- *Как:* эндпоинт `POST /api/links/suggest` (`api/links.py`). Кандидаты — через
  `context_service` (vector-поиск ближайших), тип связи классифицирует LLM
  (refines/implements/tests/depends_on/related_to) + `rationale`/`confidence`. Принятие → существующий
  `services/link_service.py::create_link`. Mock-вариант — эвристика по парам типов.

**Авто-починка согласованности.**
- *Что:* из отчёта согласованности LLM достраивает недостающее (тест/задачу для непокрытого
  требования) одной кнопкой.
- *Как:* эндпоинт принимает `ConsistencyIssue` (напр. `requirement_without_test`), LLM генерит item
  (test_case, покрывающий Rk, с `refs=[Rk]`), добавляем в нужный документ через
  `update_artifact(items=...)`. UI — кнопка в строке отчёта.

**Дубликаты/противоречия.** Эмбеддинги ищут близкие пары пунктов, LLM судит «дубликат vs
противоречие» → новые коды в отчёт согласованности.

**Context-UI (§4.1.3).** Тонкая страница/панель поверх готового `GET /api/search/context`
(`api/search.py`, схемы `ContextQuery`/`ContextBundle`): ввод запроса → показать seed-артефакты +
расширенный срез графа. Делает головную фишку наглядной.

### 3. Глубина авторства и UX (table stakes)
- **DecisionRecord (§8.1).** *Как:* добавить `decision_record = "decision_record"` в
  `enums.py::ArtifactType` и в `STATUSES_FOR_TYPE` (напр. draft/approved/archived). **Alembic:** PG
  native enum — autogenerate НЕ ловит добавление значения; писать вручную
  `op.execute("ALTER TYPE artifact_type ADD VALUE IF NOT EXISTS 'decision_record'")` (ADD VALUE не
  работает внутри транзакции — выполнять вне транзакционного блока). Зеркально — фронтовые типы и
  `STATUSES_FOR_TYPE` (`apps/web/src/lib/types.ts` после `gen:api`), сайдбар-группировка, форма
  нового артефакта. Связи §9.2: разрешить decision_record → requirement/task в UI выбора связи.
- **Редактирование Items в UI.** Бэкенд уже умеет (`ArtifactUpdate.items`). Сделать UI add/edit/
  reorder пунктов на странице артефакта (PATCH с новым массивом `items`).
- **`extract_items_from_content` (Human-путь).** Новый метод `LLMProvider` + кнопка «Sync items» +
  эндпоинт; mock — наивная эвристика.
- Комментарии/обсуждения; граф (авто-раскладка dagre/elk, фильтры, фокус, рёбра на уровне пунктов);
  глобальный поиск в UI; diff версий.

### 4. Совместная работа и платформа
Аутентификация + пользователи, роли; несколько проектов/воркспейсов (сейчас один неявный); лента
активности; реал-тайм (WebSocket/SSE). Перед мультипользовательностью.

### 5. Интеграции — низкий приоритет
> ⚠️ MCP/«отдача памяти наружу» — **канал доставки, не моат**. Плоский retrieval (vector+RAG+готовые
> MCP-memory) закоммодитизирован. Ценность Engram — отдавать связанный/версионированный/непротиворечивый
> срез, но это свойство движка (§2), а не эндпоинта. Делать не раньше, чем ядро §2 окрепнет.

MCP-сервер поверх Engram; плагины Confluence/Jira/Notion/GitHub; импорт/экспорт (Markdown, позже DOCX).

### 6. Оркестрация и масштаб
**LangGraph** за `WorkflowEngine` (ветвление, чекпоинты, human-in-the-loop, стриминг) — *осознанно
отложено, потоки процедурные; добавлять когда нужен апрув-флоу*. Фоновые воркфлоу; графовый слой
(Neo4j) — только при росте нагрузки на запросы по связям.

### 7. Надёжность и эксплуатация
- **Тесты:** довести покрытие сервисов/правил (Этап 2); **Playwright** e2e в `apps/web` поверх
  API-e2e; фронт unit (Vitest).
- **CI:** GitHub Actions — `uv sync && uv run pytest && ruff check` + `pnpm build`; pre-commit хуки.
- **Деплой:** Docker-образы api+web, прод-compose, секреты. **git-remote** не настроен
  (`gh repo create`, аккаунт `Axx-Axvd`).
- Наблюдаемость (логи/метрики/трейсинг); прод-безопасность (валидация, rate limiting).

### 8. Техдолг и уборка
Переименовать каталог `upz-project` → `engram`; полноценный shadcn/ui (сейчас чистый Tailwind);
**версионирование на уровне пунктов** (сейчас на уровне документа — упирается в §2 точечный impact).

---

## ~~Debugging — аудит Codex (2026-05-28)~~ — устранено 2026-05-29

> Баги прохода Codex **закрыты** (проверено в коде: #1, #2, #4, #6; #3/#5 — со слов автора).
> Оставлено зачёркнутым как след, что аудит был и отработан.

1. ~~Build/lint blocker — refs во время render в `SlashMenu.tsx`.~~ → перенесено в `useEffect` (`SlashMenu.tsx:85`).
2. ~~Rich-text ломает change request (append к Tiptap JSON в `mock.py`).~~ → `content_to_text` + `text_to_doc` round-trip.
3. ~~Свежий checkout не собирается без локального generated `types.ts`.~~ → (со слов автора устранено).
4. ~~Backend принимает некорректные статусы для типов.~~ → валидатор `_status_matches_type` (`schemas/artifact.py:39`).
5. ~~Stale data в UI после change request (узкая инвалидация в `queries.ts`).~~ → (со слов автора устранено).
6. ~~Дефолт конфига расходится с docker-compose (5432 vs 5433).~~ → дефолт выровнен на 5433 (`config.py:22`).

---

## Приоритезация (impact × effort) — ориентир

| Идея | Польза | Трудозатраты | Когда |
|------|--------|--------------|-------|
| Стабилизация + тест MVP (Этап 1) | Очень высокая | Низкие | ✅ Готово |
| Правила §10.1 7/7 + тесты (Этап 2) | Высокая | Низкие | ✅ Готово |
| Реальная LLM (§1) | Очень высокая | Низкие | Как будет ключ |
| Точечный impact по пунктам (§2) | Очень высокая | Средние | Скоро — дифференциатор |
| AI-подсказки связей (§2) | Высокая | Средние | Скоро — дифференциатор |
| Авто-починка согласованности (§2) | Высокая | Средние | Скоро |
| Context-UI (§2) | Средняя | Низкие | Скоро |
| DecisionRecord (§3) | Средняя | Низкие | Скоро |
| Rich-text редактор (§0) | — | — | ✅ Реализован (banked) |
| CI + деплой (§7) | Средняя | Низкие/средние | Перед публичным показом |
| MCP / интеграции (§5) | Низкая→средняя | Средние | Низкий приоритет (коммодити) |
| Аутентификация/воркспейсы (§4) | Средняя | Высокие | Перед мультипользовательностью |
| LangGraph + HITL (§6) | Средняя | Средние | Когда нужен апрув-флоу |
| Графовый слой Neo4j (§6) | Низкая (пока) | Высокие | Только при росте нагрузки |

## Явно вне ближайшего фокуса

Полная кодогенерация/SDLC, продвинутый MLOps, обязательная UML-генерация (спека — не цель MVP).
Богатый редактор/комментарии сверх достаточного, MCP/интеграции и auth — после усиления ядра (§2).
