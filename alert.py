import threading
import winsound  # Funciona en Windows sin instalar nada extra

def reproducir_sonido_alerta():
    """
    Reproduce un beep de alerta usando el sistema de Windows.
    Se ejecuta en un hilo separado para no pausar la detección.
    """
    def _beep():
        # Frecuencia 1000hz, duración 800ms — suena fuerte y claro
        for _ in range(3):
            winsound.Beep(1000, 800)

    hilo = threading.Thread(target=_beep, daemon=True)
    hilo.start()


def reproducir_sonido_precaucion():
    """
    Sonido más suave para cuando detecta un bostezo.
    """
    def _beep():
        winsound.Beep(600, 500)

    hilo = threading.Thread(target=_beep, daemon=True)
    hilo.start()


def lanzar_alerta(tipo="alerta"):
    """
    Función principal que se llama desde main.py
    tipo: 'alerta' = microsueño | 'precaucion' = bostezo
    """
    if tipo == "alerta":
        reproducir_sonido_alerta()
    elif tipo == "precaucion":
        reproducir_sonido_precaucion()