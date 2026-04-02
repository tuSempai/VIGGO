import cv2
import time
import threading
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Ellipse, Rectangle
from kivy.uix.widget import Widget
from kivy.metrics import dp

from database import registrar_usuario, verificar_login
from detector import detectar_rostro, evaluar_estado, EAR_MALO, EAR_MEDIANO
from alert import lanzar_alerta

Window.size = (400, 750)
Window.clearcolor = (0.04, 0.06, 0.12, 1)

# ── Paleta ────────────────────────────────────────────────────────────────────
C_CARD   = (0.08, 0.11, 0.20, 1)
C_DARK   = (0.05, 0.07, 0.14, 1)
C_CYAN   = (0.00, 0.83, 1.00, 1)
C_GREEN  = (0.10, 0.90, 0.50, 1)
C_YELLOW = (1.00, 0.80, 0.10, 1)
C_ORANGE = (1.00, 0.50, 0.05, 1)
C_RED    = (1.00, 0.22, 0.35, 1)
C_TEXT   = (0.88, 0.92, 1.00, 1)
C_MUTED  = (0.45, 0.52, 0.68, 1)
C_BORDER = (0.14, 0.20, 0.38, 1)

ESTADO_INFO = {
    "bueno":   ("✓",  "Conductor alerta — Todo bien",        C_GREEN),
    "mediano": ("〰", "Fatiga leve — Mantente atento",        C_YELLOW),
    "malo":    ("⚠",  "Fatiga alta — Considera detenerte",   C_ORANGE),
    "alerta":  ("🚨", "¡MICROSUEÑO! — Detente ahora",        C_RED),
}
NIVEL_TEXTO = {
    "bueno":   "● ○ ○ ○  BUENO",
    "mediano": "● ● ○ ○  MEDIANO",
    "malo":    "● ● ● ○  ALTO",
    "alerta":  "● ● ● ●  CRÍTICO",
}


def make_card(widget, r=16, color=C_CARD):
    with widget.canvas.before:
        Color(*color)
        widget._bg_rect = RoundedRectangle(
            pos=widget.pos, size=widget.size, radius=[r])
    widget.bind(
        pos=lambda *a: setattr(widget._bg_rect, 'pos', widget.pos),
        size=lambda *a: setattr(widget._bg_rect, 'size', widget.size))


class StyledInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(
            background_color=(0.10, 0.14, 0.25, 1),
            background_normal='',
            background_active='',
            foreground_color=(0.88, 0.92, 1.00, 1),
            hint_text_color=(0.45, 0.52, 0.68, 1),
            cursor_color=(0.00, 0.83, 1.00, 1),
            padding=[dp(16), dp(14)],
            font_size=dp(15),
            multiline=False,
            **kwargs
        )


class CyanButton(Button):
    def __init__(self, **kwargs):
        super().__init__(
            background_color=(0, 0, 0, 0),
            background_normal='',
            color=(0.04, 0.06, 0.12, 1),
            bold=True,
            **kwargs
        )
        with self.canvas.before:
            Color(*C_CYAN)
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._bg.pos  = self.pos
        self._bg.size = self.size


class GhostButton(Button):
    def __init__(self, **kwargs):
        super().__init__(
            background_color=(0, 0, 0, 0),
            background_normal='',
            color=C_CYAN,
            **kwargs
        )
        with self.canvas.before:
            Color(*C_BORDER)
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._bg.pos  = self.pos
        self._bg.size = self.size


