import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import FaceLandmarkerOptions, RunningMode
import urllib.request
import os

# ── Umbrales ───────────────────────────────────────────────────────────────────
EAR_BUENO   = 0.28
EAR_MEDIANO = 0.24
EAR_MALO    = 0.21
MAR_BOSTEZO = 0.55

# ── Índices de landmarks (MediaPipe 478 puntos con refine) ─────────────────────
LEFT_EYE  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH     = [13, 14, 78, 308]

# ── Silhouette para dibujar contorno del rostro ────────────────────────────────
SILHOUETTE = [10,338,297,332,284,251,389,356,454,323,361,288,
              397,365,379,378,400,377,152,148,176,149,150,136,
              172,58,132,93,234,127,162,21,54,103,67,109,10]

# ── Descargar modelo si no existe ─────────────────────────────────────────────
MODEL_PATH = "face_landmarker.task"
MODEL_URL  = ("https://storage.googleapis.com/mediapipe-models/"
              "face_landmarker/face_landmarker/float16/1/face_landmarker.task")

def _asegurar_modelo():
    if not os.path.exists(MODEL_PATH):
        print("[VIGGO] Descargando modelo de MediaPipe (~6 MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("[VIGGO] Modelo descargado.")

_asegurar_modelo()

# ── Inicializar FaceLandmarker ─────────────────────────────────────────────────
_base_opts = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
_opts = FaceLandmarkerOptions(
    base_options=_base_opts,
    running_mode=RunningMode.IMAGE,
    num_faces=1,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
LANDMARKER = mp_vision.FaceLandmarker.create_from_options(_opts)


# ── Funciones de cálculo ───────────────────────────────────────────────────────
def _dist(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


def _ear(lm, indices, w, h):
    pts = [(lm[i].x * w, lm[i].y * h) for i in indices]
    v1 = _dist(pts[1], pts[5])
    v2 = _dist(pts[2], pts[4])
    ho = _dist(pts[0], pts[3])
    return (v1 + v2) / (2.0 * ho + 1e-6)


def _mar(lm, indices, w, h):
    pts = [(lm[i].x * w, lm[i].y * h) for i in indices]
    vert = _dist(pts[0], pts[1])
    hori = _dist(pts[2], pts[3])
    return vert / (hori + 1e-6)


# ── Función principal ──────────────────────────────────────────────────────────
def detectar_rostro(frame):
    """
    Procesa el frame y retorna (ear, mar, frame_anotado).
    Si no detecta rostro retorna ear=0.35, mar=0.0.
    """
    h, w = frame.shape[:2]
    rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = LANDMARKER.detect(mp_img)

    ear_val = 0.35
    mar_val = 0.0

    if result.face_landmarks:
        lm = result.face_landmarks[0]

        ear_val = (_ear(lm, LEFT_EYE,  w, h) + _ear(lm, RIGHT_EYE, w, h)) / 2.0
        mar_val = _mar(lm, MOUTH, w, h)

        def pt(i):
            return (int(lm[i].x * w), int(lm[i].y * h))

        # Dibujar contorno de ojos
        for eye_idx in [LEFT_EYE, RIGHT_EYE]:
            pts = np.array([pt(i) for i in eye_idx], np.int32)
            cv2.polylines(frame, [pts], isClosed=True, color=(0, 230, 255), thickness=1)
            for p in pts:
                cv2.circle(frame, tuple(p), 2, (0, 255, 200), -1)

        # Dibujar boca
        for a, b in [(MOUTH[0], MOUTH[1]), (MOUTH[2], MOUTH[3])]:
            cv2.line(frame, pt(a), pt(b), (0, 255, 100), 1)
        for i in MOUTH:
            cv2.circle(frame, pt(i), 2, (0, 255, 100), -1)

        # Silhouette facial
        sil_pts = np.array([pt(i) for i in SILHOUETTE], np.int32)
        cv2.polylines(frame, [sil_pts], isClosed=False,
                      color=(0, 160, 255), thickness=1)

    return round(ear_val, 3), round(mar_val, 3), frame


def evaluar_estado(ear, mar, segundos_ojos_cerrados):
    """
    Retorna: 'bueno' | 'mediano' | 'malo' | 'alerta'
    """
    if segundos_ojos_cerrados >= 2.0:
        return "alerta"
    if mar > MAR_BOSTEZO:
        return "malo"
    if ear >= EAR_BUENO:
        return "bueno"
    if ear >= EAR_MEDIANO:
        return "mediano"
    if segundos_ojos_cerrados >= 1.0:
        return "malo"
    return "mediano"