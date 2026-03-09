from PIL import Image

img = Image.open(r'C:\Users\Khvorostov\Desktop\template_bpmn_export.png')
w, h = img.size
print(f"Full size: {w}x{h}")

# Left section: lane headers + first tasks
left = img.crop((0, 0, int(w * 0.30), h))
left.save(r'C:\Users\Khvorostov\Desktop\tmpl_left.png')
print(f"Left: {left.size}")

# Middle: gateways area 
mid = img.crop((int(w * 0.28), 0, int(w * 0.62), h))
mid.save(r'C:\Users\Khvorostov\Desktop\tmpl_mid.png')
print(f"Mid: {mid.size}")

# Right area
right = img.crop((int(w * 0.60), 0, w, h))
right.save(r'C:\Users\Khvorostov\Desktop\tmpl_right.png')
print(f"Right: {right.size}")
