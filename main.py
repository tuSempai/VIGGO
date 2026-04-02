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
from kivy.graphics import Color, RoundedRectangle, Ellipse, Rectangle, Line
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.animation import Animation

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
    "bueno":   ("✓",  "Conductor alerta — Todo bien",       C_GREEN),
    "mediano": ("〰", "Fatiga leve — Mantente atento",       C_YELLOW),
    "malo":    ("⚠",  "Fatiga alta — Considera detenerte",  C_ORANGE),
    "alerta":  ("🚨", "¡MICROSUEÑO! — Detente ahora",       C_RED),
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
            bold=True, **kwargs
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
            color=C_CYAN, **kwargs
        )
        with self.canvas.before:
            Color(*C_BORDER)
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._bg.pos  = self.pos
        self._bg.size = self.size


# ═════════════════════════════════════════════
# SPLASH SCREEN
# ═════════════════════════════════════════════
class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0.00, 0.83, 1.00, 0.06)
            Ellipse(pos=(-80, 380), size=(420, 420))
            Color(0.00, 0.50, 0.85, 0.04)
            Ellipse(pos=(180, -60), size=(320, 320))

        layout = FloatLayout()

        center = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width=dp(280), height=dp(300),
            pos_hint={'center_x': 0.5, 'center_y': 0.54},
            spacing=dp(8)
        )

        self.lbl_icon = Label(
            text='◉', font_size=dp(80),
            color=(*C_CYAN[:3], 0.0),
            size_hint_y=None, height=dp(96), bold=True
        )
        self.lbl_nombre = Label(
            text='VIGGO', font_size=dp(56), bold=True,
            color=(*C_TEXT[:3], 0.0),
            size_hint_y=None, height=dp(70)
        )
        self.lbl_tag = Label(
            text='Detectar el cansancio\nes salvar una vida.',
            font_size=dp(14), color=(*C_MUTED[:3], 0.0),
            size_hint_y=None, height=dp(52),
            halign='center', line_height=1.5
        )
        self.lbl_tag.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        self.lbl_ver = Label(
            text='v1.0  ·  IA Local  ·  Privacidad 100%',
            font_size=dp(10), color=(*C_MUTED[:3], 0.0),
            size_hint_y=None, height=dp(22)
        )

        center.add_widget(self.lbl_icon)
        center.add_widget(self.lbl_nombre)
        center.add_widget(self.lbl_tag)
        center.add_widget(self.lbl_ver)

        self.lbl_cargando = Label(
            text='Iniciando sistema de detección...',
            font_size=dp(11), color=(*C_CYAN[:3], 0.0),
            size_hint=(1, None), height=dp(30),
            pos_hint={'center_x': 0.5, 'y': 0.05}
        )

        layout.add_widget(center)
        layout.add_widget(self.lbl_cargando)
        self.add_widget(layout)

    def on_enter(self):
        t = 0.55
        Animation(color=(*C_CYAN[:3], 1.0),  duration=t).start(self.lbl_icon)
        Clock.schedule_once(lambda dt: Animation(
            color=(*C_TEXT[:3], 1.0), duration=t).start(self.lbl_nombre), 0.25)
        Clock.schedule_once(lambda dt: Animation(
            color=(*C_MUTED[:3], 0.85), duration=t).start(self.lbl_tag), 0.5)
        Clock.schedule_once(lambda dt: Animation(
            color=(*C_MUTED[:3], 0.5), duration=t).start(self.lbl_ver), 0.75)
        Clock.schedule_once(lambda dt: Animation(
            color=(*C_CYAN[:3], 0.65), duration=0.4).start(self.lbl_cargando), 1.0)
        Clock.schedule_once(self._ir_login, 2.8)

    def _ir_login(self, dt):
        self.manager.current = 'login'


