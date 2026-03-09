"""Генерация иконки приложения через Pillow"""
import os
import sys

def generate_icon():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Установка Pillow...")
        os.system(f"{sys.executable} -m pip install Pillow -q")
        from PIL import Image, ImageDraw

    build_dir = os.path.join(os.path.dirname(__file__), '..', 'build')
    os.makedirs(build_dir, exist_ok=True)

    sizes = [256, 128, 64, 48, 32, 16]
    images = []

    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Фоновый прямоугольник с градиентом (симуляция)
        radius = size // 6
        draw.rounded_rectangle([0, 0, size-1, size-1], radius=radius,
                                fill=(99, 102, 241, 255))

        # Иконка диаграммы (столбцы)
        margin = size // 5
        col_w = max(2, size // 12)
        gap = max(1, size // 16)
        bar_x = margin

        heights = [0.6, 0.9, 0.5, 0.75, 0.4]
        for h_ratio in heights:
            bar_h = int((size - 2 * margin) * h_ratio)
            bar_y = size - margin - bar_h
            draw.rectangle([bar_x, bar_y, bar_x + col_w, size - margin],
                           fill=(255, 255, 255, 230))
            bar_x += col_w + gap

        images.append(img)

    # Сохранить PNG
    png_path = os.path.join(build_dir, 'icon.png')
    images[0].save(png_path)
    print(f"PNG сохранён: {png_path}")

    # Сохранить ICO (все размеры)
    ico_path = os.path.join(build_dir, 'icon.ico')
    images[0].save(ico_path, format='ICO', sizes=[(s, s) for s in sizes])
    print(f"ICO сохранён: {ico_path}")

if __name__ == '__main__':
    generate_icon()
