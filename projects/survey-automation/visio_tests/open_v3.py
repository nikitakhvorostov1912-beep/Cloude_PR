import win32com.client as win32
import subprocess, time

vsdx = r'C:\Users\Khvorostov\Desktop\logistics_bpmn_v3.vsdx'

# Try to get active Visio or open it
try:
    visio = win32.GetActiveObject("Visio.Application")
    print(f"Visio connected: {visio.Version}")
except:
    print("Starting Visio...")
    subprocess.Popen([r'C:\Program Files\Microsoft Office\root\Office16\VISIO.EXE', vsdx])
    time.sleep(8)
    visio = win32.GetActiveObject("Visio.Application")

# Open v3 file
print("Opening v3 file...")
doc = visio.Documents.Open(vsdx)
time.sleep(3)

page = doc.Pages.Item(1)
print(f"Page: {page.Name}, Shapes: {page.Shapes.Count}")

# Print first few element names to verify fix
for i in range(1, min(6, page.Shapes.Count + 1)):
    sh = page.Shapes.Item(i)
    if sh.Text:
        print(f"  Shape {i}: '{sh.Text[:60]}'")

# Export as PNG
out = r'C:\Users\Khvorostov\Desktop\visio_v3_export.png'
page.Export(out)
print(f"Exported to: {out}")

# Close this doc to avoid conflicts
doc.Close()
print("Done")
