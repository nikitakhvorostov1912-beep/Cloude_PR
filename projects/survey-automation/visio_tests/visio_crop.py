from PIL import Image

img = Image.open(r'C:\Users\Khvorostov\Desktop\visio_page_export.png')
w, h = img.size
print(f"Full size: {w}x{h}")

# Left portion - lane headers area (first 20% width)
left = img.crop((0, 0, int(w * 0.20), h))
left.save(r'C:\Users\Khvorostov\Desktop\visio_crop_left.png')
print(f"Left crop saved: {left.size}")

# First few elements area (0-35% width)
first_elements = img.crop((0, 0, int(w * 0.35), h))
first_elements.save(r'C:\Users\Khvorostov\Desktop\visio_crop_first.png')
print(f"First elements saved: {first_elements.size}")

# Middle portion
mid = img.crop((int(w * 0.35), 0, int(w * 0.70), h))
mid.save(r'C:\Users\Khvorostov\Desktop\visio_crop_mid.png')
print(f"Mid crop saved: {mid.size}")
