"""Скрипт создания сложного бизнес-процесса для тестирования диаграмм."""

import json
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pid = "6fa5881144a34dcf9ea274c5ca448e07"
proj_dir = Path("data/projects") / pid

# =====================================================================
# COMPLEX PROCESS: Закупка товаров и материалов
# 7 ролей, 13 шагов, 4 решения, 5 проблемных зон
# =====================================================================

processes_data = {
    "source_transcripts": ["interview_procurement_01.txt"],
    "company": 'ООО "Промышленные решения"',
    "extracted_at": "2026-03-02T10:00:00",
    "processes": [
        {
            "id": "proc_purchase",
            "name": "Закупка товаров и материалов",
            "description": (
                "Полный цикл закупки от формирования потребности до оприходования на склад. "
                "Процесс включает согласование заявок, выбор поставщика через тендер, "
                "контрактование, контроль поставки и приёмку товара с проверкой качества. "
                "Задействованы подразделения: производство, закупки, финансы, склад и юридический отдел."
            ),
            "trigger": "Формирование потребности в материалах",
            "result": "Товар оприходован на склад",
            "department": "Отдел закупок",
            "status": "approved",
            "participants": [
                {"role": "Инициатор заявки", "department": "Производство"},
                {"role": "Руководитель подразделения", "department": "Производство"},
                {"role": "Менеджер по закупкам", "department": "Отдел закупок"},
                {"role": "Руководитель отдела закупок", "department": "Отдел закупок"},
                {"role": "Финансовый контролёр", "department": "Финансовый отдел"},
                {"role": "Юрист", "department": "Юридический отдел"},
                {"role": "Кладовщик", "department": "Склад"},
            ],
            "steps": [
                {
                    "order": 1, "name": "Формирование заявки на закупку",
                    "description": "Инициатор создаёт заявку с указанием номенклатуры, количества, сроков и технических требований.",
                    "performer": "Инициатор заявки", "actor": "Инициатор заявки",
                    "inputs": ["Потребность производства"], "outputs": ["Заявка на закупку"],
                    "systems": ["1С:ERP"], "system": "1С:ERP", "duration_estimate": "30 мин"
                },
                {
                    "order": 2, "name": "Согласование руководителем",
                    "description": "Руководитель проверяет обоснованность заявки и соответствие бюджету подразделения.",
                    "performer": "Руководитель подразделения", "actor": "Руководитель подразделения",
                    "inputs": ["Заявка на закупку"], "outputs": ["Согласованная заявка"],
                    "systems": ["1С:ERP"], "system": "1С:ERP", "duration_estimate": "1-2 часа"
                },
                {
                    "order": 3, "name": "Проверка бюджета",
                    "description": "Финансовый контролёр проверяет наличие средств и соответствие финансовому плану.",
                    "performer": "Финансовый контролёр", "actor": "Финансовый контролёр",
                    "inputs": ["Согласованная заявка"], "outputs": ["Финансовое подтверждение"],
                    "systems": ["1С:ERP"], "system": "1С:ERP", "duration_estimate": "2-4 часа"
                },
                {
                    "order": 4, "name": "Поиск и выбор поставщиков",
                    "description": "Запрос коммерческих предложений, сравнительный анализ цен и условий.",
                    "performer": "Менеджер по закупкам", "actor": "Менеджер по закупкам",
                    "inputs": ["Утверждённая заявка"], "outputs": ["Сравнительная таблица"],
                    "systems": ["1С:ERP", "Email"], "system": "1С:ERP, Email", "duration_estimate": "2-5 дней"
                },
                {
                    "order": 5, "name": "Проведение тендера",
                    "description": "Тендерная процедура с привлечением от 3 поставщиков. Оценка: цена, качество, сроки.",
                    "performer": "Руководитель отдела закупок", "actor": "Руководитель отдела закупок",
                    "inputs": ["КП поставщиков"], "outputs": ["Протокол тендера"],
                    "systems": ["Портал закупок"], "system": "Портал закупок", "duration_estimate": "3-7 дней"
                },
                {
                    "order": 6, "name": "Согласование договора",
                    "description": "Юрист проверяет условия: законодательство, ответственность, гарантии, расчёты.",
                    "performer": "Юрист", "actor": "Юрист",
                    "inputs": ["Проект договора"], "outputs": ["Согласованный договор"],
                    "systems": ["СЭД"], "system": "СЭД", "duration_estimate": "1-3 дня"
                },
                {
                    "order": 7, "name": "Подписание договора",
                    "description": "Подписание договора с поставщиком, регистрация в реестре.",
                    "performer": "Руководитель отдела закупок", "actor": "Руководитель отдела закупок",
                    "inputs": ["Согласованный договор"], "outputs": ["Подписанный договор"],
                    "systems": ["1С:ERP"], "system": "1С:ERP", "duration_estimate": "1 день"
                },
                {
                    "order": 8, "name": "Формирование заказа поставщику",
                    "description": "Создание заказа с номенклатурой, количеством, ценами и сроками.",
                    "performer": "Менеджер по закупкам", "actor": "Менеджер по закупкам",
                    "inputs": ["Подписанный договор"], "outputs": ["Заказ поставщику"],
                    "systems": ["1С:ERP"], "system": "1С:ERP", "duration_estimate": "1 час"
                },
                {
                    "order": 9, "name": "Контроль сроков поставки",
                    "description": "Отслеживание статуса, взаимодействие с поставщиком по логистике.",
                    "performer": "Менеджер по закупкам", "actor": "Менеджер по закупкам",
                    "inputs": ["Заказ поставщику"], "outputs": ["Уведомление о поставке"],
                    "systems": ["1С:ERP"], "system": "1С:ERP", "duration_estimate": "по графику"
                },
                {
                    "order": 10, "name": "Приёмка товара на складе",
                    "description": "Проверка количества, внешнего вида, соответствие документам.",
                    "performer": "Кладовщик", "actor": "Кладовщик",
                    "inputs": ["Товар", "Накладная"], "outputs": ["Акт приёмки"],
                    "systems": ["1С:ERP"], "system": "1С:ERP", "duration_estimate": "2-4 часа"
                },
                {
                    "order": 11, "name": "Контроль качества",
                    "description": "Проверка соответствия техническим требованиям из заявки.",
                    "performer": "Инициатор заявки", "actor": "Инициатор заявки",
                    "inputs": ["Товар", "Спецификация"], "outputs": ["Заключение о качестве"],
                    "systems": [], "system": "", "duration_estimate": "1-2 дня"
                },
                {
                    "order": 12, "name": "Оприходование на склад",
                    "description": "Оформление прихода, присвоение мест хранения, обновление остатков.",
                    "performer": "Кладовщик", "actor": "Кладовщик",
                    "inputs": ["Акт приёмки"], "outputs": ["Складская карточка"],
                    "systems": ["1С:ERP"], "system": "1С:ERP", "duration_estimate": "30 мин"
                },
                {
                    "order": 13, "name": "Обработка оплаты",
                    "description": "Формирование платёжного поручения на основании акта приёмки и счёта-фактуры.",
                    "performer": "Финансовый контролёр", "actor": "Финансовый контролёр",
                    "inputs": ["Счёт-фактура"], "outputs": ["Платёжное поручение"],
                    "systems": ["1С:ERP", "Клиент-банк"], "system": "1С:ERP", "duration_estimate": "1-2 дня"
                },
            ],
            "decisions": [
                {
                    "name": "Согласование",
                    "condition": "Заявка обоснована?",
                    "after_step_id": "step_2",
                    "question": "Заявка обоснована?",
                    "yes_branch": "Проверка бюджета",
                    "no_branch": "Возврат инициатору",
                    "options": []
                },
                {
                    "name": "Проверка бюджета",
                    "condition": "Бюджет достаточен?",
                    "after_step_id": "step_3",
                    "question": "Достаточно средств?",
                    "yes_branch": "Поиск поставщиков",
                    "no_branch": "Запрос доп. финансирования",
                    "options": []
                },
                {
                    "name": "Необходимость тендера",
                    "condition": "Сумма > 500 тыс?",
                    "after_step_id": "step_4",
                    "question": "Сумма > 500 000 руб?",
                    "yes_branch": "Тендер",
                    "no_branch": "Прямая закупка",
                    "options": []
                },
                {
                    "name": "Проверка качества",
                    "condition": "Товар соответствует?",
                    "after_step_id": "step_11",
                    "question": "Товар соответствует?",
                    "yes_branch": "Оприходование",
                    "no_branch": "Рекламация",
                    "options": []
                },
            ],
            "pain_points": [
                {
                    "id": "pp1",
                    "description": "Длительные сроки согласования заявок — до 5 дней из-за ручного документооборота",
                    "severity": "high", "category": "Скорость",
                },
                {
                    "id": "pp2",
                    "description": "Отсутствие единого реестра поставщиков с рейтингами и историей",
                    "severity": "medium", "category": "Данные",
                },
                {
                    "id": "pp3",
                    "description": "Ручной контроль сроков поставки — нет автоматических уведомлений",
                    "severity": "high", "category": "Автоматизация",
                },
                {
                    "id": "pp4",
                    "description": "Дублирование ввода данных в Excel, 1С и СЭД — до 15% ошибок",
                    "severity": "critical", "category": "Интеграция",
                },
                {
                    "id": "pp5",
                    "description": "Нет прозрачности статуса закупки для инициатора заявки",
                    "severity": "medium", "category": "Прозрачность",
                },
            ],
            "integrations": ["1С:ERP", "СЭД", "Email", "Портал закупок", "Клиент-банк"],
            "metrics": {
                "frequency": "50-80 заявок/мес",
                "duration": "10-25 рабочих дней",
                "participants_count": 7,
            },
        }
    ],
}

