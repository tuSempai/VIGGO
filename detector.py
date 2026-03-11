import numpy as np

# ─── Índices de puntos faciales de MediaPipe ───────────────────────────────
OJO_IZQ = [362, 385, 387, 263, 373, 380]
OJO_DER = [33,  160, 158, 133, 153, 144]
BOCA    = [13,  14,  78,  308, 82,  312]

# ─── Umbrales ─────────────────────────────────────────────────────────────
UMBRAL_EAR = 0.25   # Menor a este valor = ojos cerrados
UMBRAL_MAR = 0.60   # Mayor a este valor = bostezo


def calcular_EAR(landmarks, puntos_ojo, w, h):
    """
    Eye Aspect Ratio — mide qué tan abierto está el ojo.
    Si el valor baja de 0.25 significa que el ojo está cerrado.
    """
    p = [
        (int(landmarks[i].x * w), int(landmarks[i].y * h))
        for i in puntos_ojo
    ]
    vertical1   = np.linalg.norm(np.array(p[1]) - np.array(p[5]))
    vertical2   = np.linalg.norm(np.array(p[2]) - np.array(p[4]))
    horizontal  = np.linalg.norm(np.array(p[0]) - np.array(p[3]))

    if horizontal == 0:
        return 0.0

    ear = (vertical1 + vertical2) / (2.0 * horizontal)
    return round(ear, 3)


def calcular_MAR(landmarks, w, h):
    """
    Mouth Aspect Ratio — mide qué tan abierta está la boca.
    Si el valor sube de 0.60 significa que la persona está bostezando.
    """
    p = [
        (int(landmarks[i].x * w), int(landmarks[i].y * h))
        for i in BOCA
    ]
    vertical   = np.linalg.norm(np.array(p[0]) - np.array(p[1]))
    horizontal = np.linalg.norm(np.array(p[2]) - np.array(p[3]))

    if horizontal == 0:
        return 0.0

    mar = vertical / horizontal
    return round(mar, 3)


def evaluar_estado(ear, mar, segundos_ojos_cerrados):
    """
    Decide el estado del conductor según EAR, MAR y tiempo.
    Retorna: 'normal', 'precaucion' o 'alerta'
    """
    if ear < UMBRAL_EAR and segundos_ojos_cerrados >= 2:
        return "alerta"       # Microsueño detectado
    elif mar > UMBRAL_MAR:
        return "precaucion"   # Bostezo detectado
    else:
        return "normal"