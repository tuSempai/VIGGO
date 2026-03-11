import cv2
import numpy as np

# Cargamos los detectores que vienen incluidos en OpenCV
DETECTOR_ROSTRO = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)
DETECTOR_OJOS = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_eye.xml'
)

UMBRAL_EAR   = 0.25
UMBRAL_MAR   = 0.60


def detectar_ojos(frame):
    """
    Detecta ojos en el frame y retorna su EAR aproximado.
    Retorna (ear, frame_con_dibujo)
    """
    gris  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rostros = DETECTOR_ROSTRO.detectMultiScale(gris, 1.1, 5, minSize=(80, 80))

    ear = 0.35  # valor normal por defecto

    for (x, y, w, h) in rostros:
        roi_gris  = gris[y:y+h, x:x+w]
        ojos = DETECTOR_OJOS.detectMultiScale(roi_gris, 1.1, 10)

        if len(ojos) >= 2:
            # EAR aproximado: altura / ancho del ojo detectado
            areas_ear = []
            for (ex, ey, ew, eh) in ojos[:2]:
                ear_ojo = eh / ew  # cuando cierra, eh baja → EAR baja
                areas_ear.append(ear_ojo)
                cv2.rectangle(frame,
                              (x+ex, y+ey),
                              (x+ex+ew, y+ey+eh),
                              (0, 255, 255), 2)
            ear = sum(areas_ear) / len(areas_ear)

        elif len(ojos) == 1:
            # Solo detecta un ojo → probablemente cerrando
            ear = 0.20

        elif len(ojos) == 0:
            # No detecta ojos → ojos muy cerrados
            ear = 0.10

        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 200, 255), 2)

    return round(ear, 3), frame


def detectar_boca(frame):
    """
    Detecta boca abierta usando detector de sonrisa/boca.
    Retorna MAR aproximado.
    """
    detector_boca = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_smile.xml'
    )
    gris   = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rostros = DETECTOR_ROSTRO.detectMultiScale(gris, 1.1, 5, minSize=(80, 80))

    mar = 0.0

    for (x, y, w, h) in rostros:
        roi_gris = gris[y + h//2 : y+h, x:x+w]  # solo mitad inferior
        bocas = detector_boca.detectMultiScale(roi_gris, 1.7, 20)

        if len(bocas) > 0:
            bx, by, bw, bh = bocas[0]
            mar = bh / bw  # boca abierta → mar sube
            cv2.rectangle(frame,
                          (x+bx, y + h//2 + by),
                          (x+bx+bw, y + h//2 + by+bh),
                          (0, 255, 0), 2)

    return round(mar, 3), frame


def evaluar_estado(ear, mar, segundos_ojos_cerrados):
    """
    Retorna: 'normal', 'precaucion' o 'alerta'
    """
    if ear < UMBRAL_EAR and segundos_ojos_cerrados >= 2:
        return "alerta"
    elif mar > UMBRAL_MAR:
        return "precaucion"
    else:
        return "normal"