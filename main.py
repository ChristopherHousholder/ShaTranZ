import os
import sys
import traceback

def handle_exception(exc_type, exc_value, exc_traceback):
    error = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"Uncaught exception:\n{error}")

sys.excepthook = handle_exception

import threading
import requests
import io

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.graphics import Color, Ellipse, InstructionGroup, RoundedRectangle
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty
from kivy.utils import platform

# Dynamically locate font
base_dir = os.path.dirname(__file__)
font_path = os.path.join(base_dir, "assets", "NotoSansCJKkr-Regular.otf")
if not os.path.exists(font_path):
    font_path = "assets/NotoSansCJKkr-Regular.otf"

Window.clearcolor = (0.1, 0.0, 0.2, 1)

if platform == 'android':
    from android.permissions import request_permissions, check_permission, Permission
    from jnius import autoclass, JavaException

LANG_MAP = {
    "English": "en", "Español": "es", "한국어": "ko", "Français": "fr", "Deutsch": "de",
    "Italiano": "it", "Português": "pt", "Nederlands": "nl", "Русский": "ru", "中文": "zh",
    "日本語": "ja", "हिन्दी": "hi", "Türkçe": "tr", "Polski": "pl",
    "Ελληνικά": "el", "العربية": "ar", "Magyar": "hu", "Čeština": "cs",
    "Română": "ro", "Українська": "uk", "Svenska": "sv", "Suomi": "fi", "Dansk": "da",
    "Norsk": "no", "Bahasa Indonesia": "id", "Tiếng Việt": "vi", "Tagalog": "tl", "Malay": "ms"
}

SERVER_URL = "http://192.168.86.39:8000"

class RippleLayer(InstructionGroup):
    def __init__(self, widget):
        super().__init__()
        self.w = widget

    def spawn(self, duration=1.0):
        col = Color(0.4, 0.6, 1, 0.6)
        ripple = Ellipse(size=(0, 0), pos=self.w.center)
        self.add(col)
        self.add(ripple)
        diam = max(self.w.width, self.w.height) * 0.9
        max_sz = (diam, diam)
        max_pos = (self.w.center_x - diam / 2, self.w.center_y - diam / 2)
        grow = Animation(size=max_sz, pos=max_pos, duration=duration, t="out_quad")
        shrink = Animation(size=(0, 0), pos=self.w.center, duration=duration, t="in_quad")
        grow.bind(on_complete=lambda *_: shrink.start(ripple))
        shrink.bind(on_complete=lambda *_: (self.remove(col), self.remove(ripple)))
        grow.start(ripple)

class BoltButton(ButtonBehavior, Image):
    def __init__(self, **kwargs):
        kwargs.setdefault("source", "bolt.png")
        kwargs.setdefault("allow_stretch", True)
        kwargs.setdefault("keep_ratio", True)
        super().__init__(**kwargs)
        self.ripples = RippleLayer(self)
        self.canvas.before.add(self.ripples)
        self._pulse = None

    def on_press(self):
        if self._pulse is None:
            self.ripples.spawn()
            self._pulse = Clock.schedule_interval(lambda dt: self.ripples.spawn(), 1.5)
        else:
            self._pulse.cancel()
            self._pulse = None
        app = App.get_running_app()
        if app.is_recording:
            app.stop_translation()
        else:
            app.start_translation()

