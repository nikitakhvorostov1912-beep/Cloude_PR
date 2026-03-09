"""
check_visio.py — Верификатор VSDX-файлов BPMN-диаграмм.

Парсит visio/pages/page1.xml из VSDX (ZIP-архив) и проверяет:
  R1.1 — Нет перекрывающихся фигур (bbox intersection)
  R1.2 — Все фигуры лежат внутри своей дорожки
  R1.3 — Минимальный gap между соседними фигурами ≥ 0.03"
  R1.4 — Ни одна фигура не выходит за правую границу страницы
  R2.1 — Нет emoji (U+1F000+) в тексте фигур
  R2.2 — Текст doc-бейджей помещается в shape (нет overflow)
  R2.3 — Нет "…" в тексте (нет усечения)

Запуск:
  python backend/scripts/check_visio.py path/to/file.vsdx
  python backend/scripts/check_visio.py backend/data/projects/<id>/visio/  # все файлы

Exit codes:
  0 — все проверки PASS
  1 — есть нарушения
"""
from __future__ import annotations

import math
import sys
import io
import zipfile

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from itertools import combinations

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

NS = "http://schemas.microsoft.com/office/visio/2012/main"
MIN_GAP_INCH = 0.03          # минимальный зазор между фигурами
LANE_MIN_WIDTH = 5.0         # фигуры шире этого — дорожки (пулы/lanes)
CONNECTOR_OBJ_TYPE = "2"     # ObjType=2 → коннектор
HEADER_MAX_WIDTH = 1.0       # узкие заголовки дорожек (rotated text)
OVERLAP_TOLERANCE = 0.005    # допуск для перекрытий (погрешность float)
BADGE_MAX_SIZE = 0.30        # фигуры меньше этого — бейджи (👤, ⚙ и т.д.), исключаем из R1.1

# ---------------------------------------------------------------------------
# Структуры данных
# ---------------------------------------------------------------------------

@dataclass
class Shape:
    shape_id: str
    name: str
    pin_x: float
    pin_y: float
    width: float
    height: float
    obj_type: str = "1"   # "1"=shape, "2"=connector
    is_connector: bool = False
    is_lane: bool = False
    is_header: bool = False
    txt_angle: float = 0.0
    text: str = ""

    @property
    def x_min(self) -> float:
        return self.pin_x - self.width / 2

    @property
    def x_max(self) -> float:
        return self.pin_x + self.width / 2

    @property
    def y_min(self) -> float:
        return self.pin_y - self.height / 2

    @property
    def y_max(self) -> float:
        return self.pin_y + self.height / 2

    @property
    def label(self) -> str:
        t = self.text[:40].replace("\n", " ")
        if t:
            return f'"{t}"'
        return f"Shape#{self.shape_id}({self.name})"


@dataclass
class CheckResult:
    code: str
    passed: bool
    message: str
    violations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Парсер VSDX
# ---------------------------------------------------------------------------

def _get_cell(shape_el: ET.Element, name: str) -> str | None:
    """Возвращает атрибут V ячейки с именем name."""
    for cell in shape_el.iterfind(f"{{{NS}}}Cell"):
        if cell.get("N") == name:
            return cell.get("V")
    return None


def _get_text(shape_el: ET.Element) -> str:
    """Извлекает текст из элемента Shape."""
    text_el = shape_el.find(f"{{{NS}}}Text")
    if text_el is not None:
        parts = []
        if text_el.text:
            parts.append(text_el.text.strip())
        for cp in text_el:
            if cp.tail:
                parts.append(cp.tail.strip())
        return " ".join(p for p in parts if p)
    return ""


