from PIL import Image

img = Image.open(r'C:\Users\Khvorostov\Desktop\visio_v3_export.png')
w, h = img.size
print(f"Full size: {w}x{h}")

# Left portion with lane headers and first tasks
left = img.crop((0, 0, int(w * 0.08), h))
left.save(r'C:\Users\Khvorostov\Desktop\v3_left.png')
print(f"Left crop: {left.size}")

# First tasks area (0-20% width)
tasks_area = img.crop((0, 0, int(w * 0.20), h))
tasks_area.save(r'C:\Users\Khvorostov\Desktop\v3_tasks.png')
print(f"Tasks area: {tasks_area.size}")

# Middle area with gateways (30-60% width)
mid = img.crop((int(w * 0.28), 0, int(w * 0.55), h))
mid.save(r'C:\Users\Khvorostov\Desktop\v3_mid.png')
print(f"Mid crop: {mid.size}")

# Right side
right = img.crop((int(w * 0.55), 0, w, h))
right.save(r'C:\Users\Khvorostov\Desktop\v3_right.png')
print(f"Right crop: {right.size}")
