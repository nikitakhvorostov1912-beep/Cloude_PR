import time, ctypes
from ctypes import wintypes

EnumWindows = ctypes.windll.user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
IsWindowVisible = ctypes.windll.user32.IsWindowVisible
ShowWindow = ctypes.windll.user32.ShowWindow
SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
GetWindowRect = ctypes.windll.user32.GetWindowRect

handles = []
def foreach_window(hwnd, lParam):
    length = GetWindowTextLength(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowText(hwnd, buf, length + 1)
        title = buf.value
        if IsWindowVisible(hwnd):
            handles.append((hwnd, title))
    return True

EnumWindows(EnumWindowsProc(foreach_window), 0)

# Find the logistics window
target_hwnd = None
for hwnd, title in handles:
    if 'logistics_bpmn_new' in title.lower() or 'logistics' in title.lower():
        target_hwnd = hwnd
        print(f'Found target: hwnd={ctypes.cast(hwnd, ctypes.c_void_p).value}, title={title}')
        break

if target_hwnd is None:
    # fallback - show all visio windows
    for hwnd, title in handles:
        if 'visio' in title.lower() or 'vsdx' in title.lower() or 'svg' in title.lower():
            print(f'Visio/SVG window: {ctypes.cast(hwnd, ctypes.c_void_p).value} - {title}')
    print('No logistics window found')
else:
    # Move window to primary monitor first, then maximize
    # MoveWindow to (0,0) on primary screen before maximizing
    SW_RESTORE = 9
    SW_MAXIMIZE = 3
    ShowWindow(target_hwnd, SW_RESTORE)
    time.sleep(1)
    
    # Move window to primary screen (0,0)
    MoveWindow = ctypes.windll.user32.MoveWindow
    MoveWindow(target_hwnd, 100, 100, 1600, 900, True)
    time.sleep(0.5)
    
    ShowWindow(target_hwnd, SW_MAXIMIZE)
    SetForegroundWindow(target_hwnd)
    time.sleep(2)

    # Send Ctrl+Shift+H (Fit to Page)
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    KEY_H = 0x48
    KEYEVENTF_KEYUP = 0x0002

    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 0, 0)
    ctypes.windll.user32.keybd_event(KEY_H, 0, 0, 0)
    ctypes.windll.user32.keybd_event(KEY_H, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(2)

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    rect = RECT()
    GetWindowRect(target_hwnd, ctypes.byref(rect))
    print(f'Window rect: {rect.left},{rect.top},{rect.right},{rect.bottom}')

    from PIL import ImageGrab
    l = rect.left
    t = rect.top
    r = rect.right
    b = rect.bottom

    # Clamp to valid positive region
    l = max(l, 0)
    t = max(t, 0)
    r = max(r, 1)
    b = max(b, 1)

    if r <= l or b <= t:
        print(f'ERROR: Invalid bbox after clamping: ({l},{t},{r},{b}). Window may be off-screen.')
        print('Trying full primary screen capture instead...')
        img = ImageGrab.grab()
    else:
        img = ImageGrab.grab(bbox=(l, t, r, b))

    out = r'C:\Users\Khvorostov\Desktop\visio_logistics.png'
    img.save(out)
    print(f'Screenshot saved: {out}')
    print(f'Size: {img.size}')