# Save processes
(proj_dir / "processes" / "processes.json").write_text(
    json.dumps(processes_data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("Saved processes.json")
print(f"  Steps: {len(processes_data['processes'][0]['steps'])}")
print(f"  Decisions: {len(processes_data['processes'][0]['decisions'])}")
print(f"  Pain points: {len(processes_data['processes'][0]['pain_points'])}")
print(f"  Participants: {len(processes_data['processes'][0]['participants'])}")

# =====================================================================
# Generate BPMN JSON, XML and SVG using project pipeline
# =====================================================================

from app.bpmn.process_to_bpmn import ProcessToBpmnConverter  # noqa: E402
from app.bpmn.renderer import BPMNRenderer  # noqa: E402
from app.bpmn.json_to_bpmn import BpmnConverter  # noqa: E402
from app.bpmn.layout import BpmnLayout  # noqa: E402

process = processes_data["processes"][0]

# 1. Convert process to BPMN JSON
converter = ProcessToBpmnConverter()
bpmn_json = converter.convert(process)

# Save BPMN JSON
bpmn_json_path = proj_dir / "processes" / "proc_purchase_bpmn.json"
bpmn_json_path.write_text(json.dumps(bpmn_json, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nBPMN JSON saved: {len(bpmn_json.get('elements', []))} elements, {len(bpmn_json.get('flows', []))} flows")

# 2. Calculate layout
layout_engine = BpmnLayout()
layout = layout_engine.calculate_layout(bpmn_json)
bpmn_json_with_layout = {**bpmn_json, "layout": layout}
print(f"Layout calculated: {len(layout.get('elements', {}))} positioned elements")

# 3. Convert to BPMN XML
bpmn_converter = BpmnConverter()
bpmn_xml = bpmn_converter.convert(bpmn_json_with_layout)
bpmn_xml_path = proj_dir / "bpmn" / "proc_purchase.bpmn"
bpmn_xml_path.write_text(bpmn_xml, encoding="utf-8")
print(f"BPMN XML saved: {len(bpmn_xml)} bytes")

# 4. Render SVG
renderer = BPMNRenderer()
svg = renderer.render_svg(bpmn_xml)
svg_path = proj_dir / "bpmn" / "proc_purchase.svg"
svg_path.write_text(svg, encoding="utf-8")
print(f"SVG saved: {len(svg)} bytes")

# Count elements in generated output
print("\n=== Summary ===")
print(f"Project: {pid}")
print(f"Process: {process['name']}")
print(f"  Roles (lanes): {len(set(p['role'] for p in process['participants']))}")
print(f"  Steps: {len(process['steps'])}")
print(f"  Decisions: {len(process['decisions'])}")
print(f"  BPMN Elements: {len(bpmn_json.get('elements', []))}")
print(f"  BPMN Flows: {len(bpmn_json.get('flows', []))}")
