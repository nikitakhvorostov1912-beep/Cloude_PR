"""
BPM Architect: Массовое исправление всех BPMN-процессов.

Этот скрипт исправляет:
1. Нечитаемые lane IDs (подчёркивания -> осмысленные хэши)
2. Обрезанные названия элементов
3. Дубликаты названий элементов
4. Логику XOR gateways (путь "Нет" -> альтернативный исход)
5. Пересчитывает layout через layout engine
"""

import json
import sys
import hashlib
from pathlib import Path

# Добавляем backend в path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.bpmn.layout import BpmnLayout


def generate_lane_id(name: str) -> str:
    """Генерирует читаемый lane ID из имени."""
    h = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"lane_{h}"


def fix_proc_001(data: dict) -> dict:
    """Исправляет процесс 'Обработка заказа клиента'."""

    # 1. Исправляем lane IDs
    lane_mapping = {
        "lane_____________________": generate_lane_id("Менеджер по продажам"),
        "lane___________________________": generate_lane_id("Руководитель отдела продаж"),
        "lane______________________": generate_lane_id("Коммерческий директор"),
        "lane___________________": generate_lane_id("Заведующий складом"),
    }

    # 2. Исправляем обрезанные названия
    name_fixes = {
        "proc_001_start": "Обращение клиента (телефон/email/сайт)",
        "proc_001_gw_split_1": "Товар в наличии?",
        "proc_001_no_1": "Согласование сроков поставки с поставщиком",
        "proc_001_gw_split_2": "Скидка превышает 5%?",
        "proc_001_yes_2": "Согласование коммерческим директором",
        "proc_001_no_2": "Утверждение руководителем отдела",
        "proc_001_task_3": "Формирование коммерческого предложения",  # Было дублирование "Расчёт стоимости"
        "proc_001_gw_split_3": "Клиент принял КП?",
        "proc_001_yes_3": "Подготовка договора",  # Было дублирование "Внутреннее согласование"
        "proc_001_no_3": "Корректировка КП или закрытие заявки",
        "proc_001_task_6": "Согласование с руководителем отдела",  # Было дублирование "Внутреннее согласование"
        "proc_001_end": "Подтверждённый заказ с рассчитанной стоимостью",
    }

    # Применяем исправления
    data = _apply_lane_mapping(data, lane_mapping)
    data = _apply_name_fixes(data, name_fixes)

    # 3. Исправляем логику: путь "Нет" из gw_split_3 должен вести к endEvent (закрытие заявки)
    # Добавляем отдельный end event для отклонённых заявок
    data = _add_rejection_end_event(
        data,
        gateway_id="proc_001_gw_split_3",
        no_task_id="proc_001_no_3",
        merge_id="proc_001_gw_merge_3",
        rejection_end_id="proc_001_end_rejected",
        rejection_end_name="Заявка отклонена/отложена",
        lane_id=lane_mapping["lane_____________________"],
    )

    return data


def fix_proc_002(data: dict) -> dict:
    """Исправляет процесс 'Приёмка товара на склад'."""

    lane_mapping = {
        "lane___________________": generate_lane_id("Заведующий складом"),
        "lane________": generate_lane_id("Грузчик"),
        "lane__________": generate_lane_id("Бухгалтер"),
        "lane_____________________": generate_lane_id("Менеджер по закупкам"),
    }

    name_fixes = {
        "proc_002_start": "Прибытие транспорта с товаром от поставщика",
        "proc_002_gw_split_1": "Расхождение с ТТН?",
        "proc_002_yes_1": "Составление акта расхождения, фото фиксация",
        "proc_002_end": "Оприходованный товар с актуальными остатками",
    }

    data = _apply_lane_mapping(data, lane_mapping)
    data = _apply_name_fixes(data, name_fixes)

    return data


