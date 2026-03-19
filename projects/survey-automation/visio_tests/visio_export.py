import time, sys

try:
    import win32com.client as win32
    
    # Connect to running Visio instance
    visio = win32.GetActiveObject("Visio.Application")
    print(f"Visio connected: {visio.Version}")
    
    # Find the logistics document
    target_doc = None
    for i in range(1, visio.Documents.Count + 1):
        doc = visio.Documents.Item(i)
        print(f"  Doc: {doc.Name}")
        if 'logistics' in doc.Name.lower():
            target_doc = doc
            break
    
    if target_doc is None:
        vsdx_path = r'C:\Users\Khvorostov\Desktop\logistics_bpmn_new.vsdx'
        target_doc = visio.Documents.Open(vsdx_path)
        print(f"Opened: {target_doc.Name}")
    
    # Get page
    page = target_doc.Pages.Item(1)
    print(f"Page: {page.Name}, shapes: {page.Shapes.Count}")
    
    # List first few shapes for debugging
    for i in range(1, min(8, page.Shapes.Count + 1)):
        sh = page.Shapes.Item(i)
        print(f"  Shape {i}: '{sh.Name}' Text='{sh.Text[:30] if sh.Text else ''}' pos=({sh.PinX:.2f},{sh.PinY:.2f})")
    
    # Export page as PNG  
    out_png = r'C:\Users\Khvorostov\Desktop\visio_page_export.png'
    page.Export(out_png)
    print(f"Exported to: {out_png}")
    
    # Also fit the active window
    try:
        win = visio.ActiveWindow
        win.Zoom = 0
        print("Zoom set to fit")
    except:
        pass
        
except ImportError:
    print("pywin32 not installed, trying screenshot approach")
    import ctypes, time
    from PIL import ImageGrab
    
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
    
    if handles:
        hwnd = handles[0][0]
        # Move window to primary screen
        ctypes.windll.user32.MoveWindow(hwnd, 0, 0, 1600, 900, True)
        ctypes.windll.user32.ShowWindow(hwnd, 3)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        time.sleep(2)
        
        # Press Ctrl+A to select all, then Ctrl+Shift+H to fit
        VK_CONTROL = 0x11
        KEY_A = 0x41
        VK_SHIFT = 0x10
        KEY_H = 0x48
        KEYEVENTF_KEYUP = 0x0002
        
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        ctypes.windll.user32.keybd_event(KEY_A, 0, 0, 0)
        ctypes.windll.user32.keybd_event(KEY_A, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.5)
        
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 0, 0)
        ctypes.windll.user32.keybd_event(KEY_H, 0, 0, 0)
        ctypes.windll.user32.keybd_event(KEY_H, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(2)
        
        img = ImageGrab.grab()
        img.save(r'C:\Users\Khvorostov\Desktop\visio_page_export.png')
        print(f"Screenshot saved, size: {img.size}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
