# -------------------------------------------------------------
# FUNCIÓN DE ENCRIPTACIÓN DE CONTRASEÑAS
# -------------------------------------------------------------
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