def fix_proc_003(data: dict) -> dict:
    """Исправляет процесс 'Отгрузка товара клиенту'."""

    lane_mapping = {
        "lane___________________": generate_lane_id("Заведующий складом"),
        "lane________": generate_lane_id("Грузчик"),
        "lane_____________________": generate_lane_id("Менеджер по продажам"),
        "lane__________": generate_lane_id("Бухгалтер"),
        "lane_________": generate_lane_id("Водитель"),
    }

    name_fixes = {
        "proc_003_start": "Получение заявки на отгрузку от менеджера",
        "proc_003_gw_split_1": "Все позиции в наличии?",
        "proc_003_no_1": "Уведомление менеджера по продажам о нехватке",
        "proc_003_task_2": "Сборка и комплектация заказа",  # Было дублирование "Комплектация заказа"
        "proc_003_gw_split_2": "Заказ собран верно?",
        "proc_003_task_4": "Оформление отгрузочных документов",  # Было дублирование "Оформление документов"
        "proc_003_end": "Отгруженный товар с оформленными документами",
    }

    data = _apply_lane_mapping(data, lane_mapping)
    data = _apply_name_fixes(data, name_fixes)

    # Исправляем логику: если "Нет" в gw_split_1 (не всё в наличии) -> уведомление -> ждём
    # Добавляем альтернативный конец для случая, когда товара нет
    data = _add_rejection_end_event(
        data,
        gateway_id="proc_003_gw_split_1",
        no_task_id="proc_003_no_1",
        merge_id="proc_003_gw_merge_1",
        rejection_end_id="proc_003_end_shortage",
        rejection_end_name="Отгрузка отложена (нехватка товара)",
        lane_id=lane_mapping["lane___________________"],
    )

    return data


def fix_proc_004(data: dict) -> dict:
    """Исправляет процесс 'Согласование скидки'."""

    lane_mapping = {
        "lane_____________________": generate_lane_id("Менеджер по продажам"),
        "lane___________________________": generate_lane_id("Руководитель отдела продаж"),
        "lane______________________": generate_lane_id("Коммерческий директор"),
    }

    name_fixes = {
        "proc_004_start": "Запрос клиента на скидку более 5%",
        "proc_004_gw_split_1": "Руководитель одобряет?",
        "proc_004_yes_1": "Передача коммерческому директору",
        "proc_004_no_1": "Отклонение заявки, уведомление менеджера",
        "proc_004_gw_split_2": "Коммерческий директор одобряет?",
        "proc_004_yes_2": "Уведомление менеджера, применение скидки",
        "proc_004_no_2": "Предложение альтернативных условий",
        "proc_004_end": "Утверждённая или отклонённая скидка",
    }

    data = _apply_lane_mapping(data, lane_mapping)
    data = _apply_name_fixes(data, name_fixes)

    # Исправляем логику: если руководитель отклоняет (gw_split_1 -> no_1),
    # процесс должен завершиться отказом, а не продолжаться к коммерческому директору
    data = _add_rejection_end_event(
        data,
        gateway_id="proc_004_gw_split_1",
        no_task_id="proc_004_no_1",
        merge_id="proc_004_gw_merge_1",
        rejection_end_id="proc_004_end_rejected",
        rejection_end_name="Скидка отклонена руководителем",
        lane_id=lane_mapping["lane_____________________"],
    )

    return data


def fix_proc_purchase(data: dict) -> dict:
    """Исправляет процесс 'Закупка товаров и материалов'."""
    # Lane IDs уже нормальные (lane_3fc1c4ff и т.д.)

    name_fixes = {
        "proc_purchase_gw_split_1": "Заявка обоснована?",
        "proc_purchase_gw_split_2": "Бюджет достаточен?",
        "proc_purchase_gw_split_3": "Сумма > 500 тыс. руб.?",
        "proc_purchase_gw_split_4": "Товар соответствует заказу?",
    }

    data = _apply_name_fixes(data, name_fixes)

    # Исправляем логику: если заявка не обоснована -> возврат инициатору -> END
    data = _add_rejection_end_event(
        data,
        gateway_id="proc_purchase_gw_split_1",
        no_task_id="proc_purchase_no_1",
        merge_id="proc_purchase_gw_merge_1",
        rejection_end_id="proc_purchase_end_rejected",
        rejection_end_name="Заявка отклонена (необоснована)",
        lane_id="lane_3fc1c4ff",
    )

    return data


