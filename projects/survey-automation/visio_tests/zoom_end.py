from PIL import Image

img = Image.open(r'C:\Users\Khvorostov\Desktop\template_bpmn_export.png')
w, h = img.size
print(f"Full: {w}x{h}")

# End events area - far right, top lanes (Клиент + Менеджер)
end_area = img.crop((int(w * 0.83), 0, w, int(h * 0.30)))
end_area.save(r'C:\Users\Khvorostov\Desktop\zoom_end_events.png')
print(f"End events: {end_area.size}")

# First gateway area - zoom in on first gateway and its branches
gw_area = img.crop((int(w * 0.38), 0, int(w * 0.55), int(h * 0.25)))
gw_area.save(r'C:\Users\Khvorostov\Desktop\zoom_first_gw.png')
print(f"First GW: {gw_area.size}")

# First task close-up (blue lane, task 1 area)
task1 = img.crop((int(w * 0.07), 0, int(w * 0.22), int(h * 0.25)))
task1.save(r'C:\Users\Khvorostov\Desktop\zoom_task1.png')
print(f"Task1: {task1.size}")