def parse_vsdx(path: Path) -> tuple[list[Shape], float, float]:
    """
    Парсит VSDX и возвращает (shapes, page_width, page_height).
    page_width/height в дюймах из visio/pages/pages.xml.
    """
    shapes: list[Shape] = []
    page_width = 0.0
    page_height = 0.0

    with zipfile.ZipFile(path) as zf:
        # Размеры страницы из pages.xml
        try:
            with zf.open("visio/pages/pages.xml") as f:
                pages_root = ET.parse(f).getroot()
            page_el = pages_root.find(f"{{{NS}}}Page")
            if page_el is not None:
                sheet = page_el.find(f"{{{NS}}}PageSheet")
                if sheet is not None:
                    for cell in sheet.iterfind(f"{{{NS}}}Cell"):
                        if cell.get("N") == "PageWidth":
                            page_width = float(cell.get("V", 0))
                        elif cell.get("N") == "PageHeight":
                            page_height = float(cell.get("V", 0))
        except Exception:
            pass

        # Фигуры из page1.xml
        try:
            with zf.open("visio/pages/page1.xml") as f:
                root = ET.parse(f).getroot()
        except KeyError:
            return shapes, page_width, page_height

        shapes_el = root.find(f"{{{NS}}}Shapes")
        if shapes_el is None:
            return shapes, page_width, page_height

        for sh in shapes_el.iterfind(f"{{{NS}}}Shape"):
            sid = sh.get("ID", "?")
            name = sh.get("NameU", "")

            pin_x_s = _get_cell(sh, "PinX")
            pin_y_s = _get_cell(sh, "PinY")
            width_s = _get_cell(sh, "Width")
            height_s = _get_cell(sh, "Height")
            obj_type_s = _get_cell(sh, "ObjType") or "1"
            txt_angle_s = _get_cell(sh, "TxtAngle") or "0"

            # Пропускаем фигуры без геометрии
            if not all([pin_x_s, pin_y_s, width_s, height_s]):
                continue

            try:
                pin_x = float(pin_x_s)
                pin_y = float(pin_y_s)
                w = float(width_s)
                h = float(height_s)
                txt_angle = float(txt_angle_s)
            except (ValueError, TypeError):
                continue

            is_connector = obj_type_s == CONNECTOR_OBJ_TYPE or name.startswith("Connector.")
            is_lane = (not is_connector) and (w >= LANE_MIN_WIDTH)
            is_header = (not is_connector) and (not is_lane) and (w <= HEADER_MAX_WIDTH) and (abs(txt_angle) > 0.5)

            text = _get_text(sh)

            shapes.append(Shape(
                shape_id=sid,
                name=name,
                pin_x=pin_x,
                pin_y=pin_y,
                width=w,
                height=h,
                obj_type=obj_type_s,
                is_connector=is_connector,
                is_lane=is_lane,
                is_header=is_header,
                txt_angle=txt_angle,
                text=text,
            ))

    return shapes, page_width, page_height


# ---------------------------------------------------------------------------
# Проверки
# ---------------------------------------------------------------------------

def _is_badge(shape: Shape) -> bool:
    """Бейдж — маленькая декоративная фигура (👤, ⚙, ×, ■ на углу задачи)."""
    return shape.width <= BADGE_MAX_SIZE and shape.height <= BADGE_MAX_SIZE


def check_r1_1_overlaps(content: list[Shape]) -> CheckResult:
    """R1.1 — Нет перекрывающихся фигур (исключая бейджи на задачах)."""
    violations = []
    # Проверяем только пары NON-badge фигур или badge vs badge
    main_shapes = [s for s in content if not _is_badge(s)]

    for a, b in combinations(main_shapes, 2):
        # Проверяем перекрытие bbox с допуском
        x_overlap = (a.x_min < b.x_max - OVERLAP_TOLERANCE) and (b.x_min < a.x_max - OVERLAP_TOLERANCE)
        y_overlap = (a.y_min < b.y_max - OVERLAP_TOLERANCE) and (b.y_min < a.y_max - OVERLAP_TOLERANCE)
        if x_overlap and y_overlap:
            dx = min(a.x_max, b.x_max) - max(a.x_min, b.x_min)
            dy = min(a.y_max, b.y_max) - max(a.y_min, b.y_min)
            violations.append(
                f"  ⚠ {a.label} <-> {b.label}: перекрытие {dx:.3f}\" x {dy:.3f}\""
            )

    badges_count = len(content) - len(main_shapes)
    passed = len(violations) == 0
    msg = (
        f"R1.1 — Нет перекрывающихся фигур ({len(main_shapes)} проверено, {badges_count} бейджей исключено)"
        if passed
        else f"R1.1 — НАРУШЕНИЙ: {len(violations)} из {len(main_shapes)*(len(main_shapes)-1)//2} пар"
    )
    return CheckResult("R1.1", passed, msg, violations)


