import cv2
import time
import threading
import mediapipe as mp
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.core.window import Window

from database import registrar_usuario, verificar_login
from detector import calcular_EAR, calcular_MAR, evaluar_estado, OJO_IZQ, OJO_DER, UMBRAL_EAR, UMBRAL_MAR
from alert import lanzar_alerta

# Tamaño de ventana (simula pantalla de celular)
Window.size = (400, 700)
Window.clearcolor = (0.08, 0.08, 0.12, 1)

# ─────────────────────────────────────────────
# PANTALLA 1 — LOGIN
# ─────────────────────────────────────────────
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=40, spacing=15)

        layout.add_widget(Label(text='🚗 VIGGO', font_size=42,
                                color=(0.2, 0.8, 1, 1), size_hint_y=0.2))
        layout.add_widget(Label(text='Sistema de Detección de Fatiga',
                                font_size=14, color=(0.7, 0.7, 0.7, 1),
                                size_hint_y=0.08))

        self.email_input = TextInput(hint_text='Correo electrónico',
                                     multiline=False, size_hint_y=0.1,
                                     background_color=(0.15, 0.15, 0.2, 1),
                                     foreground_color=(1, 1, 1, 1))
        self.pass_input = TextInput(hint_text='Contraseña', password=True,
                                    multiline=False, size_hint_y=0.1,
                                    background_color=(0.15, 0.15, 0.2, 1),
                                    foreground_color=(1, 1, 1, 1))

        btn_login = Button(text='INICIAR SESIÓN', size_hint_y=0.1,
                           background_color=(0.2, 0.6, 1, 1))
        btn_login.bind(on_press=self.hacer_login)

        btn_registro = Button(text='¿No tienes cuenta? Regístrate',
                              size_hint_y=0.08,
                              background_color=(0.1, 0.1, 0.15, 1))
        btn_registro.bind(on_press=self.ir_registro)

        self.msg = Label(text='', color=(1, 0.3, 0.3, 1), size_hint_y=0.08)

        layout.add_widget(self.email_input)
        layout.add_widget(self.pass_input)
        layout.add_widget(btn_login)
        layout.add_widget(btn_registro)
        layout.add_widget(self.msg)
        self.add_widget(layout)

    def hacer_login(self, *args):
        email = self.email_input.text.strip()
        password = self.pass_input.text.strip()

        if not email or not password:
            self.msg.text = '⚠️ Completa todos los campos'
            return

        nombre = verificar_login(email, password)
        if nombre:
            camara = self.manager.get_screen('camara')
            camara.nombre_usuario = nombre
            camara.lbl_usuario.text = f'👤 Bienvenido, {nombre}'
            self.manager.current = 'camara'
        else:
            self.msg.text = '❌ Correo o contraseña incorrectos'

    def ir_registro(self, *args):
        self.manager.current = 'registro'


# ─────────────────────────────────────────────
# PANTALLA 2 — REGISTRO
# ─────────────────────────────────────────────
class RegistroScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=40, spacing=15)

        layout.add_widget(Label(text='Crear Cuenta', font_size=32,
                                color=(0.2, 0.8, 1, 1), size_hint_y=0.15))

        self.nombre_input = TextInput(hint_text='Nombre completo',
                                      multiline=False, size_hint_y=0.1,
                                      background_color=(0.15, 0.15, 0.2, 1),
                                      foreground_color=(1, 1, 1, 1))
        self.email_input = TextInput(hint_text='Correo electrónico',
                                     multiline=False, size_hint_y=0.1,
                                     background_color=(0.15, 0.15, 0.2, 1),
                                     foreground_color=(1, 1, 1, 1))
        self.pass_input = TextInput(hint_text='Contraseña', password=True,
                                    multiline=False, size_hint_y=0.1,
                                    background_color=(0.15, 0.15, 0.2, 1),
                                    foreground_color=(1, 1, 1, 1))

        btn_registrar = Button(text='CREAR CUENTA', size_hint_y=0.1,
                               background_color=(0.2, 0.8, 0.4, 1))
        btn_registrar.bind(on_press=self.hacer_registro)

        btn_volver = Button(text='← Volver al login', size_hint_y=0.08,
                            background_color=(0.1, 0.1, 0.15, 1))
        btn_volver.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))

        self.msg = Label(text='', color=(0.3, 1, 0.5, 1), size_hint_y=0.08)

        layout.add_widget(self.nombre_input)
        layout.add_widget(self.email_input)
        layout.add_widget(self.pass_input)
        layout.add_widget(btn_registrar)
        layout.add_widget(btn_volver)
        layout.add_widget(self.msg)
        self.add_widget(layout)

    def hacer_registro(self, *args):
        nombre = self.nombre_input.text.strip()
        email = self.email_input.text.strip()
        password = self.pass_input.text.strip()

        if not nombre or not email or not password:
            self.msg.color = (1, 0.3, 0.3, 1)
            self.msg.text = '⚠️ Completa todos los campos'
            return

        resultado = registrar_usuario(nombre, email, password)
        if resultado == 'ok':
            self.msg.color = (0.3, 1, 0.5, 1)
            self.msg.text = '✅ Cuenta creada. Inicia sesión'
        else:
            self.msg.color = (1, 0.3, 0.3, 1)
            self.msg.text = '❌ Ese correo ya está registrado'


