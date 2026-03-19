from PIL import Image

img = Image.open(r'C:\Users\Khvorostov\Desktop\visio_page_export.png')
w, h = img.size
print(f"Full size: {w}x{h}")

# Detail: first lane header + first few elements (far left, top 35%)
detail_header = img.crop((0, 0, int(w * 0.06), int(h * 0.40)))
detail_header.save(r'C:\Users\Khvorostov\Desktop\visio_detail_header.png')
print(f"Header detail: {detail_header.size}")

# First task area in blue lane (top lane, first 15% width, top 20% height)
first_task = img.crop((int(w * 0.00), 0, int(w * 0.15), int(h * 0.20)))
first_task.save(r'C:\Users\Khvorostov\Desktop\visio_detail_task.png')
print(f"First task area: {first_task.size}")

# Gateway area (around 35-50% width, 15-50% height)
gateway_area = img.crop((int(w * 0.33), int(h * 0.15), int(w * 0.52), int(h * 0.50)))
gateway_area.save(r'C:\Users\Khvorostov\Desktop\visio_detail_gateway.png')
print(f"Gateway area: {gateway_area.size}")