def check_r1_2_lane_boundary(content: list[Shape], lanes: list[Shape]) -> CheckResult:
    """R1.2 — Все фигуры лежат ВНУТРИ своей дорожки."""
    if not lanes:
        return CheckResult("R1.2", True, "R1.2 — Дорожки не найдены, проверка пропущена")

    # Исключаем бейджи — их позиция зависит от задачи, не от дорожки
    check_shapes = [s for s in content if not _is_badge(s)]

    violations = []
    for shape in check_shapes:
        # Ищем дорожку, в которую попадает фигура по X и Y
        enclosing = [
            lane for lane in lanes
            if (lane.x_min - OVERLAP_TOLERANCE <= shape.x_min
                and shape.x_max <= lane.x_max + OVERLAP_TOLERANCE
                and lane.y_min - OVERLAP_TOLERANCE <= shape.y_min
                and shape.y_max <= lane.y_max + OVERLAP_TOLERANCE)
        ]
        if not enclosing:
            # Найдём дорожку с наибольшим перекрытием по X (ближайшую)
            best_lane = min(
                lanes,
                key=lambda lane: abs((lane.y_min + lane.y_max) / 2 - (shape.y_min + shape.y_max) / 2)
            )
            detail_parts = []
            if shape.y_min < best_lane.y_min - OVERLAP_TOLERANCE:
                detail_parts.append(f"выходит снизу на {best_lane.y_min - shape.y_min:.3f}\"")
            if shape.y_max > best_lane.y_max + OVERLAP_TOLERANCE:
                detail_parts.append(f"выходит сверху на {shape.y_max - best_lane.y_max:.3f}\"")
            if shape.x_min < best_lane.x_min - OVERLAP_TOLERANCE:
                detail_parts.append(f"выходит влево на {best_lane.x_min - shape.x_min:.3f}\"")
            if shape.x_max > best_lane.x_max + OVERLAP_TOLERANCE:
                detail_parts.append(f"выходит вправо на {shape.x_max - best_lane.x_max:.3f}\"")
            detail = "; ".join(detail_parts) if detail_parts else "не находится ни в одной дорожке"
            violations.append(f"  ⚠ {shape.label}: {detail}")

    passed = len(violations) == 0
    msg = (
        f"R1.2 — Все {len(check_shapes)} фигур лежат в пределах дорожек"
        if passed
        else f"R1.2 — НАРУШЕНИЙ: {len(violations)} фигур выходят за дорожки"
    )
    return CheckResult("R1.2", passed, msg, violations)


def check_r1_3_min_gap(content: list[Shape]) -> CheckResult:
    """R1.3 — Минимальный gap между соседними фигурами ≥ MIN_GAP_INCH."""
    min_gap = float("inf")
    min_pair: tuple[Shape, Shape] | None = None

    for a, b in combinations(content, 2):
        # Горизонтальный gap (если ряды пересекаются по Y)
        y_overlap = (a.y_min < b.y_max) and (b.y_min < a.y_max)
        x_overlap = (a.x_min < b.x_max) and (b.x_min < a.x_max)

        if y_overlap and not x_overlap:
            gap_x = max(a.x_min, b.x_min) - min(a.x_max, b.x_max)
            if gap_x < min_gap:
                min_gap = gap_x
                min_pair = (a, b)

        # Вертикальный gap (если колонки пересекаются по X)
        if x_overlap and not y_overlap:
            gap_y = max(a.y_min, b.y_min) - min(a.y_max, b.y_max)
            if gap_y < min_gap:
                min_gap = gap_y
                min_pair = (a, b)

    if min_gap == float("inf"):
        return CheckResult("R1.3", True, "R1.3 — Нет соседних фигур для проверки gap")

    passed = min_gap >= MIN_GAP_INCH
    violations = []
    if not passed and min_pair:
        a, b = min_pair
        violations.append(
            f"  ⚠ {a.label} ↔ {b.label}: gap = {min_gap:.3f}\" (норма ≥ {MIN_GAP_INCH}\")"
        )

    msg = (
        f"R1.3 — Минимальный gap = {min_gap:.3f}\" (норма ≥ {MIN_GAP_INCH}\")"
        if passed
        else f"R1.3 — Gap {min_gap:.3f}\" ниже нормы {MIN_GAP_INCH}\""
    )
    return CheckResult("R1.3", passed, msg, violations)


