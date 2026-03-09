import win32com.client as win32
import subprocess, time

vsdx = r'C:\Users\Khvorostov\Desktop\template_bpmn.vsdx'

try:
    visio = win32.GetActiveObject("Visio.Application")
    print(f"Visio connected: {visio.Version}")
except:
    print("Starting Visio...")
    subprocess.Popen([r'C:\Program Files\Microsoft Office\root\Office16\VISIO.EXE', vsdx])
    time.sleep(8)
    visio = win32.GetActiveObject("Visio.Application")

doc = visio.Documents.Open(vsdx)
time.sleep(2)
page = doc.Pages.Item(1)
print(f"Shapes: {page.Shapes.Count}")

out = r'C:\Users\Khvorostov\Desktop\template_bpmn_export.png'
page.Export(out)
print(f"Exported: {out}")
doc.Close()
