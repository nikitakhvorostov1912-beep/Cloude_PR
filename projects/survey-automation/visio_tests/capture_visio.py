import subprocess, time, ctypes
from ctypes import wintypes

# Find Visio window
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
        if ('Visio' in title or 'vsdx' in title.lower()) and IsWindowVisible(hwnd):
            handles.append((hwnd, title))
    return True

EnumWindows(EnumWindowsProc(foreach_window), 0)
print('Visio windows:', handles)

vsdx_path = r'C:\Users\Khvorostov\Desktop\logistics_bpmn_new.vsdx'

if not handles:
    print('Opening Visio...')
    subprocess.Popen([r'C:\Program Files\Microsoft Office\root\Office16\VISIO.EXE', vsdx_path])
    time.sleep(8)
    handles = []
    EnumWindows(EnumWindowsProc(foreach_window), 0)
    print('After open:', handles)

if handles:
    hwnd = handles[0][0]
    ShowWindow(hwnd, 3)  # SW_MAXIMIZE
    SetForegroundWindow(hwnd)
    time.sleep(1.5)

    # Keyboard shortcuts using ctypes (no win32api needed)
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

    # Take screenshot
    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    rect = RECT()
    GetWindowRect(hwnd, ctypes.byref(rect))
    print(f'Window rect: {rect.left},{rect.top},{rect.right},{rect.bottom}')

    from PIL import ImageGrab
    img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    out = r'C:\Users\Khvorostov\Desktop\visio_full.png'
    img.save(out)
    print(f'Screenshot saved to: {out}')
    print(f'Image size: {img.size}')
else:
    print('ERROR: Could not find or open Visio window.')
