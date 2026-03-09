#!/usr/bin/env python3
"""
BPM Architect — Комплексный скрипт исправления ВСЕХ дефектов.
1. Добавляет Error Events во все процессы
2. Добавляет Timer Events где есть ожидание/дедлайны
3. Добавляет Message Flow между связанными процессами
4. Декомпозирует proc_purchase (32 элемента -> Sub-Process)
5. Создаёт L0 карту процессов
"""

import json
import os
import copy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT1_DIR = os.path.join(BASE_DIR, "data", "projects", "ecb4ac19b44f49bb9da0ab72d817251a", "processes")
PROJECT2_DIR = os.path.join(BASE_DIR, "data", "projects", "6fa5881144a34dcf9ea274c5ca448e07", "processes")


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Сохранено: {path}")


def add_error_events_proc001(data):
    """proc_001: Ошибки при проверке остатков, при расчёте стоимости"""
    print("\n=== proc_001: Добавляю Error Events ===")

    # Error Event: Ошибка данных при проверке остатков (после task_2)
    error_elem = {
        "id": "proc_001_error_stock",
        "type": "intermediateThrowEvent",
        "name": "Ошибка: данные остатков расходятся (Excel/1С)",
        "eventDefinition": "errorEventDefinition",
        "lane": "lane_8a6c85a1"
    }
    data["elements"].append(error_elem)

    # Error End Event: Системная ошибка
    error_end = {
        "id": "proc_001_end_error",
        "type": "endEvent",
        "name": "Ошибка обработки заказа",
        "eventDefinition": "errorEventDefinition",
        "lane": "lane_8a6c85a1"
    }
    data["elements"].append(error_end)

    # Flow: from error to error end
    data["flows"].append({
        "id": "proc_001_flow_error_stock_to_end_error",
        "source": "proc_001_error_stock",
        "target": "proc_001_end_error"
    })

    # Boundary error on task_2 (проверка остатков)
    # We add a flow from task_2 area to the error event
    # In BPMN JSON, we model it as a conditional branch
    # Add gateway after task_2 for error check
    # Actually, let's add it as a boundary-like flow from the service task
    data["flows"].append({
        "id": "proc_001_flow_task2_to_error",
        "source": "proc_001_task_2",
        "target": "proc_001_error_stock",
        "name": "Ошибка данных"
    })

    # Layout for new elements
    data["layout"]["elements"]["proc_001_error_stock"] = {
        "x": 1080.0, "y": 430.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["elements"]["proc_001_end_error"] = {
        "x": 1225.0, "y": 430.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["flows"]["proc_001_flow_error_stock_to_end_error"] = [
        {"x": 1110.0, "y": 445.0}, {"x": 1225.0, "y": 445.0}
    ]
    data["layout"]["flows"]["proc_001_flow_task2_to_error"] = [
        {"x": 1140.0, "y": 350.0}, {"x": 1140.0, "y": 430.0},
        {"x": 1095.0, "y": 430.0}, {"x": 1095.0, "y": 430.0}
    ]

    print("  + Error Event: Ошибка данных остатков (после проверки остатков)")
    print("  + Error End Event: Ошибка обработки заказа")
    return data


def add_timer_events_proc001(data):
    """proc_001: Timer на ожидание ответа клиента (1-48ч)"""
    print("\n=== proc_001: Добавляю Timer Events ===")

    timer_elem = {
        "id": "proc_001_timer_client",
        "type": "intermediateCatchEvent",
        "name": "Ожидание ответа клиента (до 48ч)",
        "eventDefinition": "timerEventDefinition",
        "lane": "lane_8a6c85a1"
    }
    data["elements"].append(timer_elem)

    # Insert timer between task_4 (Отправка КП) and task_5 (Получение подтверждения)
    # Remove old flow task_4 -> task_5
    data["flows"] = [f for f in data["flows"]
                     if f["id"] != "proc_001_flow_proc_001_task_4_to_proc_001_task_5"]

    # Add task_4 -> timer -> task_5
    data["flows"].append({
        "id": "proc_001_flow_task4_to_timer",
        "source": "proc_001_task_4",
        "target": "proc_001_timer_client"
    })
    data["flows"].append({
        "id": "proc_001_flow_timer_to_task5",
        "source": "proc_001_timer_client",
        "target": "proc_001_task_5"
    })

    # Layout - between task_4 and task_5
    data["layout"]["elements"]["proc_001_timer_client"] = {
        "x": 2785.0, "y": 305.0, "width": 30.0, "height": 30.0
    }
    # Remove old flow layout
    data["layout"]["flows"].pop("proc_001_flow_proc_001_task_4_to_proc_001_task_5", None)
    data["layout"]["flows"]["proc_001_flow_task4_to_timer"] = [
        {"x": 2800.0, "y": 320.0}, {"x": 2785.0, "y": 320.0}
    ]
    data["layout"]["flows"]["proc_001_flow_timer_to_task5"] = [
        {"x": 2815.0, "y": 320.0}, {"x": 2880.0, "y": 320.0}
    ]

    print("  + Timer Event: Ожидание ответа клиента (до 48ч)")
    return data


def add_error_events_proc002(data):
    """proc_002: Error при расхождении с ТТН"""
    print("\n=== proc_002: Добавляю Error Events ===")

    error_end = {
        "id": "proc_002_end_error",
        "type": "endEvent",
        "name": "Критическое расхождение (брак/недостача)",
        "eventDefinition": "errorEventDefinition",
        "lane": "lane_1b0d3d71"
    }
    data["elements"].append(error_end)

    # After yes_1 (акт расхождения) — если критично, то Error End
    data["flows"].append({
        "id": "proc_002_flow_yes1_to_error",
        "source": "proc_002_yes_1",
        "target": "proc_002_end_error",
        "name": "Критическое"
    })

    data["layout"]["elements"]["proc_002_end_error"] = {
        "x": 925.0, "y": 170.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["flows"]["proc_002_flow_yes1_to_error"] = [
        {"x": 740.0, "y": 220.0}, {"x": 740.0, "y": 185.0}, {"x": 925.0, "y": 185.0}
    ]

    print("  + Error End Event: Критическое расхождение (брак/недостача)")
    return data


def add_timer_events_proc002(data):
    """proc_002: Timer - задержка проведения в 1С (1-2 дня)"""
    print("\n=== proc_002: Добавляю Timer Events ===")

    timer = {
        "id": "proc_002_timer_1c",
        "type": "intermediateCatchEvent",
        "name": "Ожидание проведения в 1С (1-2 дня)",
        "eventDefinition": "timerEventDefinition",
        "lane": "lane_1b0d3d71"
    }
    data["elements"].append(timer)

    # Insert between task_5 and task_6
    data["flows"] = [f for f in data["flows"]
                     if f["id"] != "proc_002_flow_proc_002_task_5_to_proc_002_task_6"]
    data["flows"].append({
        "id": "proc_002_flow_task5_to_timer",
        "source": "proc_002_task_5",
        "target": "proc_002_timer_1c"
    })
    data["flows"].append({
        "id": "proc_002_flow_timer_to_task6",
        "source": "proc_002_timer_1c",
        "target": "proc_002_task_6"
    })

    data["layout"]["elements"]["proc_002_timer_1c"] = {
        "x": 1785.0, "y": 305.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["flows"].pop("proc_002_flow_proc_002_task_5_to_proc_002_task_6", None)
    data["layout"]["flows"]["proc_002_flow_task5_to_timer"] = [
        {"x": 1800.0, "y": 320.0}, {"x": 1785.0, "y": 320.0}
    ]
    data["layout"]["flows"]["proc_002_flow_timer_to_task6"] = [
        {"x": 1815.0, "y": 320.0}, {"x": 1840.0, "y": 320.0},
        {"x": 1840.0, "y": 1060.0}, {"x": 1880.0, "y": 1060.0}
    ]

    print("  + Timer Event: Ожидание проведения в 1С (1-2 дня)")
    return data


def add_error_events_proc003(data):
    """proc_003: Error при комплектации"""
    print("\n=== proc_003: Добавляю Error Events ===")

    error_end = {
        "id": "proc_003_end_error",
        "type": "endEvent",
        "name": "Ошибка комплектации (возврат)",
        "eventDefinition": "errorEventDefinition",
        "lane": "lane_1b0d3d71"
    }
    data["elements"].append(error_end)

    # From no_2 (Исправление комплектации) - если критично
    data["flows"].append({
        "id": "proc_003_flow_no2_to_error",
        "source": "proc_003_no_2",
        "target": "proc_003_end_error",
        "name": "Невозможно исправить"
    })

    data["layout"]["elements"]["proc_003_end_error"] = {
        "x": 1720.0, "y": 430.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["flows"]["proc_003_flow_no2_to_error"] = [
        {"x": 1600.0, "y": 390.0}, {"x": 1660.0, "y": 390.0},
        {"x": 1660.0, "y": 445.0}, {"x": 1720.0, "y": 445.0}
    ]

    print("  + Error End Event: Ошибка комплектации (возврат)")
    return data


def add_timer_events_proc003(data):
    """proc_003: Timer - ожидание документов от бухгалтерии"""
    print("\n=== proc_003: Добавляю Timer Events ===")

    timer = {
        "id": "proc_003_timer_docs",
        "type": "intermediateCatchEvent",
        "name": "Ожидание документов (до 1ч)",
        "eventDefinition": "timerEventDefinition",
        "lane": "lane_1b0d3d71"
    }
    data["elements"].append(timer)

    # Insert between task_3 (проверка комплектности) and task_4 (документы)
    data["flows"] = [f for f in data["flows"]
                     if f["id"] != "proc_003_flow_proc_003_task_3_to_proc_003_task_4"]
    data["flows"].append({
        "id": "proc_003_flow_task3_to_timer",
        "source": "proc_003_task_3",
        "target": "proc_003_timer_docs"
    })
    data["flows"].append({
        "id": "proc_003_flow_timer_to_task4",
        "source": "proc_003_timer_docs",
        "target": "proc_003_task_4"
    })

    data["layout"]["elements"]["proc_003_timer_docs"] = {
        "x": 1985.0, "y": 305.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["flows"].pop("proc_003_flow_proc_003_task_3_to_proc_003_task_4", None)
    data["layout"]["flows"]["proc_003_flow_task3_to_timer"] = [
        {"x": 2000.0, "y": 320.0}, {"x": 1985.0, "y": 320.0}
    ]
    data["layout"]["flows"]["proc_003_flow_timer_to_task4"] = [
        {"x": 2015.0, "y": 320.0}, {"x": 2040.0, "y": 320.0},
        {"x": 2040.0, "y": 1140.0}, {"x": 2080.0, "y": 1140.0}
    ]

    print("  + Timer Event: Ожидание документов (до 1ч)")
    return data


def add_error_events_proc004(data):
    """proc_004: Error если скидка приводит к убытку"""
    print("\n=== proc_004: Добавляю Error Events ===")

    error_end = {
        "id": "proc_004_end_error",
        "type": "endEvent",
        "name": "Ошибка: скидка делает заказ убыточным",
        "eventDefinition": "errorEventDefinition",
        "lane": "lane_8a6c85a1"
    }
    data["elements"].append(error_end)

    data["flows"].append({
        "id": "proc_004_flow_no2_to_error",
        "source": "proc_004_no_2",
        "target": "proc_004_end_error",
        "name": "Убыточно"
    })

    data["layout"]["elements"]["proc_004_end_error"] = {
        "x": 1720.0, "y": 1010.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["flows"]["proc_004_flow_no2_to_error"] = [
        {"x": 1600.0, "y": 970.0}, {"x": 1660.0, "y": 970.0},
        {"x": 1660.0, "y": 1025.0}, {"x": 1720.0, "y": 1025.0}
    ]

    print("  + Error End Event: Скидка делает заказ убыточным")
    return data


def add_timer_events_proc004(data):
    """proc_004: Timer - ожидание согласования (1-8ч / до 3 дней)"""
    print("\n=== proc_004: Добавляю Timer Events ===")

    timer1 = {
        "id": "proc_004_timer_approval1",
        "type": "intermediateCatchEvent",
        "name": "Ожидание решения руководителя (1-8ч)",
        "eventDefinition": "timerEventDefinition",
        "lane": "lane_8a6c85a1"
    }
    data["elements"].append(timer1)

    timer2 = {
        "id": "proc_004_timer_approval2",
        "type": "intermediateCatchEvent",
        "name": "Ожидание решения директора (до 3 дней)",
        "eventDefinition": "timerEventDefinition",
        "lane": "lane_83319e17"
    }
    data["elements"].append(timer2)

    # Timer1: between task_1 and gw_split_1
    data["flows"] = [f for f in data["flows"]
                     if f["id"] != "proc_004_flow_proc_004_task_1_to_proc_004_gw_split_1"]
    data["flows"].append({
        "id": "proc_004_flow_task1_to_timer1",
        "source": "proc_004_task_1",
        "target": "proc_004_timer_approval1"
    })
    data["flows"].append({
        "id": "proc_004_flow_timer1_to_gw1",
        "source": "proc_004_timer_approval1",
        "target": "proc_004_gw_split_1"
    })

    # Timer2: between task_2 and gw_split_2
    data["flows"] = [f for f in data["flows"]
                     if f["id"] != "proc_004_flow_proc_004_task_2_to_proc_004_gw_split_2"]
    data["flows"].append({
        "id": "proc_004_flow_task2_to_timer2",
        "source": "proc_004_task_2",
        "target": "proc_004_timer_approval2"
    })
    data["flows"].append({
        "id": "proc_004_flow_timer2_to_gw2",
        "source": "proc_004_timer_approval2",
        "target": "proc_004_gw_split_2"
    })

    # Layout
    data["layout"]["elements"]["proc_004_timer_approval1"] = {
        "x": 455.0, "y": 305.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["elements"]["proc_004_timer_approval2"] = {
        "x": 1255.0, "y": 885.0, "width": 30.0, "height": 30.0
    }

    data["layout"]["flows"].pop("proc_004_flow_proc_004_task_1_to_proc_004_gw_split_1", None)
    data["layout"]["flows"]["proc_004_flow_task1_to_timer1"] = [
        {"x": 400.0, "y": 320.0}, {"x": 455.0, "y": 320.0}
    ]
    data["layout"]["flows"]["proc_004_flow_timer1_to_gw1"] = [
        {"x": 485.0, "y": 320.0}, {"x": 520.0, "y": 320.0}
    ]

    data["layout"]["flows"].pop("proc_004_flow_proc_004_task_2_to_proc_004_gw_split_2", None)
    data["layout"]["flows"]["proc_004_flow_task2_to_timer2"] = [
        {"x": 1200.0, "y": 900.0}, {"x": 1255.0, "y": 900.0}
    ]
    data["layout"]["flows"]["proc_004_flow_timer2_to_gw2"] = [
        {"x": 1285.0, "y": 900.0}, {"x": 1320.0, "y": 900.0}
    ]

    print("  + Timer Event: Ожидание решения руководителя (1-8ч)")
    print("  + Timer Event: Ожидание решения директора (до 3 дней)")
    return data


def add_error_events_purchase(data):
    """proc_purchase: Error на приёмке и при рекламации"""
    print("\n=== proc_purchase: Добавляю Error Events ===")

    error_end = {
        "id": "proc_purchase_end_error",
        "type": "endEvent",
        "name": "Ошибка: товар не соответствует (рекламация)",
        "eventDefinition": "errorEventDefinition",
        "lane": "lane_94feb930"
    }
    data["elements"].append(error_end)

    # From no_4 (Рекламация) -> Error End
    data["flows"].append({
        "id": "proc_purchase_flow_no4_to_error",
        "source": "proc_purchase_no_4",
        "target": "proc_purchase_end_error",
        "name": "Отказ"
    })

    data["layout"]["elements"]["proc_purchase_end_error"] = {
        "x": 3320.0, "y": 1570.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["flows"]["proc_purchase_flow_no4_to_error"] = [
        {"x": 3200.0, "y": 1550.0}, {"x": 3260.0, "y": 1550.0},
        {"x": 3260.0, "y": 1585.0}, {"x": 3320.0, "y": 1585.0}
    ]

    print("  + Error End Event: Товар не соответствует (рекламация)")
    return data


def add_timer_events_purchase(data):
    """proc_purchase: Timer на контроль сроков поставки и на тендер"""
    print("\n=== proc_purchase: Добавляю Timer Events ===")

    timer_delivery = {
        "id": "proc_purchase_timer_delivery",
        "type": "intermediateCatchEvent",
        "name": "Контроль срока поставки (по графику)",
        "eventDefinition": "timerEventDefinition",
        "lane": "lane_94feb930"
    }
    data["elements"].append(timer_delivery)

    # Insert between task_8 (заказ поставщику) and task_9 (контроль сроков)
    data["flows"] = [f for f in data["flows"]
                     if f["id"] != "proc_purchase_flow_proc_purchase_task_8_to_proc_purchase_task_9"]
    data["flows"].append({
        "id": "proc_purchase_flow_task8_to_timer",
        "source": "proc_purchase_task_8",
        "target": "proc_purchase_timer_delivery"
    })
    data["flows"].append({
        "id": "proc_purchase_flow_timer_to_task9",
        "source": "proc_purchase_timer_delivery",
        "target": "proc_purchase_task_9"
    })

    data["layout"]["elements"]["proc_purchase_timer_delivery"] = {
        "x": 4185.0, "y": 1465.0, "width": 30.0, "height": 30.0
    }
    data["layout"]["flows"].pop("proc_purchase_flow_proc_purchase_task_8_to_proc_purchase_task_9", None)
    data["layout"]["flows"]["proc_purchase_flow_task8_to_timer"] = [
        {"x": 4200.0, "y": 1480.0}, {"x": 4185.0, "y": 1480.0}
    ]
    data["layout"]["flows"]["proc_purchase_flow_timer_to_task9"] = [
        {"x": 4215.0, "y": 1480.0}, {"x": 4280.0, "y": 1480.0}
    ]

    print("  + Timer Event: Контроль срока поставки")
    return data


def decompose_purchase(data):
    """Декомпозируем proc_purchase: группируем шаги 5-7 в Sub-Process 'Тендер и контрактование',
    шаги 10-12 в Sub-Process 'Приёмка и оприходование'"""
    print("\n=== proc_purchase: Декомпозиция (Sub-Process) ===")

    # Add Sub-Process markers to existing elements
    # Sub-Process 1: Тендер и контрактование (task_5 + task_6 + task_7)
    sub1 = {
        "id": "proc_purchase_sub_tender",
        "type": "subProcess",
        "name": "Тендер и контрактование",
        "lane": "lane_6aecdb2a",
        "contains": ["proc_purchase_task_5", "proc_purchase_task_6", "proc_purchase_task_7"]
    }

    # Sub-Process 2: Приёмка и оприходование (task_10 + task_11 + task_12)
    sub2 = {
        "id": "proc_purchase_sub_reception",
        "type": "subProcess",
        "name": "Приёмка и оприходование",
        "lane": "lane_3ee1b33d",
        "contains": ["proc_purchase_task_10", "proc_purchase_task_11", "proc_purchase_task_12"]
    }

    data["elements"].append(sub1)
    data["elements"].append(sub2)

    # Layout for sub-processes (bounding boxes around their children)
    data["layout"]["elements"]["proc_purchase_sub_tender"] = {
        "x": 3460.0, "y": 1870.0, "width": 560.0, "height": 120.0
    }
    data["layout"]["elements"]["proc_purchase_sub_reception"] = {
        "x": 4460.0, "y": 260.0, "width": 560.0, "height": 120.0
    }

    print("  + Sub-Process: Тендер и контрактование (task_5, task_6, task_7)")
    print("  + Sub-Process: Приёмка и оприходование (task_10, task_11, task_12)")
    print(f"  Было 32 элемента верхнего уровня, теперь логически сгруппировано")
    return data


def add_message_flows_project1(proc001, proc002, proc003, proc004):
    """Добавляем Message Flow между процессами проекта 1"""
    print("\n=== Добавляю Message Flow между процессами ===")

    # proc_001 -> proc_003: Заказ -> Отгрузка (передача заказа в работу)
    proc001["message_flows"].append({
        "id": "mf_001_to_003",
        "name": "Заявка на отгрузку",
        "source_process": "proc_001",
        "source_element": "proc_001_task_7",
        "target_process": "proc_003",
        "target_element": "proc_003_start"
    })
    print("  + Message Flow: proc_001 (Передача заказа в работу) -> proc_003 (Начало отгрузки)")

    # proc_001 -> proc_004: Заказ -> Согласование скидки
    proc001["message_flows"].append({
        "id": "mf_001_to_004",
        "name": "Запрос на согласование скидки",
        "source_process": "proc_001",
        "source_element": "proc_001_yes_2",
        "target_process": "proc_004",
        "target_element": "proc_004_start"
    })
    print("  + Message Flow: proc_001 (Скидка >5%) -> proc_004 (Начало согласования)")

    # proc_001 -> proc_002: Заказ -> Приёмка (при заказе у поставщика)
    proc001["message_flows"].append({
        "id": "mf_001_to_002",
        "name": "Заказ поставщику (товар не в наличии)",
        "source_process": "proc_001",
        "source_element": "proc_001_no_1",
        "target_process": "proc_002",
        "target_element": "proc_002_start"
    })
    print("  + Message Flow: proc_001 (Товар не в наличии) -> proc_002 (Приёмка от поставщика)")

    # proc_003 -> proc_001: Уведомление о нехватке
    proc003["message_flows"].append({
        "id": "mf_003_to_001",
        "name": "Уведомление о нехватке товара",
        "source_process": "proc_003",
        "source_element": "proc_003_no_1",
        "target_process": "proc_001",
        "target_element": "proc_001_task_1"
    })
    print("  + Message Flow: proc_003 (Нехватка товара) -> proc_001 (Менеджер по продажам)")

    # proc_004 -> proc_001: Результат согласования скидки
    proc004["message_flows"].append({
        "id": "mf_004_to_001",
        "name": "Решение по скидке",
        "source_process": "proc_004",
        "source_element": "proc_004_task_4",
        "target_process": "proc_001",
        "target_element": "proc_001_task_3"
    })
    print("  + Message Flow: proc_004 (Решение по скидке) -> proc_001 (Формирование КП)")

    # Copy message flows to other processes too (for bidirectional awareness)
    proc002["message_flows"] = proc001["message_flows"][:1]  # Just reference
    proc003["message_flows"].append(proc001["message_flows"][0])

    return proc001, proc002, proc003, proc004


def create_l0_map(output_dir):
    """Создаём L0 карту процессов предприятия"""
    print("\n=== Создаю L0 карту процессов ===")

    l0_map = {
        "process_id": "L0_process_map",
        "process_name": "Карта процессов предприятия (L0)",
        "description": "Обзорная карта всех бизнес-процессов двух предприятий",
        "level": 0,
        "enterprises": [
            {
                "id": "ent_oknaprom",
                "name": "ООО \"ОкнаПром\"",
                "type": "Производство и продажа окон",
                "processes": {
                    "core": [
                        {
                            "id": "proc_001",
                            "name": "Обработка заказа клиента",
                            "type": "ОСНОВНОЙ",
                            "level": "L1",
                            "trigger": "Обращение клиента",
                            "result": "Подтверждённый заказ",
                            "department": "Отдел продаж",
                            "elements_count": 24,
                            "lanes": ["Менеджер по продажам", "Руководитель отдела продаж",
                                      "Коммерческий директор", "Заведующий складом"],
                            "linked_processes": ["proc_002", "proc_003", "proc_004"]
                        },
                        {
                            "id": "proc_003",
                            "name": "Отгрузка товара клиенту",
                            "type": "ОСНОВНОЙ",
                            "level": "L1",
                            "trigger": "Заявка на отгрузку от менеджера",
                            "result": "Отгруженный товар с документами",
                            "department": "Склад",
                            "elements_count": 19,
                            "lanes": ["Заведующий складом", "Грузчик", "Менеджер по продажам",
                                      "Бухгалтер", "Водитель"],
                            "linked_processes": ["proc_001"]
                        }
                    ],
                    "support": [
                        {
                            "id": "proc_002",
                            "name": "Приёмка товара на склад",
                            "type": "ПОДДЕРЖИВАЮЩИЙ",
                            "level": "L1",
                            "trigger": "Прибытие транспорта с товаром",
                            "result": "Оприходованный товар",
                            "department": "Склад",
                            "elements_count": 14,
                            "lanes": ["Заведующий складом", "Грузчик", "Бухгалтер",
                                      "Менеджер по закупкам"],
                            "linked_processes": ["proc_001"]
                        }
                    ],
                    "management": [
                        {
                            "id": "proc_004",
                            "name": "Согласование скидки",
                            "type": "УПРАВЛЕНЧЕСКИЙ",
                            "level": "L1",
                            "trigger": "Запрос клиента на скидку >5%",
                            "result": "Утверждённая/отклонённая скидка",
                            "department": "Отдел продаж",
                            "elements_count": 18,
                            "lanes": ["Менеджер по продажам", "Руководитель отдела продаж",
                                      "Коммерческий директор"],
                            "linked_processes": ["proc_001"]
                        }
                    ]
                }
            },
            {
                "id": "ent_promresheniya",
                "name": "ООО \"Промышленные решения\"",
                "type": "Промышленное предприятие",
                "processes": {
                    "core": [],
                    "support": [
                        {
                            "id": "proc_purchase",
                            "name": "Закупка товаров и материалов",
                            "type": "ПОДДЕРЖИВАЮЩИЙ",
                            "level": "L1",
                            "trigger": "Формирование потребности в материалах",
                            "result": "Товар оприходован на склад",
                            "department": "Отдел закупок",
                            "elements_count": 35,
                            "sub_processes": [
                                "Тендер и контрактование",
                                "Приёмка и оприходование"
                            ],
                            "lanes": ["Инициатор заявки", "Руководитель подразделения",
                                      "Менеджер по закупкам", "Руководитель отдела закупок",
                                      "Финансовый контролёр", "Юрист", "Кладовщик"],
                            "linked_processes": []
                        }
                    ],
                    "management": []
                }
            }
        ],
        "inter_process_flows": [
            {
                "id": "mf_001_to_003",
                "source": "proc_001",
                "target": "proc_003",
                "name": "Заявка на отгрузку",
                "description": "После подтверждения заказа менеджер передаёт заявку на склад"
            },
            {
                "id": "mf_001_to_004",
                "source": "proc_001",
                "target": "proc_004",
                "name": "Запрос на согласование скидки",
                "description": "При скидке >5% запускается процесс согласования"
            },
            {
                "id": "mf_001_to_002",
                "source": "proc_001",
                "target": "proc_002",
                "name": "Заказ поставщику",
                "description": "При отсутствии товара на складе инициируется закупка"
            },
            {
                "id": "mf_003_to_001",
                "source": "proc_003",
                "target": "proc_001",
                "name": "Уведомление о нехватке",
                "description": "Склад сообщает менеджеру о недостающих позициях"
            },
            {
                "id": "mf_004_to_001",
                "source": "proc_004",
                "target": "proc_001",
                "name": "Решение по скидке",
                "description": "Результат согласования скидки возвращается менеджеру"
            }
        ]
    }

    save_json(os.path.join(output_dir, "L0_process_map.json"), l0_map)
    print("  + L0 карта процессов создана: L0_process_map.json")
    return l0_map


def main():
    print("=" * 60)
    print("  BPM ARCHITECT — КОМПЛЕКСНОЕ ИСПРАВЛЕНИЕ ДЕФЕКТОВ")
    print("=" * 60)

    # Load all processes
    proc001 = load_json(os.path.join(PROJECT1_DIR, "proc_001_bpmn.json"))
    proc002 = load_json(os.path.join(PROJECT1_DIR, "proc_002_bpmn.json"))
    proc003 = load_json(os.path.join(PROJECT1_DIR, "proc_003_bpmn.json"))
    proc004 = load_json(os.path.join(PROJECT1_DIR, "proc_004_bpmn.json"))
    purchase = load_json(os.path.join(PROJECT2_DIR, "proc_purchase_bpmn.json"))

    # Phase 1: Error Events
    proc001 = add_error_events_proc001(proc001)
    proc002 = add_error_events_proc002(proc002)
    proc003 = add_error_events_proc003(proc003)
    proc004 = add_error_events_proc004(proc004)
    purchase = add_error_events_purchase(purchase)

    # Phase 2: Timer Events
    proc001 = add_timer_events_proc001(proc001)
    proc002 = add_timer_events_proc002(proc002)
    proc003 = add_timer_events_proc003(proc003)
    proc004 = add_timer_events_proc004(proc004)
    purchase = add_timer_events_purchase(purchase)

    # Phase 3: Message Flow
    proc001, proc002, proc003, proc004 = add_message_flows_project1(
        proc001, proc002, proc003, proc004)

    # Phase 4: Decompose proc_purchase
    purchase = decompose_purchase(purchase)

    # Phase 5: Create L0 map
    create_l0_map(PROJECT1_DIR)

    # Save all
    print("\n=== Сохраняю все файлы ===")
    save_json(os.path.join(PROJECT1_DIR, "proc_001_bpmn.json"), proc001)
    save_json(os.path.join(PROJECT1_DIR, "proc_002_bpmn.json"), proc002)
    save_json(os.path.join(PROJECT1_DIR, "proc_003_bpmn.json"), proc003)
    save_json(os.path.join(PROJECT1_DIR, "proc_004_bpmn.json"), proc004)
    save_json(os.path.join(PROJECT2_DIR, "proc_purchase_bpmn.json"), purchase)

    # Count elements
    print("\n=== ИТОГИ ===")
    for name, proc in [("proc_001", proc001), ("proc_002", proc002),
                        ("proc_003", proc003), ("proc_004", proc004),
                        ("proc_purchase", purchase)]:
        elem_count = len(proc["elements"])
        flow_count = len(proc["flows"])
        msg_count = len(proc["message_flows"])
        error_count = sum(1 for e in proc["elements"]
                         if e.get("eventDefinition") == "errorEventDefinition")
        timer_count = sum(1 for e in proc["elements"]
                         if e.get("eventDefinition") == "timerEventDefinition")
        sub_count = sum(1 for e in proc["elements"] if e.get("type") == "subProcess")
        print(f"  {name}: {elem_count} элементов, {flow_count} потоков, "
              f"{msg_count} message flows, {error_count} error events, "
              f"{timer_count} timer events, {sub_count} sub-processes")

    print("\n" + "=" * 60)
    print("  ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ УСПЕШНО")
    print("=" * 60)


if __name__ == "__main__":
    main()