# ─────────────────────────────────────────────
# PANTALLA 1 — LOGIN
# ─────────────────────────────────────────────
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0.00, 0.83, 1.00, 0.04)
            Ellipse(pos=(-100, 400), size=(400, 400))
            Color(0.00, 0.50, 0.85, 0.03)
            Ellipse(pos=(200, -50), size=(300, 300))

        layout = BoxLayout(orientation='vertical', padding=[dp(32), dp(40)],
                           spacing=dp(14), size_hint=(1, 1))

        logo_box = BoxLayout(orientation='vertical',
                             size_hint_y=None, height=dp(130))
        logo_box.add_widget(Label(text='◉', font_size=dp(48), color=C_CYAN,
                                  size_hint_y=None, height=dp(60)))
        logo_box.add_widget(Label(text='VIGGO', font_size=dp(38), bold=True,
                                  color=C_TEXT, size_hint_y=None, height=dp(46)))
        logo_box.add_widget(Label(text='Sistema de Detección de Fatiga',
                                  font_size=dp(12), color=(*C_MUTED[:3], 1),
                                  size_hint_y=None, height=dp(20)))
        layout.add_widget(logo_box)
        layout.add_widget(Widget(size_hint_y=None, height=dp(8)))

        lbl_e = Label(text='CORREO ELECTRÓNICO', font_size=dp(10),
                      color=(*C_CYAN[:3], 0.8), halign='left', bold=True,
                      size_hint=(1, None), height=dp(20))
        lbl_e.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        self.email_input = StyledInput(hint_text='usuario@correo.com',
                                       size_hint_y=None, height=dp(48))

        lbl_p = Label(text='CONTRASEÑA', font_size=dp(10),
                      color=(*C_CYAN[:3], 0.8), halign='left', bold=True,
                      size_hint=(1, None), height=dp(20))
        lbl_p.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        self.pass_input = StyledInput(hint_text='••••••••', password=True,
                                      size_hint_y=None, height=dp(48))

        layout.add_widget(lbl_e)
        layout.add_widget(self.email_input)
        layout.add_widget(lbl_p)
        layout.add_widget(self.pass_input)

        self.msg = Label(text='', font_size=dp(12), color=C_RED,
                         size_hint_y=None, height=dp(24))
        layout.add_widget(self.msg)

        btn_login = CyanButton(text='INICIAR SESIÓN', font_size=dp(15),
                               size_hint_y=None, height=dp(52))
        btn_login.bind(on_press=self.hacer_login)
        layout.add_widget(btn_login)

        btn_reg = GhostButton(text='¿No tienes cuenta?  Regístrate →',
                              font_size=dp(13), size_hint_y=None, height=dp(44))
        btn_reg.bind(on_press=lambda *a: setattr(
            self.manager, 'current', 'registro'))
        layout.add_widget(btn_reg)

        layout.add_widget(Widget())
        self.add_widget(layout)

    def hacer_login(self, *args):
        email    = self.email_input.text.strip()
        password = self.pass_input.text.strip()
        if not email or not password:
            self.msg.text = '⚠  Completa todos los campos'
            return
        nombre = verificar_login(email, password)
        if nombre:
            camara = self.manager.get_screen('camara')
            camara.nombre_usuario   = nombre
            camara.lbl_usuario.text = nombre
            self.manager.current = 'camara'
        else:
            self.msg.text = '✕  Correo o contraseña incorrectos'


# ─────────────────────────────────────────────
# PANTALLA 2 — REGISTRO
# ─────────────────────────────────────────────
class RegistroScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=[dp(32), dp(40)],
                           spacing=dp(14))

        layout.add_widget(Label(text='Crear Cuenta', font_size=dp(30), bold=True,
                                color=C_TEXT, size_hint_y=None, height=dp(44)))
        layout.add_widget(Label(text='Únete a VIGGO y conduce seguro',
                                font_size=dp(12), color=(*C_MUTED[:3], 1),
                                size_hint_y=None, height=dp(20)))
        layout.add_widget(Widget(size_hint_y=None, height=dp(8)))

        fields = [
            ('NOMBRE COMPLETO',    'nombre_input', 'Tu nombre completo', False),
            ('CORREO ELECTRÓNICO', 'email_input',  'usuario@correo.com', False),
            ('CONTRASEÑA',         'pass_input',   '••••••••',           True),
        ]
        for label_text, attr, hint, pwd in fields:
            lbl = Label(text=label_text, font_size=dp(10),
                        color=(*C_CYAN[:3], 0.8), halign='left', bold=True,
                        size_hint=(1, None), height=dp(20))
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            inp = StyledInput(hint_text=hint, password=pwd,
                              size_hint_y=None, height=dp(48))
            setattr(self, attr, inp)
            layout.add_widget(lbl)
            layout.add_widget(inp)

        self.msg = Label(text='', font_size=dp(12), color=C_GREEN,
                         size_hint_y=None, height=dp(24))
        layout.add_widget(self.msg)

        btn_crear = CyanButton(text='CREAR CUENTA', font_size=dp(15),
                               size_hint_y=None, height=dp(52))
        btn_crear.bind(on_press=self.hacer_registro)
        layout.add_widget(btn_crear)

        btn_volver = GhostButton(text='← Volver al inicio de sesión',
                                 font_size=dp(13), size_hint_y=None, height=dp(44))
        btn_volver.bind(
            on_press=lambda *a: setattr(self.manager, 'current', 'login'))
        layout.add_widget(btn_volver)

        layout.add_widget(Widget())
        self.add_widget(layout)

    def hacer_registro(self, *args):
        nombre   = self.nombre_input.text.strip()
        email    = self.email_input.text.strip()
        password = self.pass_input.text.strip()
        if not nombre or not email or not password:
            self.msg.color = C_RED
            self.msg.text  = '⚠  Completa todos los campos'
            return
        resultado = registrar_usuario(nombre, email, password)
        if resultado == 'ok':
            self.msg.color = C_GREEN
            self.msg.text  = '✓  Cuenta creada — Inicia sesión'
        else:
            self.msg.color = C_RED
            self.msg.text  = '✕  Ese correo ya está registrado'


