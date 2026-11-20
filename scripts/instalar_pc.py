"""Deja lista la parte del PC (Idealista y yaencontre). Se puede relanzar: no duplica nada.

    python scripts/instalar_pc.py            comprueba, instala, crea las tareas y hace una pasada de prueba
    python scripts/instalar_pc.py --sin-prueba

Qué hace y por qué:
1. Comprueba Python 3.12+, Edge, git con remoto y `gh` autenticado (el PC sube los datos y relanza el workflow).
2. Instala requirements-pc.txt (playwright usa el Edge instalado: no descarga navegadores).
3. Crea la tarea programada «Pisos Almeria - diario» (09:00, solo con la sesión iniciada porque Edge tiene que
   verse para poder resolver el captcha) y un lanzador oculto en la carpeta Inicio que corre 5 min después de
   entrar. pisos.pc consulta como mucho una vez al día con éxito, así que los dos no duplican visitas.
4. Pasada de prueba con --seco: abre Edge, lee los dos portales (resuelve el captcha si sale) y no sube nada.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
LANZADOR = RAIZ / "scripts" / "ejecutar_pc.pyw"
TAREAS = {
    "Pisos Almeria - diario": ["/SC", "DAILY", "/ST", "09:00"],
}
# Una tarea /SC ONLOGON exige administrador (medido el 20/11/2026: «Acceso denegado»). Al iniciar sesión se usa
# un .vbs en la carpeta Inicio del usuario, que no lo exige y lanza la pasada oculta tras 5 minutos.
INICIO = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
VBS = INICIO / "pisos-almeria.vbs"
EDGE = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]


def comprobar() -> list[str]:
    faltas = []
    if sys.version_info < (3, 12):
        faltas.append(f"Python 3.12 o superior (tienes {sys.version.split()[0]}): https://www.python.org/downloads/")
    if not any(p.exists() for p in EDGE):
        faltas.append("Microsoft Edge: https://www.microsoft.com/edge")
    if not shutil.which("git"):
        faltas.append("git: https://git-scm.com/download/win")
    elif subprocess.run(["git", "-C", str(RAIZ), "remote", "get-url", "origin"], capture_output=True).returncode:
        faltas.append("el repositorio no tiene remoto 'origin': clónalo con «gh repo clone mng60/pisos-almeria»")
    if not shutil.which("gh"):
        faltas.append("GitHub CLI: https://cli.github.com/ y luego «gh auth login»")
    elif subprocess.run(["gh", "auth", "status"], capture_output=True).returncode:
        faltas.append("GitHub CLI sin sesión: ejecuta «gh auth login»")
    return faltas


def pythonw() -> str:
    candidato = Path(sys.executable).with_name("pythonw.exe")
    return str(candidato if candidato.exists() else sys.executable)


def crear_tareas() -> None:
    accion = f'"{pythonw()}" "{LANZADOR}"'
    for nombre, cuando in TAREAS.items():
        # /IT: solo con la sesión iniciada (Edge tiene que verse). /F: sobrescribe si ya existe.
        r = subprocess.run(["schtasks", "/Create", "/F", "/IT", "/TN", nombre, "/TR", accion, *cuando],
                           capture_output=True, text=True)
        estado = "creada" if r.returncode == 0 else f"ERROR: {r.stderr.strip() or r.stdout.strip()}"
        print(f"  tarea «{nombre}»: {estado}")
        if r.returncode:
            sys.exit(1)
    # 0 = ventana oculta; --retraso 300 espera 5 min a que el escritorio esté listo.
    VBS.write_text(f'CreateObject("WScript.Shell").Run """{pythonw()}"" ""{LANZADOR}"" --retraso 300", 0\n',
                   encoding="utf-8")
    print(f"  al iniciar sesión: {VBS}")


def main() -> None:
    print("1. Comprobando requisitos…")
    faltas = comprobar()
    if faltas:
        print("Falta:\n  - " + "\n  - ".join(faltas))
        sys.exit(1)
    print("   todo bien")
    print("2. Instalando dependencias…")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(RAIZ / "requirements-pc.txt")],
                   check=True)
    print("3. Creando tareas programadas…")
    crear_tareas()
    if "--sin-prueba" in sys.argv:
        return
    print("4. Pasada de prueba (sin subir nada). Si sale un captcha en Edge, resuélvelo.")
    subprocess.run([sys.executable, "-m", "pisos.pc", "--seco", "--forzar"], cwd=RAIZ, check=True)
    print("Listo. Registro de cada pasada: %LOCALAPPDATA%\\pisos-almeria\\pc.log")


if __name__ == "__main__":
    main()
