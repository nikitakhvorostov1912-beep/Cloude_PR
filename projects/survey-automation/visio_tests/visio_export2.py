import win32com.client as win32

visio = win32.GetActiveObject("Visio.Application")
print(f"Visio: {visio.Version}")

# Find logistics doc
target_doc = None
for i in range(1, visio.Documents.Count + 1):
    doc = visio.Documents.Item(i)
    if 'logistics' in doc.Name.lower():
        target_doc = doc
        break

if target_doc is None:
    target_doc = visio.Documents.Open(r'C:\Users\Khvorostov\Desktop\logistics_bpmn_new.vsdx')

page = target_doc.Pages.Item(1)
print(f"Shapes: {page.Shapes.Count}")

# Export to PNG
out = r'C:\Users\Khvorostov\Desktop\visio_page_export.png'
page.Export(out)
print(f"Exported: {out}")