def check_r1_4_page_boundary(content: list[Shape], page_width: float, page_height: float) -> CheckResult:
    """R1.4 — Ни одна фигура не выходит за границы страницы."""
    violations = []
    for shape in content:
        if page_width > 0 and shape.x_max > page_width + OVERLAP_TOLERANCE:
            violations.append(
                f"  ⚠ {shape.label}: x_max={shape.x_max:.3f}\" > page_width={page_width:.3f}\" "
                f"(выход на {shape.x_max - page_width:.3f}\")"
            )
        if page_width > 0 and shape.x_min < -OVERLAP_TOLERANCE:
            violations.append(
                f"  ⚠ {shape.label}: x_min={shape.x_min:.3f}\" < 0"
            )
        if page_height > 0 and shape.y_max > page_height + OVERLAP_TOLERANCE:
            violations.append(
                f"  ⚠ {shape.label}: y_max={shape.y_max:.3f}\" > page_height={page_height:.3f}\""
            )
        if page_height > 0 and shape.y_min < -OVERLAP_TOLERANCE:
            violations.append(
                f"  ⚠ {shape.label}: y_min={shape.y_min:.3f}\" < 0"
            )

    passed = len(violations) == 0
    msg = (
        f"R1.4 — Все фигуры в пределах страницы {page_width:.2f}\" × {page_height:.2f}\""
        if passed
        else f"R1.4 — НАРУШЕНИЙ: {len(violations)} фигур выходят за границу страницы"
    )
    return CheckResult("R1.4", passed, msg, violations)


# ---------------------------------------------------------------------------
# R2 — Качество текста и рендеринга
# ---------------------------------------------------------------------------

def _visual_text_width_ascii(text: str) -> int:
    """Простая оценка визуальной ширины текста в условных символах.

    Кирилличесике и CJK-символы считаются как 1.2 латинских.
    Используется только для оценки (не пиксельная точность).
    """
    total = 0.0
    for c in (text or ""):
        cp = ord(c)
        if 0x0400 <= cp <= 0x04FF:  # Кириллица
            total += 1.2
        elif cp > 0x2000:           # Прочие широкие
            total += 1.2
        else:
            total += 1.0
    return int(total)


def _is_doc_badge(shape: Shape) -> bool:
    """Doc/system-бейджи: шире 0.30" но уже 2.2", высотой 0.20-0.50"."""
    return (0.30 < shape.width <= 2.2) and (0.20 <= shape.height <= 0.50)


def check_r2_1_no_emoji(shapes: list[Shape]) -> CheckResult:
    """R2.1 — Emoji (U+1F000+) смешанный с текстом вызывает проблемы рендеринга в Visio.

    Чисто-иконочные shapes (текст = только emoji, без других символов) — OK.
    Проблема: emoji смешан с обычным текстом (e.g. "📥 Название документа").
    """
    violations = []
    for shape in shapes:
        if not shape.text:
            continue
        emoji_chars = [c for c in shape.text if ord(c) >= 0x1F000]
        if not emoji_chars:
            continue
        # Чистая иконка (весь текст — только emoji) — допустимо
        non_emoji = "".join(c for c in shape.text if ord(c) < 0x1F000).strip()
        if non_emoji:  # emoji + обычный текст = проблема рендеринга
            codes = ", ".join(f"U+{ord(c):04X}" for c in emoji_chars[:3])
            violations.append(
                f"  !! {shape.label}: emoji {codes} смешан с текстом '{non_emoji[:30]}'"
            )
    passed = len(violations) == 0
    msg = (
        "R2.1 — Emoji не смешаны с текстом в фигурах"
        if passed
        else f"R2.1 — НАРУШЕНИЙ: {len(violations)} фигур содержат emoji вместе с текстом"
    )
    return CheckResult("R2.1", passed, msg, violations)


