import threading
import winsound


def reproducir_sonido_alerta():
    """
    Alerta de MICROSUEÑO — patrón agresivo de alta frecuencia.
    Alterna entre dos tonos altos para que sea imposible de ignorar.
    Se ejecuta en hilo separado para no pausar la detección.
    """
    def _beep():
        # Patrón: tono alto / tono muy alto, 6 veces
        # 1800 Hz y 2400 Hz son frecuencias que el oído percibe como urgentes
        for _ in range(6):
            winsound.Beep(1800, 180)   # tono alto, corto
            winsound.Beep(2400, 180)   # tono más alto, corto
        # Remate largo para que no quede duda
        winsound.Beep(2000, 600)

    hilo = threading.Thread(target=_beep, daemon=True)
    hilo.start()


def reproducir_sonido_precaucion():
    """
    Alerta de BOSTEZO — más suave, solo un aviso preventivo.
    """
    def _beep():
        winsound.Beep(900, 300)
        winsound.Beep(700, 300)

    hilo = threading.Thread(target=_beep, daemon=True)
    hilo.start()


def lanzar_alerta(tipo="alerta"):
    """
    Función principal llamada desde main.py
    tipo: 'alerta' = microsueño | 'precaucion' = bostezo
    """
    if tipo == "alerta":
        reproducir_sonido_alerta()
    elif tipo == "precaucion":
        reproducir_sonido_precaucion()