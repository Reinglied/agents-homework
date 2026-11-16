"""Hidden console input compatible with Windows line editing."""
import getpass
import os


def read_key():
    """Use Windows line editing with echo disabled, preserving normal paste."""
    if os.name != "nt":
        return getpass.getpass("API key (hidden): ").strip()
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.ReadConsoleW.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                                   ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    handle = kernel.GetStdHandle(-10 & 0xffffffff)
    original_mode = wintypes.DWORD()
    if not kernel.GetConsoleMode(handle, ctypes.byref(original_mode)):
        raise OSError("Run this script in an interactive PowerShell terminal.")
    # Processed line input handles console editing; turn echo and VT input off.
    mode = (original_mode.value | 0x0001 | 0x0002) & ~(0x0004 | 0x0200)
    if not kernel.SetConsoleMode(handle, mode):
        raise ctypes.WinError(ctypes.get_last_error())
    print("API key (hidden; paste then Enter): ", end="", flush=True)
    try:
        buffer = ctypes.create_unicode_buffer(4096)
        count = wintypes.DWORD()
        if not kernel.ReadConsoleW(handle, buffer, len(buffer) - 1, ctypes.byref(count), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if not count.value:
            raise OSError("Input cancelled.")
        return buffer[:count.value].strip()
    finally:
        kernel.SetConsoleMode(handle, original_mode.value)
        print()
