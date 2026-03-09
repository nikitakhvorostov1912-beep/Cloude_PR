"""LLM prompts for business process extraction and BPMN generation."""

SYSTEM_PROMPT_ANALYST = """Ты — опытный бизнес-аналитик, специализирующийся на предпроектном обследовании для внедрения 1С.
Твоя задача — анализировать расшифровки интервью с сотрудниками и извлекать бизнес-процессы.

Правила:
1. Извлекай ТОЛЬКО то, что явно описано в интервью — не додумывай
2. Используй терминологию респондентов
3. Определяй роли участников процессов
4. Выявляй болевые точки и проблемы
5. Отмечай интеграции с другими системами и отделами
6. Формируй структуру в формате JSON"""

EXTRACT_PROCESSES_PROMPT = """Проанализируй расшифровку интервью и извлеки бизнес-процессы.

## Расшифровка интервью:
{transcript}

## Задача:
Извлеки ВСЕ бизнес-процессы, упомянутые в интервью. Для каждого процесса определи:
- Название процесса
- Триггер (что запускает процесс)
- Шаги процесса (последовательность действий)
- Участников (роли)
- Результат (чем завершается)
- Документы (входящие и исходящие)
- Точки принятия решений (развилки)
- Исключения и нештатные ситуации
- Проблемы и болевые точки

## Формат ответа (строго JSON):
{{
  "department": "Название отдела",
  "respondent": "Должность респондента",
  "processes": [
    {{
      "id": "proc_1",
      "name": "Название процесса",
      "type": "as_is",
      "trigger": "Что запускает процесс",
      "result": "Конечный результат",
      "frequency": "Периодичность (ежедневно/еженедельно/по событию)",
      "participants": [
        {{
          "role": "Название роли",
          "department": "Отдел"
        }}
      ],
      "steps": [
        {{
          "id": "step_1",
          "name": "Название шага",
          "description": "Описание действия",
          "performer": "Роль исполнителя",
          "type": "task",
          "documents_in": ["Входящий документ"],
          "documents_out": ["Исходящий документ"]
        }}
      ],
      "decisions": [
        {{
          "id": "dec_1",
          "question": "Вопрос решения",
          "after_step": "step_X",
          "options": [
            {{
              "condition": "Условие",
              "next_step": "step_Y"
            }}
          ]
        }}
      ],
      "exceptions": [
        {{
          "description": "Описание исключения",
          "handling": "Как обрабатывается"
        }}
      ],
      "pain_points": [
        {{
          "description": "Описание проблемы",
          "impact": "Влияние на работу",
          "severity": "high/medium/low"
        }}
      ],
      "integrations": [
        {{
          "system": "Название системы",
          "type": "Тип интеграции",
          "description": "Описание"
        }}
      ]
    }}
  ],
  "general_issues": [
    {{
      "description": "Общая проблема отдела",
      "category": "Категория"
    }}
  ],
  "automation_requests": [
    {{
      "description": "Что хотят автоматизировать",
      "priority": "high/medium/low"
    }}
  ]
}}"""

GENERATE_TO_BE_PROMPT = """На основе AS IS процессов предложи оптимизированные TO BE процессы.

## Текущие процессы (AS IS):
{processes_json}

## Задача:
Для каждого AS IS процесса предложи оптимизированный TO BE вариант:
1. Устрани выявленные болевые точки
2. Автоматизируй ручные операции где возможно
3. Убери дублирование данных
4. Оптимизируй документооборот
5. Учитывай возможности 1С:ERP

## Формат ответа (строго JSON):
{{
  "to_be_processes": [
    {{
      "id": "proc_1_to_be",
      "based_on": "proc_1",
      "name": "Название оптимизированного процесса",
      "type": "to_be",
      "changes_summary": "Краткое описание изменений",
      "trigger": "Триггер",
      "result": "Результат",
      "participants": [...],
      "steps": [...],
      "decisions": [...],
      "improvements": [
        {{
          "description": "Что улучшено",
          "benefit": "Какой эффект"
        }}
      ],
      "automation_points": [
        {{
          "description": "Что автоматизировано",
          "tool": "1С:ERP / Интеграция / Отчёт"
        }}
      ]
    }}
  ],
  "implementation_priorities": [
    {{
      "process_id": "proc_1_to_be",
      "priority": 1,
      "reason": "Почему первым"
    }}
  ]
}}"""