# -----------------------------------------------------------------------
# Вспомогательные функции
# -----------------------------------------------------------------------

def _apply_lane_mapping(data: dict, mapping: dict) -> dict:
    """Заменяет lane IDs во всех элементах, participants и layout."""

    # Элементы
    for elem in data.get("elements", []):
        old_lane = elem.get("lane", "")
        if old_lane in mapping:
            elem["lane"] = mapping[old_lane]

    # Participants
    new_participants = []
    for part in data.get("participants", []):
        old_id = part.get("id", "")
        old_lane_id = part.get("lane_id", "")

        if old_id in mapping:
            part["id"] = mapping[old_id]
        if old_lane_id in mapping:
            part["lane_id"] = mapping[old_lane_id]

        new_participants.append(part)
    data["participants"] = new_participants

    # Layout lanes
    if "layout" in data and "lanes" in data["layout"]:
        new_lanes = {}
        for old_id, pos in data["layout"]["lanes"].items():
            new_id = mapping.get(old_id, old_id)
            new_lanes[new_id] = pos
        data["layout"]["lanes"] = new_lanes

    # Layout participants
    if "layout" in data and "participants" in data["layout"]:
        new_parts = {}
        for old_id, pos in data["layout"]["participants"].items():
            new_id = mapping.get(old_id, old_id)
            new_parts[new_id] = pos
        data["layout"]["participants"] = new_parts

    return data


def _apply_name_fixes(data: dict, fixes: dict) -> dict:
    """Применяет исправления названий элементов."""
    for elem in data.get("elements", []):
        elem_id = elem.get("id", "")
        if elem_id in fixes:
            elem["name"] = fixes[elem_id]

    # Также исправляем conditions в flows, если gateway name поменялся
    for flow in data.get("flows", []):
        source = flow.get("source", "")
        if source in fixes and "condition" in flow:
            # Обновляем condition чтобы соответствовал новому имени gateway
            flow["condition"] = fixes[source]

    return data


def _add_rejection_end_event(
    data: dict,
    gateway_id: str,
    no_task_id: str,
    merge_id: str,
    rejection_end_id: str,
    rejection_end_name: str,
    lane_id: str,
) -> dict:
    """
    Изменяет логику: путь "Нет" из gateway ведёт к отдельному endEvent
    вместо слияния обратно в merge gateway.

    Было: gw_split -> no_task -> gw_merge -> (продолжение)
    Стало: gw_split -> no_task -> end_rejected

    Идемпотентно: если rejection_end_id уже существует, не добавляет дубликат.
    """

    # Проверяем идемпотентность
    existing_ids = {e["id"] for e in data.get("elements", [])}
    if rejection_end_id in existing_ids:
        # Уже добавлен ранее, пропускаем
        return data

    # Добавляем новый endEvent
    data["elements"].append({
        "id": rejection_end_id,
        "type": "endEvent",
        "name": rejection_end_name,
        "lane": lane_id,
    })

    # Находим и заменяем flow: no_task -> merge на no_task -> rejection_end
    new_flows = []
    for flow in data["flows"]:
        if flow.get("source") == no_task_id and flow.get("target") == merge_id:
            # Заменяем этот flow на: no_task -> rejection_end
            flow["target"] = rejection_end_id
            flow["id"] = f"{data['process_id']}_flow_{no_task_id}_to_{rejection_end_id}"
        new_flows.append(flow)
    data["flows"] = new_flows

    return data


def recalculate_layout(data: dict) -> dict:
    """Пересчитывает layout через layout engine."""
    layout_engine = BpmnLayout()
    new_layout = layout_engine.calculate_layout(data)
    data["layout"] = new_layout
    return data