KV = """
<SpinnerOption>:
    font_name: app.get_font_for_text(self.text)

<NeonButton@Button>:
    background_normal: ''
    background_color: 0, 0, 0, 0
    font_name: app.get_font_for_text(self.text)
    canvas.before:
        Color:
            rgba: (0.3, 0.6, 1, 0.5) if self.text != "English" else (1, 0, 0.5, 1)
        RoundedRectangle:
            size: self.size
            pos: self.pos
            radius: [20]
    color: 1, 1, 1, 1
    font_size: '20sp'
    bold: True

BoxLayout:
    orientation: 'vertical'
    padding: 20
    spacing: 20

    BoxLayout:
        size_hint_y: 0.2
        spacing: 20

        Spinner:
            id: lang_spinner
            text: "Choose Language"
            values: app.lang_names
            font_name: app.get_font_for_text(self.text)
            on_text:
                if self.text != "Choose Language": app.set_language(self.text)
            size_hint_x: 1
            background_normal: ''
            background_color: 0.3, 0.6, 1, 0.5
            color: 1, 1, 1, 1
            font_size: '20sp'

        NeonButton:
            text: "English"
            on_release: app.set_output_language()

    FloatLayout:
        size_hint_y: 0.3
        canvas.before:
            Color:
                rgba: 0.2, 0.3, 0.6, 0.5
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [30]
        BoltButton:
            size_hint: None, None
            size: 240, 240
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}

    BoxLayout:
        orientation: 'vertical'
        spacing: 10
        size_hint_y: 0.5

        BoxLayout:
            canvas.before:
                Color:
                    rgba: 1, 0.2, 0.6, 0.5
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [20]
            ScrollView:
                do_scroll_x: False
                bar_width: 8
                Label:
                    id: transcription_output
                    text: app.translated_text
                    font_name: app.get_font_for_text(self.text)
                    color: 1, 1, 1, 1
                    font_size: '18sp'
                    text_size: self.width, None
                    size_hint_y: None
                    height: self.texture_size[1]
                    halign: 'left'
                    valign: 'middle'
        BoxLayout:
            canvas.before:
                Color:
                    rgba: 0.3, 0.6, 1, 0.5
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [20]
            ScrollView:
                do_scroll_x: False
                bar_width: 8
                Label:
                    id: output_label
                    text: app.status_text
                    font_name: app.get_font_for_text(self.text)
                    color: 1, 1, 1, 1
                    font_size: '16sp'
                    text_size: self.width, None
                    size_hint_y: None
                    height: self.texture_size[1]
                    halign: 'left'
                    valign: 'middle'
"""

