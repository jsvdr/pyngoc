import os
import sys

# Agregar backend/ al sys.path para todos los módulos de prueba.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "backend"),
)
