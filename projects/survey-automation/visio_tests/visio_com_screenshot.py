import time, sys

try:
    import win32com.client as win32
    
    # Connect to running Visio instance
    visio = win32.GetActiveObject("Visio.Application")
    print(f"Visio connected: {visio.Version}")
    
    # Find the logistics document
    target_doc = None
    for doc in visio.Documents:
        print(f"  Doc: {doc.Name}")
        if 'logistics' in doc.Name.lower():
            target_doc = doc
            break
    
    if target_doc is None:
        # Try opening it
        vsdx_path = r'C:\Users\Khvorostov\Desktop\logistics_bpmn_new.vsdx'
        target_doc = visio.Documents.Open(vsdx_path)
        print(f"Opened: {target_doc.Name}")
    
    # Get page
    page = target_doc.Pages[1]
    print(f"Page: {page.Name}, shapes: {page.Shapes.Count}")
    
    # List shapes
    for i in range(1, min(6, page.Shapes.Count + 1)):
        sh = page.Shapes[i]
        print(f"  Shape {i}: '{sh.Name}', pos=({sh.PinX:.2f},{sh.PinY:.2f}), w={sh.Width:.2f}, h={sh.Height:.2f}")
    
    # Activate the window and fit all
    win = visio.ActiveWindow
    win.Activate()
    win.Zoom = 0  # 0 = fit to page/window
    time.sleep(1)
    
    # Export page as PNG for inspection  
    out_png = r'C:\Users\Khvorostov\Desktop\visio_export.png'
    page.Export(out_png)
    print(f"Page exported to: {out_png}")
    
except Exception as e:
    print(f"COM error: {e}")
    # Fallback: try via screenshot with keyboard
    import ctypes, time
    
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    
    handles = []
    def foreach_window(hwnd, lParam):
        length = GetWindowTextLength(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buf, length + 1)
            title = buf.value
            if 'logistics' in title.lower() and IsWindowVisible(hwnd):
                handles.append((hwnd, title))
        return True
    
    EnumWindows(EnumWindowsProc(foreach_window), 0)
    print(f"Logistics windows found: {handles}")