def main():
    base_dir = Path(__file__).resolve().parent.parent / "data" / "projects"

    process_files = {
        "proc_001": {
            "path": base_dir / "ecb4ac19b44f49bb9da0ab72d817251a" / "processes" / "proc_001_bpmn.json",
            "fix_fn": fix_proc_001,
        },
        "proc_002": {
            "path": base_dir / "ecb4ac19b44f49bb9da0ab72d817251a" / "processes" / "proc_002_bpmn.json",
            "fix_fn": fix_proc_002,
        },
        "proc_003": {
            "path": base_dir / "ecb4ac19b44f49bb9da0ab72d817251a" / "processes" / "proc_003_bpmn.json",
            "fix_fn": fix_proc_003,
        },
        "proc_004": {
            "path": base_dir / "ecb4ac19b44f49bb9da0ab72d817251a" / "processes" / "proc_004_bpmn.json",
            "fix_fn": fix_proc_004,
        },
        "proc_purchase": {
            "path": base_dir / "6fa5881144a34dcf9ea274c5ca448e07" / "processes" / "proc_purchase_bpmn.json",
            "fix_fn": fix_proc_purchase,
        },
    }

    results = []

    for proc_id, info in process_files.items():
        filepath = info["path"]
        fix_fn = info["fix_fn"]

        print(f"\n{'='*60}")
        print(f"ИСПРАВЛЕНИЕ: {proc_id}")
        print(f"{'='*60}")

        # Читаем
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Дедупликация элементов (на случай повторного запуска)
        seen_ids = set()
        deduped_elements = []
        for elem in data.get("elements", []):
            eid = elem.get("id", "")
            if eid not in seen_ids:
                seen_ids.add(eid)
                deduped_elements.append(elem)
        data["elements"] = deduped_elements

        print(f"  Элементов: {len(data.get('elements', []))}")
        print(f"  Потоков: {len(data.get('flows', []))}")

        # Исправляем содержание
        data = fix_fn(data)

        # Пересчитываем layout
        data = recalculate_layout(data)

        # Валидируем: проверяем что все элементы внутри своих lanes
        validate_layout(data, proc_id)

        # Сохраняем
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  СОХРАНЕНО: {filepath}")
        results.append((proc_id, "OK"))

    print(f"\n{'='*60}")
    print("РЕЗУЛЬТАТЫ:")
    print(f"{'='*60}")
    for proc_id, status in results:
        print(f"  {proc_id}: {status}")


def validate_layout(data: dict, proc_id: str):
    """Валидирует что все элементы внутри своих lanes."""
    layout = data.get("layout", {})
    element_positions = layout.get("elements", {})
    lane_positions = layout.get("lanes", {})

    if not lane_positions:
        print(f"  [WARN] Нет lane positions для {proc_id}")
        return

    errors = 0
    for elem in data.get("elements", []):
        elem_id = elem.get("id", "")
        elem_lane = elem.get("lane", "")

        elem_pos = element_positions.get(elem_id)
        lane_pos = lane_positions.get(elem_lane)

        if not elem_pos or not lane_pos:
            continue

        elem_top = elem_pos["y"]
        elem_bottom = elem_pos["y"] + elem_pos["height"]
        lane_top = lane_pos["y"]
        lane_bottom = lane_pos["y"] + lane_pos["height"]

        if elem_top < lane_top - 5 or elem_bottom > lane_bottom + 5:
            print(f"  [ERROR] {elem_id} (y={elem_top:.0f}-{elem_bottom:.0f}) "
                  f"выходит за lane {elem_lane} (y={lane_top:.0f}-{lane_bottom:.0f})")
            errors += 1

    if errors == 0:
        print(f"  [OK] Все элементы внутри своих lanes")
    else:
        print(f"  [WARN] {errors} элементов вне своих lanes")


if __name__ == "__main__":
    main()
