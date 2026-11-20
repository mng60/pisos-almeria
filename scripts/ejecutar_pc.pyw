"""Lanzador sin consola para la tarea programada: python -m pisos.pc desde la raíz del repositorio.

Se usa .pyw con pythonw.exe para que no aparezca una ventana negra; el registro va a
%LOCALAPPDATA%\\pisos-almeria\\pc.log.
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ))
sys.argv = ["pisos.pc", *sys.argv[1:]]

from pisos.pc import main  # noqa: E402

main()
