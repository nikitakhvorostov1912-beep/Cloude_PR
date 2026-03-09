# -*- coding: utf-8 -*-
import sys, os, glob, subprocess

sys.stdout.reconfigure(encoding='utf-8')

INFOBASE = r"C:\Users\Khvorostov\Documents\InfoBase7"
SRC_DIR  = r"C:\CLOUDE_PR\projects\1c-uso\epf\src"
OUT_EPF  = r"C:\CLOUDE_PR\projects\1c-uso\epf\MetadataUSO.epf"
OUT_LOG  = r"C:\CLOUDE_PR\projects\1c-uso\epf\build_log.txt"

# Найти 1cv8c.exe
exe = None
for p in [r"C:\Program Files\1cv8\*\bin\1cv8c.exe",
          r"C:\Program Files (x86)\1cv8\*\bin\1cv8c.exe"]:
    m = sorted(glob.glob(p))
    if m:
        exe = m[-1]
        break

if not exe:
    print("ОШИБКА: 1cv8c.exe не найден")
    sys.exit(1)

bin_dir = os.path.dirname(exe)
print(f"1cv8c: {exe}")
print(f"bin_dir: {bin_dir}")

# Добавляем bin-папку в PATH — чтобы загрузились зависимые DLL
env = os.environ.copy()
env["PATH"] = bin_dir + ";" + env.get("PATH", "")

cmd = [
    exe, "DESIGNER",
    "/F", INFOBASE,
    "/LoadExternalDataProcessorFromFiles", SRC_DIR, OUT_EPF,
    "/DisableStartupDialogs",
    "/Out", OUT_LOG,
]

print(f"Команда: {' '.join(cmd)}")
print("\nЗапускаю (ожидание до 90 сек)...")
result = subprocess.run(cmd, env=env, cwd=bin_dir, timeout=90)
print(f"Код возврата: {result.returncode}")

if os.path.exists(OUT_LOG):
    with open(OUT_LOG, encoding='utf-8', errors='replace') as f:
        content = f.read()
        print(f"\nЛог ({len(content)} байт):")
        print(content[-3000:] if len(content) > 3000 else content)

if os.path.exists(OUT_EPF):
    print(f"\nUSPEH: {OUT_EPF}  ({os.path.getsize(OUT_EPF)//1024} KB)")
else:
    print("\nFAIL: .epf не создан")
    # Попробуем альтернативный синтаксис команды
    print("\nПробую альтернативный синтаксис...")
    cmd2 = [exe, "/F", INFOBASE,
            "/LoadExternalDataProcessorFromFiles", SRC_DIR, OUT_EPF]
    r2 = subprocess.run(cmd2, env=env, cwd=bin_dir, timeout=90)
    print(f"Код возврата 2: {r2.returncode}")
    if os.path.exists(OUT_EPF):
        print(f"USPEH (попытка 2): {OUT_EPF}")