GENERATE_BPMN_JSON_PROMPT = """Преобразуй бизнес-процесс в BPMN 2.0 формат (JSON).

## Процесс:
{process_json}

## Уровень детализации: {detail_level}

## Задача:
Создай BPMN-представление процесса в JSON формате. Используй стандартные элементы BPMN 2.0.

## Формат ответа (строго JSON):
{{
  "process_id": "id процесса",
  "process_name": "Название",
  "pools": [
    {{
      "id": "pool_1",
      "name": "Название пула (организация/отдел)",
      "lanes": [
        {{
          "id": "lane_1",
          "name": "Роль/Должность",
          "elements": ["elem_id_1", "elem_id_2"]
        }}
      ]
    }}
  ],
  "elements": [
    {{
      "id": "start_1",
      "type": "startEvent",
      "name": "Начало",
      "outgoing": ["flow_1"]
    }},
    {{
      "id": "task_1",
      "type": "userTask",
      "name": "Название задачи",
      "incoming": ["flow_1"],
      "outgoing": ["flow_2"]
    }},
    {{
      "id": "gateway_1",
      "type": "exclusiveGateway",
      "name": "Условие?",
      "incoming": ["flow_2"],
      "outgoing": ["flow_3", "flow_4"]
    }},
    {{
      "id": "end_1",
      "type": "endEvent",
      "name": "Конец",
      "incoming": ["flow_5"]
    }}
  ],
  "flows": [
    {{
      "id": "flow_1",
      "source": "start_1",
      "target": "task_1",
      "name": ""
    }},
    {{
      "id": "flow_3",
      "source": "gateway_1",
      "target": "task_2",
      "name": "Да",
      "condition": "Условие выполнено"
    }}
  ]
}}

## Правила:
1. Каждый процесс начинается с startEvent и заканчивается endEvent
2. Используй типы элементов: startEvent, endEvent, userTask, serviceTask, scriptTask, manualTask, exclusiveGateway, parallelGateway, eventBasedGateway, intermediateCatchEvent, intermediateThrowEvent, subProcess
3. Для {detail_level} уровня:
   - "high_level": 5-10 основных шагов, без подпроцессов
   - "detailed": все шаги, подпроцессы, исключения, таймеры
4. Каждый элемент должен иметь входящие и исходящие потоки (кроме start/end)
5. Шлюзы должны иметь условия на исходящих потоках
6. Используй lanes для разделения по ролям"""

GENERATE_PROCESS_CARD_PROMPT = """Создай карточку бизнес-процесса для документации.

## Процесс:
{process_json}

## Формат ответа (строго JSON):
{{
  "process_card": {{
    "name": "Название процесса",
    "id": "Идентификатор",
    "owner": "Владелец процесса (роль/должность)",
    "department": "Отдел",
    "type": "as_is / to_be",
    "purpose": "Цель процесса",
    "trigger": "Входное событие/триггер",
    "result": "Выходной результат",
    "frequency": "Периодичность выполнения",
    "avg_duration": "Среднее время выполнения",
    "participants": [
      {{
        "role": "Роль",
        "responsibility": "Ответственность в процессе"
      }}
    ],
    "inputs": [
      {{
        "name": "Название входа",
        "source": "Откуда поступает",
        "format": "Формат данных/документа"
      }}
    ],
    "outputs": [
      {{
        "name": "Название выхода",
        "target": "Куда направляется",
        "format": "Формат данных/документа"
      }}
    ],
    "kpi": [
      {{
        "name": "Название показателя",
        "target_value": "Целевое значение",
        "measurement": "Способ измерения"
      }}
    ],
    "risks": [
      {{
        "description": "Описание риска",
        "probability": "high/medium/low",
        "mitigation": "Способ снижения"
      }}
    ],
    "related_processes": ["Связанные процессы"],
    "regulatory_requirements": ["Нормативные требования"],
    "it_systems": ["Используемые ИТ-системы"],
    "description": "Подробное текстовое описание процесса (2-3 абзаца)"
  }}
}}"""
