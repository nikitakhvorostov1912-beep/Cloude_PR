"""Создание .vsdx файлов на базе шаблона из библиотеки vsdx.

Использует встроенный шаблон ``media.vsdx`` из пакета ``vsdx`` как
основу — он содержит все необходимые XML-файлы (windows.xml,
document.xml с полной структурой), которые требуются
Microsoft Visio 2013+ для корректного открытия файла.

Мастер-шейпы (masters) полностью удалены из архива вместе
со всеми ссылками ([Content_Types].xml, document.xml.rels,
page1.xml.rels), чтобы Visio не переопределял размеры
наших фигур формулами из мастера.

Наши фигуры подставляются в page1.xml, а размеры страницы
обновляются в pages.xml.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import vsdx


def _get_template_path() -> str:
    """Путь к встроенному шаблону из библиотеки vsdx."""
    return str(Path(vsdx.__file__).parent / "media" / "media.vsdx")


def create_blank_vsdx(output_path: Path) -> Path:
    """Создаёт минимальный пустой .vsdx файл.

    Args:
        output_path: Путь для сохранения файла.

    Returns:
        Путь к созданному файлу.
    """
    return create_bpmn_vsdx("", output_path)


def create_bpmn_vsdx(
    shapes_xml: str,
    output_path: Path,
    title: str = "BPMN Diagram",
    page_width: float = 33.11,
    page_height: float = 46.81,
) -> Path:
    """Создаёт .vsdx файл с BPMN-элементами.

    Берёт за основу шаблон из библиотеки ``vsdx`` (содержит все
    необходимые структурные XML-файлы), заменяет page1.xml на наши
    фигуры и обновляет размеры страницы в pages.xml.

    Все мастер-шейпы удалены, [Content_Types].xml и
    document.xml.rels перезаписаны без ссылок на masters.

    Args:
        shapes_xml: XML-строка с элементами ``<Shape>`` для page1.xml.
        output_path: Путь для сохранения.
        title: Название диаграммы.
        page_width: Ширина страницы в дюймах.
        page_height: Высота страницы в дюймах.

    Returns:
        Путь к созданному файлу.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    template_path = _get_template_path()

    # Файлы, которые мы заменяем или удаляем
    skip_files = {
        # Наши замены
        "[Content_Types].xml",  # убираем ссылки на masters
        "visio/pages/page1.xml",
        "visio/pages/pages.xml",
        "visio/pages/_rels/page1.xml.rels",
        # Удаляем мастер-шейпы полностью
        "visio/masters/masters.xml",
        "visio/masters/master1.xml",
        "visio/masters/_rels/masters.xml.rels",
        # Заменяем document.xml.rels (убираем ссылку на masters)
        "visio/_rels/document.xml.rels",
        # Не нужен thumbnail
        "docProps/thumbnail.emf",
    }

    # page1.xml — наши фигуры
    page1_xml = (
        "<?xml version='1.0' encoding='utf-8' ?>\n"
        "<PageContents xmlns='http://schemas.microsoft.com/office/visio/2012/main'"
        " xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'"
        " xml:space='preserve'>"
        "<Shapes>\n"
        f"{shapes_xml}\n"
        "</Shapes>"
        "</PageContents>"
    )

    # pages.xml — описание страницы с размерами
    pages_xml = (
        "<?xml version='1.0' encoding='utf-8' ?>\n"
        "<Pages xmlns='http://schemas.microsoft.com/office/visio/2012/main'"
        " xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'"
        " xml:space='preserve'>"
        f"<Page ID='0' NameU='{_xml_attr_escape(title)}'"
        f" Name='{_xml_attr_escape(title)}'>"
        "<PageSheet LineStyle='0' FillStyle='0' TextStyle='0'>"
        f"<Cell N='PageWidth' V='{page_width:.4f}'/>"
        f"<Cell N='PageHeight' V='{page_height:.4f}'/>"
        "<Cell N='ShdwOffsetX' V='0.1181102362204724'/>"
        "<Cell N='ShdwOffsetY' V='-0.1181102362204724'/>"
        "<Cell N='PageScale' V='1' U='IN_F'/>"
        "<Cell N='DrawingScale' V='1' U='IN_F'/>"
        "<Cell N='DrawingSizeType' V='1'/>"
        "<Cell N='DrawingScaleType' V='0'/>"
        "<Cell N='InhibitSnap' V='0'/>"
        "<Cell N='UIVisibility' V='0'/>"
        "<Cell N='ShdwType' V='0'/>"
        "<Cell N='ShdwObliqueAngle' V='0'/>"
        "<Cell N='ShdwScaleFactor' V='1'/>"
        "<Cell N='DrawingResizeType' V='0'/>"
        "</PageSheet>"
        "<Rel r:id='rId1'/>"
        "</Page>"
        "</Pages>"
    )

    # [Content_Types].xml — БЕЗ masters
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels"'
        ' ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/visio/document.xml"'
        ' ContentType="application/vnd.ms-visio.drawing.main+xml"/>'
        '<Override PartName="/visio/pages/pages.xml"'
        ' ContentType="application/vnd.ms-visio.pages+xml"/>'
        '<Override PartName="/visio/pages/page1.xml"'
        ' ContentType="application/vnd.ms-visio.page+xml"/>'
        '<Override PartName="/visio/windows.xml"'
        ' ContentType="application/vnd.ms-visio.windows+xml"/>'
        '<Override PartName="/docProps/core.xml"'
        ' ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '<Override PartName="/docProps/custom.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>'
        '</Types>'
    )

    # document.xml.rels — БЕЗ ссылки на masters (rId1 удалён)
    doc_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns='
        '"http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId3"'
        ' Type="http://schemas.microsoft.com/visio/2010/relationships/windows"'
        ' Target="windows.xml"/>'
        '<Relationship Id="rId2"'
        ' Type="http://schemas.microsoft.com/visio/2010/relationships/pages"'
        ' Target="pages/pages.xml"/>'
        '</Relationships>'
    )

    # Пустой page1.xml.rels — без ссылки на master
    page1_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns='
        '"http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )

    # Копируем шаблон, пропуская мастера и заменяемые файлы
    with zipfile.ZipFile(template_path, "r") as src:
        with zipfile.ZipFile(str(output_path), "w", zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                if item.filename in skip_files:
                    continue
                data = src.read(item.filename)
                dst.writestr(item, data)

            # Записываем наши файлы
            dst.writestr("[Content_Types].xml", content_types_xml)
            dst.writestr("visio/pages/page1.xml", page1_xml)
            dst.writestr("visio/pages/pages.xml", pages_xml)
            dst.writestr("visio/pages/_rels/page1.xml.rels", page1_rels)
            dst.writestr("visio/_rels/document.xml.rels", doc_rels_xml)

    return output_path


def _xml_attr_escape(text: str) -> str:
    """Экранирует спецсимволы для XML-атрибутов."""
    return (
        text.replace("&", "&amp;")
        .replace("'", "&apos;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