def check_r2_2_badge_text_fit(shapes: list[Shape]) -> CheckResult:
    """R2.2 — Текст doc/system-бейджей должен помещаться в shape (нет overflow)."""
    FONT_SIZE = 0.065        # размер шрифта бейджей в дюймах
    LINE_HEIGHT = FONT_SIZE * 1.4
    CHAR_WIDTH = FONT_SIZE * 0.85   # средняя ширина символа кириллицы
    H_PADDING = 0.12                # горизонтальные поля (LeftMargin + RightMargin)
    V_PADDING = 0.08                # вертикальные поля

    violations = []
    for shape in shapes:
        if not _is_doc_badge(shape) or not shape.text:
            continue
        usable_w = max(0.01, shape.width - H_PADDING)
        chars_per_line = max(1, int(usable_w / CHAR_WIDTH))
        visual_len = _visual_text_width_ascii(shape.text)
        lines_needed = math.ceil(visual_len / chars_per_line)
        usable_h = max(0.01, shape.height - V_PADDING)
        lines_available = max(1, int(usable_h / LINE_HEIGHT))
        if lines_needed > lines_available:
            violations.append(
                f"  !! {shape.label}: нужно {lines_needed} строк, "
                f"вмещается {lines_available} (h={shape.height:.3f}\")"
            )
    passed = len(violations) == 0
    msg = (
        "R2.2 — Текст всех бейджей помещается в shape"
        if passed
        else f"R2.2 — НАРУШЕНИЙ: {len(violations)} бейджей с overflow текста"
    )
    return CheckResult("R2.2", passed, msg, violations)


def check_r2_3_no_truncation(shapes: list[Shape]) -> CheckResult:
    """R2.3 — Нет усечённого текста (символ "…" = Visio обрезал содержимое)."""
    violations = []
    for shape in shapes:
        if shape.text and "\u2026" in shape.text:
            violations.append(
                f"  !! {shape.label}: текст содержит усечение '…'"
            )
    passed = len(violations) == 0
    msg = (
        "R2.3 — Нет усечённых текстов"
        if passed
        else f"R2.3 — НАРУШЕНИЙ: {len(violations)} фигур с усечённым текстом"
    )
    return CheckResult("R2.3", passed, msg, violations)


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def check_file(path: Path) -> bool:
    """
    Проверяет один VSDX файл. Возвращает True если все PASS.
    """
    print(f"\n{'='*60}")
    print(f"[FILE] {path.name}")
    print(f"{'='*60}")

    try:
        shapes, page_width, page_height = parse_vsdx(path)
    except Exception as e:
        print(f"[ERROR] Не удалось разобрать файл: {e}")
        return False

    # Классифицируем фигуры
    lanes = [s for s in shapes if s.is_lane]
    connectors = [s for s in shapes if s.is_connector]
    headers = [s for s in shapes if s.is_header]
    content = [s for s in shapes if not s.is_connector and not s.is_lane and not s.is_header]

    print(f"[STAT] всего={len(shapes)}, дорожек={len(lanes)}, "
          f"хедеров={len(headers)}, контент={len(content)}, коннекторов={len(connectors)}")
    print(f"[PAGE] {page_width:.2f}\" x {page_height:.2f}\"")

    # Запускаем проверки
    results = [
        check_r1_1_overlaps(content),
        check_r1_2_lane_boundary(content, lanes),
        check_r1_3_min_gap(content),
        check_r1_4_page_boundary(content, page_width, page_height),
        check_r2_1_no_emoji(shapes),
        check_r2_2_badge_text_fit(shapes),
        check_r2_3_no_truncation(shapes),
    ]

    all_passed = True
    print()
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.message}")
        for v in result.violations:
            print(v)
        if not result.passed:
            all_passed = False

    print()
    if all_passed:
        print(f"[OK] ИТОГ: ВСЕ {len(results)} ПРОВЕРОК ПРОШЛИ")
    else:
        fail_count = sum(1 for r in results if not r.passed)
        print(f"[!!] ИТОГ: НАРУШЕНИЙ В {fail_count} ИЗ {len(results)} ПРОВЕРОК")

    return all_passed


def main() -> int:
    # Принудительно UTF-8 для Windows-терминала (только при прямом запуске)
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Использование:")
        print("  python check_visio.py <file.vsdx>           # один файл")
        print("  python check_visio.py <directory/>          # все .vsdx в папке")
        return 1

    target = Path(sys.argv[1])

    if target.is_dir():
        files = list(target.glob("**/*.vsdx"))
        if not files:
            print(f"[ERROR] Нет .vsdx файлов в {target}")
            return 1
    elif target.is_file():
        files = [target]
    else:
        print(f"[ERROR] Не найдено: {target}")
        return 1

    all_ok = True
    for f in sorted(files):
        ok = check_file(f)
        if not ok:
            all_ok = False

    if len(files) > 1:
        print(f"\n{'='*60}")
        if all_ok:
            print(f"[OK] ИТОГО: все {len(files)} файлов прошли проверку")
        else:
            print(f"[!!] ИТОГО: есть нарушения в файлах (см. выше)")
        print(f"{'='*60}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