# ═════════════════════════════════════════════
# LOGIN
# ═════════════════════════════════════════════
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.00, 0.83, 1.00, 0.04)
            Ellipse(pos=(-100, 400), size=(400, 400))
            Color(0.00, 0.50, 0.85, 0.03)
            Ellipse(pos=(200, -50), size=(300, 300))

        layout = BoxLayout(orientation='vertical',
                           padding=[dp(32), dp(40)],
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

        for lbl_txt, attr, hint, pwd in [
            ('CORREO ELECTRÓNICO', 'email_input', 'usuario@correo.com', False),
            ('CONTRASEÑA',         'pass_input',  '••••••••',           True),
        ]:
            lbl = Label(text=lbl_txt, font_size=dp(10),
                        color=(*C_CYAN[:3], 0.8), halign='left', bold=True,
                        size_hint=(1, None), height=dp(20))
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            inp = StyledInput(hint_text=hint, password=pwd,
                              size_hint_y=None, height=dp(48))
            setattr(self, attr, inp)
            layout.add_widget(lbl)
            layout.add_widget(inp)

        self.msg = Label(text='', font_size=dp(12), color=C_RED,
                         size_hint_y=None, height=dp(24))
        layout.add_widget(self.msg)

        btn = CyanButton(text='INICIAR SESIÓN', font_size=dp(15),
                         size_hint_y=None, height=dp(52))
        btn.bind(on_press=self.hacer_login)
        layout.add_widget(btn)

        btn2 = GhostButton(text='¿No tienes cuenta?  Regístrate →',
                           font_size=dp(13), size_hint_y=None, height=dp(44))
        btn2.bind(on_press=lambda *a: setattr(
            self.manager, 'current', 'registro'))
        layout.add_widget(btn2)
        layout.add_widget(Widget())
        self.add_widget(layout)

    def hacer_login(self, *args):
        email = self.email_input.text.strip()
        pwd   = self.pass_input.text.strip()
        if not email or not pwd:
            self.msg.text = '⚠  Completa todos los campos'
            return
        nombre = verificar_login(email, pwd)
        if nombre:
            c = self.manager.get_screen('camara')
            c.nombre_usuario   = nombre
            c.lbl_usuario.text = nombre
            self.manager.current = 'camara'
        else:
            self.msg.text = '✕  Correo o contraseña incorrectos'


# ═════════════════════════════════════════════
# REGISTRO
# ═════════════════════════════════════════════
class RegistroScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical',
                           padding=[dp(32), dp(40)], spacing=dp(14))
        layout.add_widget(Label(text='Crear Cuenta', font_size=dp(30),
                                bold=True, color=C_TEXT,
                                size_hint_y=None, height=dp(44)))
        layout.add_widget(Label(text='Únete a VIGGO y conduce seguro',
                                font_size=dp(12), color=(*C_MUTED[:3], 1),
                                size_hint_y=None, height=dp(20)))
        layout.add_widget(Widget(size_hint_y=None, height=dp(8)))

        for lbl_txt, attr, hint, pwd in [
            ('NOMBRE COMPLETO',    'nombre_input', 'Tu nombre completo', False),
            ('CORREO ELECTRÓNICO', 'email_input',  'usuario@correo.com', False),
            ('CONTRASEÑA',         'pass_input',   '••••••••',           True),
        ]:
            lbl = Label(text=lbl_txt, font_size=dp(10),
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

        btn = CyanButton(text='CREAR CUENTA', font_size=dp(15),
                         size_hint_y=None, height=dp(52))
        btn.bind(on_press=self.hacer_registro)
        layout.add_widget(btn)

        btn2 = GhostButton(text='← Volver al inicio de sesión',
                           font_size=dp(13), size_hint_y=None, height=dp(44))
        btn2.bind(on_press=lambda *a: setattr(self.manager, 'current', 'login'))
        layout.add_widget(btn2)
        layout.add_widget(Widget())
        self.add_widget(layout)

    def hacer_registro(self, *args):
        nombre = self.nombre_input.text.strip()
        email  = self.email_input.text.strip()
        pwd    = self.pass_input.text.strip()
        if not nombre or not email or not pwd:
            self.msg.color = C_RED
            self.msg.text  = '⚠  Completa todos los campos'
            return
        r = registrar_usuario(nombre, email, pwd)
        if r == 'ok':
            self.msg.color = C_GREEN
            self.msg.text  = '✓  Cuenta creada — Inicia sesión'
        else:
            self.msg.color = C_RED
            self.msg.text  = '✕  Ese correo ya está registrado'


# ═════════════════════════════════════════════
# CÁMARA Y DETECCIÓN
# ═════════════════════════════════════════════
class CamaraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nombre_usuario       = ''
        self.cap                  = None
        self.activo               = False
        self.tiempo_ojos_cerrados = 0
        self.ultima_alerta        = 0
        self.contador_alertas     = 0
        self.contador_bostezos    = 0
        self.tiempo_inicio        = 0
        self._blink_clock         = None
        self._blink_visible       = True
        self._estado_actual       = "bueno"

        layout = BoxLayout(orientation='vertical', spacing=dp(0))

        # ── SECCIÓN CÁMARA ────────────────────────────────────────────────────
        self.cam_section = FloatLayout(size_hint=(1, None), height=dp(420))

        with self.cam_section.canvas.before:
            Color(*C_DARK)
            self._cam_bg = Rectangle(
                pos=self.cam_section.pos, size=self.cam_section.size)
        self.cam_section.bind(
            pos=lambda w, v: setattr(self._cam_bg, 'pos', w.pos),
            size=lambda w, v: setattr(self._cam_bg, 'size', w.size))

        self.img_camara = KivyImage(
            size_hint=(1, 1), pos_hint={'x': 0, 'y': 0},
            allow_stretch=True, keep_ratio=True)
        self.cam_section.add_widget(self.img_camara)

        self.lbl_cam_off = Label(
            text='[ CÁMARA DESACTIVADA ]', font_size=dp(13),
            color=(*C_MUTED[:3], 0.35),
            size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        self.cam_section.add_widget(self.lbl_cam_off)

        # Borde de alerta
        self.borde_widget = Widget(
            size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        self.cam_section.add_widget(self.borde_widget)

        # HUD top
        hud_top = BoxLayout(
            size_hint=(1, None), height=dp(52),
            pos_hint={'x': 0, 'top': 1},
            padding=[dp(16), dp(8)], spacing=dp(8))
        with hud_top.canvas.before:
            Color(0.02, 0.04, 0.10, 0.82)
            self._hud_top_bg = Rectangle(pos=hud_top.pos, size=hud_top.size)
        hud_top.bind(
            pos=lambda w, v: setattr(self._hud_top_bg, 'pos', w.pos),
            size=lambda w, v: setattr(self._hud_top_bg, 'size', w.size))

        lbl_logo = Label(text='◉  VIGGO', font_size=dp(17), bold=True,
                         color=C_CYAN, size_hint_x=0.45, halign='left')
        lbl_logo.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        self.lbl_usuario = Label(
            text='Usuario', font_size=dp(13),
            color=(*C_TEXT[:3], 0.85),
            size_hint_x=0.55, halign='right')
        self.lbl_usuario.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        hud_top.add_widget(lbl_logo)
        hud_top.add_widget(self.lbl_usuario)
        self.cam_section.add_widget(hud_top)

        # HUD bottom
        hud_bot = BoxLayout(
            size_hint=(1, None), height=dp(46),
            pos_hint={'x': 0, 'y': 0},
            padding=[dp(16), dp(8)], spacing=dp(10))
        with hud_bot.canvas.before:
            Color(0.02, 0.04, 0.10, 0.82)
            self._hud_bot_bg = Rectangle(pos=hud_bot.pos, size=hud_bot.size)
        hud_bot.bind(
            pos=lambda w, v: setattr(self._hud_bot_bg, 'pos', w.pos),
            size=lambda w, v: setattr(self._hud_bot_bg, 'size', w.size))

        self.hud_dot = Label(text='●', font_size=dp(14),
                             color=(*C_MUTED[:3], 0.4),
                             size_hint_x=None, width=dp(20))
        self.hud_estado = Label(
            text='Presiona INICIAR para comenzar',
            font_size=dp(12), color=(*C_MUTED[:3], 0.8),
            halign='left', bold=True)
        self.hud_estado.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        self.hud_nivel = Label(
            text='', font_size=dp(11), color=(*C_MUTED[:3], 0.7),
            size_hint_x=None, width=dp(110), halign='right')
        self.hud_nivel.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        hud_bot.add_widget(self.hud_dot)
        hud_bot.add_widget(self.hud_estado)
        hud_bot.add_widget(self.hud_nivel)
        self.cam_section.add_widget(hud_bot)
        layout.add_widget(self.cam_section)

        # ── PANEL INFERIOR ────────────────────────────────────────────────────
        panel = BoxLayout(
            orientation='vertical', size_hint=(1, 1),
            padding=[dp(12), dp(10), dp(12), dp(14)], spacing=dp(10))
        with panel.canvas.before:
            Color(*C_DARK)
            self._panel_bg = Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(
            pos=lambda w, v: setattr(self._panel_bg, 'pos', w.pos),
            size=lambda w, v: setattr(self._panel_bg, 'size', w.size))

        # Métricas EAR + MAR
        metricas = BoxLayout(size_hint=(1, None), height=dp(76), spacing=dp(10))
        for title, subtitle, attr in [
            ('EAR', 'Apertura de ojos', 'lbl_ear'),
            ('MAR', 'Apertura de boca', 'lbl_mar'),
        ]:
            card = BoxLayout(orientation='vertical', padding=[dp(14), dp(8)])
            make_card(card, r=14)
            row = BoxLayout(size_hint_y=None, height=dp(32))
            t = Label(text=title, font_size=dp(10),
                      color=(*C_CYAN[:3], 0.6), bold=True,
                      size_hint_x=None, width=dp(36), halign='left')
            t.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            v = Label(text='—', font_size=dp(22), bold=True,
                      color=C_TEXT, halign='right')
            v.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            setattr(self, attr, v)
            row.add_widget(t); row.add_widget(v)
            card.add_widget(row)
            s = Label(text=subtitle, font_size=dp(10),
                      color=(*C_MUTED[:3], 0.7), halign='left',
                      size_hint_y=None, height=dp(16))
            s.bind(size=lambda w, sz: setattr(w, 'text_size', (sz[0], None)))
            card.add_widget(s)
            metricas.add_widget(card)
        panel.add_widget(metricas)

        # ── Contadores: Microsueños | Bostezos | Sesión ───────────────────────
        contadores = BoxLayout(size_hint=(1, None), height=dp(58), spacing=dp(10))

        datos = [
            ('🚨', 'MICROSUEÑOS', 'lbl_cnt_alertas',  C_RED,
             (0.14, 0.05, 0.07, 1)),
            ('😮', 'BOSTEZOS',    'lbl_cnt_bostezos', C_YELLOW,
             (0.14, 0.12, 0.04, 1)),
            ('⏱',  'SESIÓN',      'lbl_duracion',     C_GREEN,
             (0.05, 0.13, 0.07, 1)),
        ]
        for emoji, titulo, attr, color, bg in datos:
            card = BoxLayout(orientation='vertical', padding=[dp(10), dp(6)])
            make_card(card, r=12, color=bg)
            hdr = Label(
                text=f'{emoji} {titulo}', font_size=dp(9),
                color=(*color[:3], 0.75), bold=True,
                size_hint_y=None, height=dp(18), halign='left')
            hdr.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            val = Label(
                text='0' if attr != 'lbl_duracion' else '00:00',
                font_size=dp(20), bold=True, color=color, halign='left')
            val.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            setattr(self, attr, val)
            card.add_widget(hdr)
            card.add_widget(val)
            contadores.add_widget(card)
        panel.add_widget(contadores)

        # Separador
        sep = Widget(size_hint_y=None, height=dp(1))
        with sep.canvas:
            Color(*C_BORDER)
            self._sep = Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(
            pos=lambda w, v: setattr(self._sep, 'pos', w.pos),
            size=lambda w, v: setattr(self._sep, 'size', w.size))
        panel.add_widget(sep)

        # Botones
        botones = BoxLayout(size_hint=(1, None), height=dp(52), spacing=dp(10))
        self.btn_camara = CyanButton(
            text='▶  INICIAR DETECCIÓN', font_size=dp(14))
        self.btn_camara.bind(on_press=self.toggle_camara)
        btn_salir = GhostButton(
            text='⏏  Salir', font_size=dp(13),
            size_hint_x=None, width=dp(100))
        btn_salir.bind(on_press=self.cerrar_sesion)
        botones.add_widget(self.btn_camara)
        botones.add_widget(btn_salir)
        panel.add_widget(botones)

        layout.add_widget(panel)
        self.add_widget(layout)

    # ── Borde parpadeante ─────────────────────────────────────────────────────
    def _draw_border(self, visible, color):
        self.borde_widget.canvas.clear()
        if not visible:
            return
        with self.borde_widget.canvas:
            Color(*color[:3], 0.9)
            Line(
                rectangle=(
                    self.borde_widget.x, self.borde_widget.y,
                    self.borde_widget.width, self.borde_widget.height),
                width=dp(5))

    def _tick_blink(self, dt):
        self._blink_visible = not self._blink_visible
        self._draw_border(self._blink_visible, C_RED)

    def _start_blink(self):
        if self._blink_clock is None:
            self._blink_clock = Clock.schedule_interval(self._tick_blink, 0.30)

    def _stop_blink(self):
        if self._blink_clock:
            Clock.unschedule(self._blink_clock)
            self._blink_clock   = None
            self._blink_visible = True
        self._draw_border(False, C_RED)

    # ── Color botón ───────────────────────────────────────────────────────────
    def _set_btn_color(self, color):
        self.btn_camara.canvas.before.clear()
        with self.btn_camara.canvas.before:
            Color(*color)
            self.btn_camara._bg = RoundedRectangle(
                pos=self.btn_camara.pos, size=self.btn_camara.size,
                radius=[dp(12)])
        self.btn_camara.bind(
            pos=self.btn_camara._upd, size=self.btn_camara._upd)

    # ── Control cámara ────────────────────────────────────────────────────────
    def toggle_camara(self, *args):
        self.iniciar_camara() if not self.activo else self.detener_camara()

    def iniciar_camara(self):
        self.cap    = cv2.VideoCapture(0)
        self.activo = True
        self.lbl_cam_off.opacity = 0
        self.btn_camara.text     = '⏹  DETENER DETECCIÓN'
        self._set_btn_color(C_RED)
        self.contador_alertas   = 0
        self.contador_bostezos  = 0
        self.tiempo_inicio      = time.time()
        self.lbl_cnt_alertas.text  = '0'
        self.lbl_cnt_bostezos.text = '0'
        self.lbl_duracion.text     = '00:00'
        Clock.schedule_interval(self.actualizar_frame, 1.0 / 20)

    def detener_camara(self):
        self.activo = False
        self._stop_blink()
        self._estado_actual = "bueno"
        Clock.unschedule(self.actualizar_frame)
        if self.cap:
            self.cap.release()
        self.lbl_cam_off.opacity  = 1
        self.btn_camara.text      = '▶  INICIAR DETECCIÓN'
        self._set_btn_color(C_CYAN)
        self.hud_estado.text      = 'Presiona INICIAR para comenzar'
        self.hud_estado.color     = (*C_MUTED[:3], 0.8)
        self.hud_dot.color        = (*C_MUTED[:3], 0.4)
        self.hud_nivel.text       = ''
        self.lbl_ear.text         = '—'
        self.lbl_mar.text         = '—'
        self.lbl_ear.color        = C_TEXT
        self.lbl_mar.color        = C_TEXT
        self.tiempo_ojos_cerrados = 0

    # ── Loop de detección ─────────────────────────────────────────────────────
    def actualizar_frame(self, dt):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        ear, mar, frame = detectar_rostro(frame)

        if ear < EAR_MALO:
            if self.tiempo_ojos_cerrados == 0:
                self.tiempo_ojos_cerrados = time.time()
            segundos = time.time() - self.tiempo_ojos_cerrados
        else:
            self.tiempo_ojos_cerrados = 0
            segundos = 0

        estado = evaluar_estado(ear, mar, segundos)
        self._estado_actual = estado

        self.lbl_ear.text = f'{ear:.3f}'
        self.lbl_mar.text = f'{mar:.3f}'

        # Duración sesión
        if self.tiempo_inicio > 0:
            e = int(time.time() - self.tiempo_inicio)
            self.lbl_duracion.text = f'{e//60:02d}:{e%60:02d}'

        # Alertas + contadores
        ahora = time.time()
        if estado == "alerta" and (ahora - self.ultima_alerta) > 3:
            self.ultima_alerta = ahora
            self.contador_alertas += 1
            self.lbl_cnt_alertas.text = str(self.contador_alertas)
            threading.Thread(
                target=lanzar_alerta, args=("alerta",), daemon=True).start()
        elif estado == "malo" and (ahora - self.ultima_alerta) > 5:
            self.ultima_alerta = ahora
            self.contador_bostezos += 1
            self.lbl_cnt_bostezos.text = str(self.contador_bostezos)
            threading.Thread(
                target=lanzar_alerta, args=("precaucion",), daemon=True).start()

        # Borde parpadeante
        if estado == "alerta":
            self._start_blink()
        elif estado == "malo":
            self._stop_blink()
            self._draw_border(True, C_ORANGE)
        else:
            self._stop_blink()

        # HUD
        emoji, texto, color = ESTADO_INFO[estado]
        self.hud_estado.text  = f'{emoji}  {texto}'
        self.hud_estado.color = color
        self.hud_dot.color    = color
        self.hud_nivel.text   = NIVEL_TEXTO[estado]
        self.hud_nivel.color  = color
        self.lbl_ear.color    = color if estado != "bueno" else C_TEXT
        self.lbl_mar.color    = color if estado in ("malo","alerta") else C_TEXT

        # Textura
        frame_flip = cv2.flip(frame, 0)
        buf        = frame_flip.tobytes()
        tex        = Texture.create(
            size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        tex.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.img_camara.texture = tex

    def cerrar_sesion(self, *args):
        self.detener_camara()
        self.manager.current = 'login'


# ═════════════════════════════════════════════
# APP
# ═════════════════════════════════════════════
class ViggoApp(App):
    def build(self):
        self.title = 'VIGGO — Detección de Fatiga'
        sm = ScreenManager(transition=FadeTransition(duration=0.25))
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegistroScreen(name='registro'))
        sm.add_widget(CamaraScreen(name='camara'))
        return sm

    def on_stop(self):
        c = self.root.get_screen('camara')
        if c.cap:
            c.cap.release()


if __name__ == '__main__':
    ViggoApp().run()