# ─────────────────────────────────────────────
# PANTALLA 3 — CÁMARA Y DETECCIÓN
# ─────────────────────────────────────────────
class CamaraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nombre_usuario = ''
        self.cap = None
        self.activo = False
        self.tiempo_ojos_cerrados = 0
        self.ultima_alerta = 0
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        layout = BoxLayout(orientation='vertical', padding=10, spacing=8)

        self.lbl_usuario = Label(text='👤 Usuario', font_size=16,
                                  color=(0.2, 0.8, 1, 1), size_hint_y=0.06)

        # Imagen de la cámara
        self.img_camara = KivyImage(size_hint_y=0.55)

        # Estado del conductor
        self.lbl_estado = Label(text='Estado: ESPERANDO...', font_size=18,
                                 color=(1, 1, 1, 1), size_hint_y=0.08)

        # Valores EAR y MAR en tiempo real
        self.lbl_ear = Label(text='EAR: --', font_size=13,
                              color=(0.7, 0.7, 0.7, 1), size_hint_y=0.05)
        self.lbl_mar = Label(text='MAR: --', font_size=13,
                              color=(0.7, 0.7, 0.7, 1), size_hint_y=0.05)

        # Botones
        botones = BoxLayout(size_hint_y=0.12, spacing=10)
        self.btn_camara = Button(text='▶ INICIAR', font_size=16,
                                  background_color=(0.2, 0.7, 0.3, 1))
        self.btn_camara.bind(on_press=self.toggle_camara)

        btn_salir = Button(text='⏏ Salir', font_size=14,
                           background_color=(0.5, 0.1, 0.1, 1))
        btn_salir.bind(on_press=self.cerrar_sesion)

        botones.add_widget(self.btn_camara)
        botones.add_widget(btn_salir)

        layout.add_widget(self.lbl_usuario)
        layout.add_widget(self.img_camara)
        layout.add_widget(self.lbl_estado)
        layout.add_widget(self.lbl_ear)
        layout.add_widget(self.lbl_mar)
        layout.add_widget(botones)
        self.add_widget(layout)

    def toggle_camara(self, *args):
        if not self.activo:
            self.iniciar_camara()
        else:
            self.detener_camara()

    def iniciar_camara(self):
        self.cap = cv2.VideoCapture(0)
        self.activo = True
        self.btn_camara.text = '⏹ DETENER'
        self.btn_camara.background_color = (0.8, 0.2, 0.2, 1)
        Clock.schedule_interval(self.actualizar_frame, 1.0 / 20)

    def detener_camara(self):
        self.activo = False
        Clock.unschedule(self.actualizar_frame)
        if self.cap:
            self.cap.release()
        self.btn_camara.text = '▶ INICIAR'
        self.btn_camara.background_color = (0.2, 0.7, 0.3, 1)
        self.lbl_estado.text = 'Estado: DETENIDO'
        self.lbl_estado.color = (1, 1, 1, 1)

    def actualizar_frame(self, dt):
        if not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado = self.face_mesh.process(rgb)

        estado = "normal"

        if resultado.multi_face_landmarks:
            lm = resultado.multi_face_landmarks[0].landmark

            ear_izq = calcular_EAR(lm, OJO_IZQ, w, h)
            ear_der = calcular_EAR(lm, OJO_DER, w, h)
            ear     = (ear_izq + ear_der) / 2
            mar     = calcular_MAR(lm, w, h)

            # Contar tiempo con ojos cerrados
            if ear < UMBRAL_EAR:
                if self.tiempo_ojos_cerrados == 0:
                    self.tiempo_ojos_cerrados = time.time()
                segundos = time.time() - self.tiempo_ojos_cerrados
            else:
                self.tiempo_ojos_cerrados = 0
                segundos = 0

            estado = evaluar_estado(ear, mar, segundos)

            self.lbl_ear.text = f'EAR: {ear:.3f}  (umbral < {UMBRAL_EAR})'
            self.lbl_mar.text = f'MAR: {mar:.3f}  (umbral > {UMBRAL_MAR})'

            # Lanzar alerta cada 3 segundos máximo para no saturar
            ahora = time.time()
            if estado != "normal" and (ahora - self.ultima_alerta) > 3:
                self.ultima_alerta = ahora
                threading.Thread(
                    target=lanzar_alerta,
                    args=(estado,),
                    daemon=True
                ).start()
        else:
            self.lbl_ear.text = 'EAR: -- (sin rostro)'
            self.lbl_mar.text = 'MAR: -- (sin rostro)'

        # Actualizar color del estado en pantalla
        if estado == "alerta":
            self.lbl_estado.text = '🚨 ALERTA — MICROSUEÑO DETECTADO'
            self.lbl_estado.color = (1, 0.2, 0.2, 1)
        elif estado == "precaucion":
            self.lbl_estado.text = '⚠️ PRECAUCIÓN — Bostezo detectado'
            self.lbl_estado.color = (1, 0.8, 0.1, 1)
        else:
            self.lbl_estado.text = '✅ NORMAL — Conductor alerta'
            self.lbl_estado.color = (0.2, 1, 0.4, 1)

        # Mostrar video en la interfaz
        frame_flip = cv2.flip(frame, 0)
        buf = frame_flip.tobytes()
        texture = Texture.create(size=(w, h), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.img_camara.texture = texture

    def cerrar_sesion(self, *args):
        self.detener_camara()
        self.manager.current = 'login'


# ─────────────────────────────────────────────
# APP PRINCIPAL
# ─────────────────────────────────────────────
class ViggoApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegistroScreen(name='registro'))
        sm.add_widget(CamaraScreen(name='camara'))
        return sm

    def on_stop(self):
        # Liberar cámara al cerrar la app
        camara = self.root.get_screen('camara')
        if camara.cap:
            camara.cap.release()


if __name__ == '__main__':
    ViggoApp().run()