# ─────────────────────────────────────────────
# PANTALLA 3 — CÁMARA Y DETECCIÓN (rediseñada)
# ─────────────────────────────────────────────
class CamaraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nombre_usuario       = ''
        self.cap                  = None
        self.activo               = False
        self.tiempo_ojos_cerrados = 0
        self.ultima_alerta        = 0

        # Layout principal sin padding superior para que cámara llegue al borde
        layout = BoxLayout(
            orientation='vertical',
            spacing=dp(0),
            padding=[dp(0), dp(0), dp(0), dp(0)]
        )

        # ── ZONA CÁMARA (FloatLayout con HUD superpuesto) ────────────────────
        # Ocupa ~58% de la pantalla = ~435px
        cam_section = FloatLayout(size_hint=(1, None), height=dp(435))

        # Fondo oscuro para el área de cámara
        with cam_section.canvas.before:
            Color(*C_DARK)
            self._cam_bg_rect = Rectangle(
                pos=cam_section.pos, size=cam_section.size)
        cam_section.bind(
            pos=lambda w, v: setattr(self._cam_bg_rect, 'pos', w.pos),
            size=lambda w, v: setattr(self._cam_bg_rect, 'size', w.size))

        # Feed de video (ocupa toda la sección)
        self.img_camara = KivyImage(
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            allow_stretch=True,
            keep_ratio=True
        )
        cam_section.add_widget(self.img_camara)

        # Placeholder cuando cámara está apagada
        self.lbl_cam_off = Label(
            text='[ CÁMARA DESACTIVADA ]',
            font_size=dp(13),
            color=(*C_MUTED[:3], 0.35),
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        cam_section.add_widget(self.lbl_cam_off)

        # ── HUD superior: barra de título superpuesta a la cámara ────────────
        hud_top = BoxLayout(
            size_hint=(1, None),
            height=dp(52),
            pos_hint={'x': 0, 'top': 1},
            padding=[dp(16), dp(8)],
            spacing=dp(8)
        )
        with hud_top.canvas.before:
            Color(0.02, 0.04, 0.10, 0.78)
            self._hud_bg = Rectangle(pos=hud_top.pos, size=hud_top.size)
        hud_top.bind(
            pos=lambda w, v: setattr(self._hud_bg, 'pos', w.pos),
            size=lambda w, v: setattr(self._hud_bg, 'size', w.size))

        hud_logo = Label(
            text='◉  VIGGO',
            font_size=dp(17),
            bold=True,
            color=C_CYAN,
            size_hint_x=0.45,
            halign='left'
        )
        hud_logo.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        # Nombre usuario a la derecha
        self.lbl_usuario = Label(
            text='Usuario',
            font_size=dp(13),
            color=(*C_TEXT[:3], 0.85),
            size_hint_x=0.55,
            halign='right'
        )
        self.lbl_usuario.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        hud_top.add_widget(hud_logo)
        hud_top.add_widget(self.lbl_usuario)
        cam_section.add_widget(hud_top)

        # ── HUD inferior: badge de estado superpuesto en la cámara ──────────
        hud_bottom = BoxLayout(
            size_hint=(1, None),
            height=dp(46),
            pos_hint={'x': 0, 'y': 0},
            padding=[dp(16), dp(8)],
            spacing=dp(10)
        )
        with hud_bottom.canvas.before:
            Color(0.02, 0.04, 0.10, 0.80)
            self._hud_bot_bg = Rectangle(
                pos=hud_bottom.pos, size=hud_bottom.size)
        hud_bottom.bind(
            pos=lambda w, v: setattr(self._hud_bot_bg, 'pos', w.pos),
            size=lambda w, v: setattr(self._hud_bot_bg, 'size', w.size))

        self.hud_dot = Label(
            text='●',
            font_size=dp(14),
            color=(*C_MUTED[:3], 0.4),
            size_hint_x=None,
            width=dp(20)
        )
        self.hud_estado = Label(
            text='Presiona INICIAR para comenzar',
            font_size=dp(12),
            color=(*C_MUTED[:3], 0.8),
            halign='left',
            bold=True
        )
        self.hud_estado.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        self.hud_nivel = Label(
            text='',
            font_size=dp(11),
            color=(*C_MUTED[:3], 0.7),
            size_hint_x=None,
            width=dp(110),
            halign='right'
        )
        self.hud_nivel.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        hud_bottom.add_widget(self.hud_dot)
        hud_bottom.add_widget(self.hud_estado)
        hud_bottom.add_widget(self.hud_nivel)
        cam_section.add_widget(hud_bottom)

        layout.add_widget(cam_section)

        # ── PANEL INFERIOR (fondo oscuro, todo pegado) ───────────────────────
        bottom_panel = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            padding=[dp(12), dp(10), dp(12), dp(14)],
            spacing=dp(10)
        )
        with bottom_panel.canvas.before:
            Color(*C_DARK)
            self._panel_bg = Rectangle(
                pos=bottom_panel.pos, size=bottom_panel.size)
        bottom_panel.bind(
            pos=lambda w, v: setattr(self._panel_bg, 'pos', w.pos),
            size=lambda w, v: setattr(self._panel_bg, 'size', w.size))

        # ── Fila métricas EAR + MAR ──────────────────────────────────────────
        metricas = BoxLayout(
            size_hint=(1, None),
            height=dp(80),
            spacing=dp(10)
        )

        for title, subtitle, attr_val, attr_sub in [
            ('EAR', 'Apertura de ojos', 'lbl_ear', 'lbl_ear_sub'),
            ('MAR', 'Apertura de boca', 'lbl_mar', 'lbl_mar_sub'),
        ]:
            card = BoxLayout(
                orientation='vertical',
                padding=[dp(14), dp(8)]
            )
            make_card(card, r=14, color=C_CARD)

            row = BoxLayout(size_hint_y=None, height=dp(32))
            lbl_title = Label(
                text=title,
                font_size=dp(10),
                color=(*C_CYAN[:3], 0.6),
                bold=True,
                size_hint_x=None,
                width=dp(36),
                halign='left'
            )
            lbl_title.bind(
                size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            val = Label(
                text='—',
                font_size=dp(24),
                bold=True,
                color=C_TEXT,
                halign='right'
            )
            val.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            setattr(self, attr_val, val)
            row.add_widget(lbl_title)
            row.add_widget(val)
            card.add_widget(row)

            sub = Label(
                text=subtitle,
                font_size=dp(10),
                color=(*C_MUTED[:3], 0.7),
                halign='left',
                size_hint_y=None,
                height=dp(18)
            )
            sub.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            setattr(self, attr_sub, sub)
            card.add_widget(sub)

            metricas.add_widget(card)

        bottom_panel.add_widget(metricas)

        # ── Separador sutil ───────────────────────────────────────────────────
        sep = Widget(size_hint_y=None, height=dp(1))
        with sep.canvas:
            Color(*C_BORDER)
            self._sep_rect = Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(
            pos=lambda w, v: setattr(self._sep_rect, 'pos', w.pos),
            size=lambda w, v: setattr(self._sep_rect, 'size', w.size))
        bottom_panel.add_widget(sep)

        # ── Botones principales ───────────────────────────────────────────────
        botones = BoxLayout(
            size_hint=(1, None),
            height=dp(54),
            spacing=dp(10)
        )

        self.btn_camara = CyanButton(
            text='▶  INICIAR DETECCIÓN',
            font_size=dp(14)
        )
        self.btn_camara.bind(on_press=self.toggle_camara)

        btn_salir = GhostButton(
            text='⏏  Salir',
            font_size=dp(13),
            size_hint_x=None,
            width=dp(100)
        )
        btn_salir.bind(on_press=self.cerrar_sesion)

        botones.add_widget(self.btn_camara)
        botones.add_widget(btn_salir)
        bottom_panel.add_widget(botones)

        layout.add_widget(bottom_panel)
        self.add_widget(layout)

    # ── Helpers de color para botón principal ──────────────────────────────
    def _set_btn_color(self, color):
        self.btn_camara.canvas.before.clear()
        with self.btn_camara.canvas.before:
            Color(*color)
            self.btn_camara._bg = RoundedRectangle(
                pos=self.btn_camara.pos,
                size=self.btn_camara.size,
                radius=[dp(12)])
        self.btn_camara.bind(
            pos=self.btn_camara._upd,
            size=self.btn_camara._upd)

    def toggle_camara(self, *args):
        if not self.activo:
            self.iniciar_camara()
        else:
            self.detener_camara()

    def iniciar_camara(self):
        self.cap    = cv2.VideoCapture(0)
        self.activo = True
        self.lbl_cam_off.opacity = 0
        self.btn_camara.text = '⏹  DETENER DETECCIÓN'
        self._set_btn_color(C_RED)
        Clock.schedule_interval(self.actualizar_frame, 1.0 / 20)

    def detener_camara(self):
        self.activo = False
        Clock.unschedule(self.actualizar_frame)
        if self.cap:
            self.cap.release()
        self.lbl_cam_off.opacity  = 1
        self.btn_camara.text      = '▶  INICIAR DETECCIÓN'
        self._set_btn_color(C_CYAN)

        # Resetear HUD
        self.hud_estado.text  = 'Presiona INICIAR para comenzar'
        self.hud_estado.color = (*C_MUTED[:3], 0.8)
        self.hud_dot.color    = (*C_MUTED[:3], 0.4)
        self.hud_nivel.text   = ''

        # Resetear métricas
        self.lbl_ear.text  = '—'
        self.lbl_mar.text  = '—'
        self.lbl_ear.color = C_TEXT
        self.lbl_mar.color = C_TEXT

        self.tiempo_ojos_cerrados = 0

    def actualizar_frame(self, dt):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        ear, mar, frame = detectar_rostro(frame)

        # Tiempo con ojos muy cerrados
        if ear < EAR_MALO:
            if self.tiempo_ojos_cerrados == 0:
                self.tiempo_ojos_cerrados = time.time()
            segundos = time.time() - self.tiempo_ojos_cerrados
        else:
            self.tiempo_ojos_cerrados = 0
            segundos = 0

        estado = evaluar_estado(ear, mar, segundos)

        # Actualizar métricas
        self.lbl_ear.text = f'{ear:.3f}'
        self.lbl_mar.text = f'{mar:.3f}'

        # Alertas sonoras
        ahora = time.time()
        if estado == "alerta" and (ahora - self.ultima_alerta) > 3:
            self.ultima_alerta = ahora
            threading.Thread(
                target=lanzar_alerta, args=("alerta",), daemon=True).start()
        elif estado == "malo" and (ahora - self.ultima_alerta) > 5:
            self.ultima_alerta = ahora
            threading.Thread(
                target=lanzar_alerta, args=("precaucion",), daemon=True).start()

        # Actualizar HUD superpuesto
        emoji, texto, color = ESTADO_INFO[estado]
        self.hud_estado.text  = f'{emoji}  {texto}'
        self.hud_estado.color = color
        self.hud_dot.color    = color
        self.hud_nivel.text   = NIVEL_TEXTO[estado]
        self.hud_nivel.color  = color

        # Color en métricas
        self.lbl_ear.color = color if estado != "bueno" else C_TEXT
        self.lbl_mar.color = color if estado == "malo" or estado == "alerta" else C_TEXT

        # Frame → textura Kivy
        frame_flip = cv2.flip(frame, 0)
        buf        = frame_flip.tobytes()
        texture    = Texture.create(
            size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
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
        self.title = 'VIGGO — Detección de Fatiga'
        sm = ScreenManager(transition=FadeTransition(duration=0.2))
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegistroScreen(name='registro'))
        sm.add_widget(CamaraScreen(name='camara'))
        return sm

    def on_stop(self):
        camara = self.root.get_screen('camara')
        if camara.cap:
            camara.cap.release()


if __name__ == '__main__':
    ViggoApp().run()