class TranslationApp(App):

    def get_font_for_text(self, text):
        for char in text:
            code = ord(char)
            if 0x0600 <= code <= 0x06FF:
                return "assets/NotoSansArabic-Regular.ttf"
            elif 0x0900 <= code <= 0x097F:
                return "assets/NotoSansDevanagari-Regular.ttf"
            elif 0xAC00 <= code <= 0xD7AF or 0x4E00 <= code <= 0x9FFF:
                return "assets/NotoSansCJKkr-Regular.otf"
        return "assets/NotoSans-Regular.ttf"

    translated_text = StringProperty("")
    status_text = StringProperty("")
    lang_names = list(LANG_MAP.keys())
    current_lang = "en"
    is_recording = BooleanProperty(False)
    font_path = font_path

    def build(self):
        return Builder.load_string(KV)

    def _initialize_tts(self):
        if platform != 'android':
            self.translated_text = "TTS only available on Android."
            return
        try:
            TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
            Locale = autoclass('java.util.Locale')
            PythonActivity = autoclass('org.kivy.android.PythonActivity').mActivity
            self.tts = TextToSpeech(PythonActivity, None)
            self.tts.setLanguage(Locale.US)
        except Exception as e:
            self.translated_text = f"TTS init error: {e}"

    def on_start(self):
        self._initialize_tts()
        if platform == 'android' and not check_permission(Permission.RECORD_AUDIO):
            request_permissions([Permission.RECORD_AUDIO], self._on_permissions)
            self.status_text = "Requesting mic permission…"

    def _on_permissions(self, permissions, grants):
        if all(grants):
            self.status_text = "Permission granted."
        else:
            self.status_text = "Microphone permission denied."

    def set_language(self, display_name):
        self.current_lang = LANG_MAP.get(display_name, "en")
        self.translated_text = f"Source language: {display_name}"

    def set_output_language(self):
        self.translated_text = "Output language button pressed."

    def start_translation(self):
        if platform != 'android':
            self.status_text = "Runs only on Android."
            return
        if not check_permission(Permission.RECORD_AUDIO):
            request_permissions([Permission.RECORD_AUDIO], self._on_permissions)
            self.status_text = "Requesting mic permission…"
            return
        try:
            self._chunk_index = 1
            self._setup_paths()
            self._begin_recording()
            self.uploader = Clock.schedule_interval(self._swap_chunk, 15.0)
            self.is_recording = True
            self.status_text = "Recording..."
        except Exception as e:
            self.status_text = f"Startup error: {e}"

    def _setup_paths(self):
        PythonActivity = autoclass('org.kivy.android.PythonActivity').mActivity
        ext = PythonActivity.getExternalFilesDir(None)
        if ext is None:
            raise RuntimeError("Could not access external storage")
        out_dir = ext.getAbsolutePath()
        self.chunk_paths = [
            f"{out_dir}/chunk1.3gp",
            f"{out_dir}/chunk2.3gp"
        ]
        self.current_chunk = 0

    def _begin_recording(self):
        self._init_recorder(self.chunk_paths[self.current_chunk])
        self.recorder.prepare()
        self.recorder.start()

    def _init_recorder(self, path):
        MediaRecorder = autoclass('android.media.MediaRecorder')
        AudioSource = autoclass('android.media.MediaRecorder$AudioSource')
        OutputFormat = autoclass('android.media.MediaRecorder$OutputFormat')
        AudioEncoder = autoclass('android.media.MediaRecorder$AudioEncoder')
        self.recorder = MediaRecorder()
        self.recorder.setAudioSource(AudioSource.MIC)
        self.recorder.setOutputFormat(OutputFormat.THREE_GPP)
        self.recorder.setAudioEncoder(AudioEncoder.AMR_NB)
        self.recorder.setOutputFile(path)

    def _swap_chunk(self, dt):
        try:
            self.recorder.stop()
            self.recorder.release()
            prev_chunk = self.chunk_paths[self.current_chunk]
            self.current_chunk = 1 - self.current_chunk
            self._init_recorder(self.chunk_paths[self.current_chunk])
            self.recorder.prepare()
            self.recorder.start()
            threading.Thread(
                target=self._upload,
                args=(prev_chunk, self.current_lang),
                daemon=True
            ).start()
        except Exception as e:
            self.status_text = f"Swap error: {e}"

    def stop_translation(self):
        if hasattr(self, 'uploader'):
            self.uploader.cancel()
        try:
            if hasattr(self, 'recorder'):
                self.recorder.stop()
                self.recorder.release()
        except Exception:
            pass
        self.is_recording = False
        self.status_text = "Stopped."

    def _upload(self, filepath, lang_code):
        try:
            with open(filepath, 'rb') as f:
                audio_bytes = f.read()
            files = {"file": ("chunk.3gp", io.BytesIO(audio_bytes), "audio/3gp")}
            data = {"language": lang_code}
            response = requests.post(f"{SERVER_URL}/transcribe/", files=files, data=data)
            resp_json = response.json()
            txt = resp_json.get("translated_text", "")
        except Exception as e:
            txt = f"Upload error: {e}"

        def _update(dt):
            try:
                self.translated_text = txt
                root = self.root
                if root and hasattr(root, 'ids') and 'transcription_output' in root.ids:
                    trans_label = root.ids['transcription_output']
                    trans_label.text = txt

                    font_path = self.get_font_for_text(txt)
                    if font_path and os.path.exists(font_path):
                        trans_label.font_name = font_path

                if platform == 'android' and txt and len(txt) >= 5 and "no meaningful speech" not in txt.lower():
                    try:
                        self.tts.speak(txt, 0, None)
                    except JavaException as e:
                        print(f"TTS error: {e}")

            except Exception as e:
                self.translated_text = f"[UI update crash] {e}"
                print(f"[ERROR] UI crash: {e}")


        Clock.schedule_once(_update, 0)

if __name__ == '__main__':
    TranslationApp().run()
