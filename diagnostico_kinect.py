"""
diagnostico_kinect.py
=====================
Rode isso PRIMEIRO antes de qualquer outra coisa.
Ele te diz exatamente o que está faltando.

Como rodar:
    python diagnostico_kinect.py
"""
import os, sys
sdk = r"C:\Program Files\Microsoft SDKs\Kinect\v2.0_1409"
os.environ['PATH'] = sdk + ";" + sdk + r"\Redist\amd64" + ";" + os.environ['PATH']
# Recarrega o PATH no processo atual (Windows específico)
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(sdk)
    os.add_dll_directory(sdk + r"\Redist\amd64")

print("=" * 55)
print("  DIAGNÓSTICO KINECT V2")
print("=" * 55)

# ── 1. Python 64-bit? (obrigatório para pykinect2) ──────────────
print("\n[1] Arquitetura do Python:")
bits = "64-bit" if sys.maxsize > 2**32 else "32-bit"
print(f"    {bits}  ({sys.executable})")
if bits != "64-bit":
    print("    ❌ PROBLEMA: pykinect2 exige Python 64-bit!")
    print("       Baixe o Python 64-bit em https://python.org")
    sys.exit(1)
else:
    print("    ✓ OK")

# ── 2. SDK instalado? ────────────────────────────────────────────
print("\n[2] Kinect for Windows SDK 2.0:")
sdk_path = os.environ.get("KINECTSDK20_DIR", "")
if sdk_path and os.path.exists(sdk_path):
    print(f"    ✓ Encontrado em: {sdk_path}")
else:
    print("    ❌ PROBLEMA: variável KINECTSDK20_DIR não encontrada.")
    print("       Reinstale o SDK e reinicie o PC.")
    print("       Download: https://www.microsoft.com/en-us/download/details.aspx?id=44561")

# ── 3. pykinect2 instalado? ──────────────────────────────────────
print("\n[3] Pacote pykinect2:")
try:
    import pykinect2
    print(f"    ✓ Instalado")
except ImportError:
    print("    ❌ PROBLEMA: não instalado.")
    print("       Execute: pip install pykinect2")
    sys.exit(1)

# ── 4. Consegue importar o runtime? ─────────────────────────────
print("\n[4] Importando PyKinectRuntime:")
try:
    from pykinect2 import PyKinectV2
    from pykinect2.PyKinectRuntime import PyKinectRuntime
    print("    ✓ Import OK")
except Exception as e:
    print(f"    ❌ PROBLEMA: {e}")
    print("       Verifique se o SDK está instalado e o PC foi reiniciado.")
    sys.exit(1)

# ── 5. Consegue abrir o sensor? ──────────────────────────────────
print("\n[5] Abrindo o sensor (aguarde ~3 segundos):")
import time
try:
    kinect = PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
    print("    ✓ Sensor aberto!")
except Exception as e:
    print(f"    ❌ PROBLEMA ao abrir sensor: {e}")
    print()
    print("    Causas comuns:")
    print("    • Kinect Studio aberto ao mesmo tempo (feche-o)")
    print("    • Outro processo usando o sensor")
    print("    • USB 2.0 — o Kinect v2 EXIGE USB 3.0")
    sys.exit(1)

# ── 6. Chega frame? ─────────────────────────────────────────────
print("\n[6] Aguardando primeiro frame de profundidade:")
deadline = time.time() + 5.0
frame_recebido = False
while time.time() < deadline:
    if kinect.has_new_depth_frame():
        frame = kinect.get_last_depth_frame()
        if frame is not None:
            import numpy as np
            arr = np.frombuffer(frame, dtype=np.uint16).copy()
            validos = int(np.sum(arr > 0))
            print(f"    ✓ Frame recebido!")
            print(f"      Tamanho do buffer : {arr.size} valores")
            print(f"      Pixels com leitura: {validos:,} de {arr.size:,}")
            print(f"      Distância média   : {arr[arr>0].mean():.0f} mm")
            frame_recebido = True
            break
    time.sleep(0.05)

if not frame_recebido:
    print("    ❌ Nenhum frame em 5 segundos.")
    print("       Verifique o cabo USB e tente outra porta USB 3.0.")

kinect.close()

# ── Resumo ───────────────────────────────────────────────────────
print()
print("=" * 55)
if frame_recebido:
    print("  ✅ TUDO OK! O Kinect v2 está funcionando.")
    print("  Pode rodar o projeto principal agora.")
else:
    print("  ⚠  Sensor abre mas não entrega frames.")
    print("  Tente outra porta USB 3.0 ou reinicie o Kinect.")
print("=" * 55)