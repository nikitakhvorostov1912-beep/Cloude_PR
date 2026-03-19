from PIL import Image, ImageDraw, ImageFont

# Load the template diagram full export
img = Image.open(r'C:\Users\Khvorostov\Desktop\template_bpmn_export.png')
w, h = img.size
print(f"Template diagram: {w}x{h}")

# Save a scaled-down version for overview (fit in 3000px wide)
scale = 3000 / w
new_w = int(w * scale)
new_h = int(h * scale)
overview = img.resize((new_w, new_h), Image.LANCZOS)
overview.save(r'C:\Users\Khvorostov\Desktop\final_overview.png')
print(f"Overview saved: {overview.size}")

# Detail montage: combine key zoomed areas
detail_task = Image.open(r'C:\Users\Khvorostov\Desktop\zoom_task1.png')
detail_end = Image.open(r'C:\Users\Khvorostov\Desktop\zoom_end_events.png')

# Resize both to same height (500px)
th = 400
task_scaled = detail_task.resize((int(detail_task.width * th / detail_task.height), th), Image.LANCZOS)
end_scaled = detail_end.resize((int(detail_end.width * th / detail_end.height), th), Image.LANCZOS)

# Side by side
total_w = task_scaled.width + end_scaled.width + 20
montage = Image.new('RGB', (total_w, th), (240, 240, 240))
montage.paste(task_scaled, (0, 0))
montage.paste(end_scaled, (task_scaled.width + 20, 0))
montage.save(r'C:\Users\Khvorostov\Desktop\final_details.png')
print(f"Detail montage saved: {montage.size}")
