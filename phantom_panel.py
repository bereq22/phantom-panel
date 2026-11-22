# language: Python 3.9+  | file: phantom_panel.py | target: Windows (modo demo fora do Windows)
# PHANTOM PANEL v2 - utilitario keep-awake / anti-AFK de nivel de sistema.
# Mantem o COMPUTADOR e a sessao acordados. Nao injeta input de gameplay,
# nao move personagem em jogo nenhum e nao e bypass de anticheat.

import sys
import time
import math
import random
import tkinter as tk

IS_WIN = sys.platform.startswith("win")

# ---------------- backend de input (Windows / ctypes) ----------------
if IS_WIN:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    PUL = ctypes.POINTER(ctypes.c_ulong)

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", PUL)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", PUL)]

    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    VK_F15 = 0x7E   # tecla no-op: nao digita, nao mexe em jogo, so conta como atividade
    VK_F8  = 0x77   # hotkey global liga/desliga

    ES_CONTINUOUS        = 0x80000000
    ES_SYSTEM_REQUIRED   = 0x00000001
    ES_DISPLAY_REQUIRED  = 0x00000002

    def tap_key(vk=VK_F15):
        ex = ctypes.c_ulong(0)
        d = INPUT(type=INPUT_KEYBOARD, u=_U(ki=KEYBDINPUT(vk, 0, 0, 0, ctypes.pointer(ex))))
        u = INPUT(type=INPUT_KEYBOARD, u=_U(ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(ex))))
        user32.SendInput(1, ctypes.byref(d), ctypes.sizeof(INPUT))
        user32.SendInput(1, ctypes.byref(u), ctypes.sizeof(INPUT))

    def _pos():
        p = wintypes.POINT(); user32.GetCursorPos(ctypes.byref(p)); return p.x, p.y

    def jiggle():
        x, y = _pos()
        user32.SetCursorPos(x + 3, y); time.sleep(0.03); user32.SetCursorPos(x, y)

    def circle():
        x, y = _pos()
        for a in range(0, 360, 45):
            user32.SetCursorPos(x + int(6 * math.cos(math.radians(a))),
                                y + int(6 * math.sin(math.radians(a))))
            time.sleep(0.012)
        user32.SetCursorPos(x, y)

    def prevent_sleep(on):
        kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED if on else ES_CONTINUOUS)

    def f8_down():
        return bool(user32.GetAsyncKeyState(VK_F8) & 0x8000)
else:  # fora do Windows: painel abre em modo demo, sem input real
    def tap_key(vk=0): pass
    def jiggle(): pass
    def circle(): pass
    def prevent_sleep(on): pass
    def f8_down(): return False

# ---------------- paleta ----------------
BG, PANEL, CARD = "#0d0f14", "#151a23", "#1b212c"
TEXT, MUTED = "#e6e9ef", "#8b93a7"
ACCENT, CYAN, OK, OFF = "#7c4dff", "#00e5ff", "#28d17c", "#ff4d6d"

PACES = {"Suave": 60, "Normal": 30, "Frequente": 15}  # segundos-base por ritmo


class PhantomPanel:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.count = 0
        self.next_fire = 0.0
        self._f8_prev = False

        # metodos (varios ao mesmo tempo)
        self.m_sleep  = tk.BooleanVar(value=True)   # impedir suspensao (API)
        self.m_key    = tk.BooleanVar(value=True)   # tecla segura F15
        self.m_jiggle = tk.BooleanVar(value=False)  # mouse tremer
        self.m_circle = tk.BooleanVar(value=False)  # mouse circulo
        self.pace = tk.StringVar(value="Normal")
        self.topmost = tk.BooleanVar(value=False)

        root.title("Phantom Panel")
        root.configure(bg=BG)
        root.geometry("460x640")
        root.resizable(False, False)

        self._header()
        self._methods()
        self._pace_row()
        self._extras()
        self._main_button()
        self._status()
        self._log_box()
        self._footer()

        self.log("Phantom Panel v2 pronto." if IS_WIN
                 else "Modo DEMO (nao-Windows): painel ativo, sem envio de input.")
        self._tick()

    # ---------- logo ----------
    def _ghost(self, c):
        c.create_oval(6, 6, 78, 78, outline=ACCENT, width=2)
        c.create_oval(12, 12, 72, 72, outline=CYAN, width=1)
        w = "#eef1f7"
        c.create_arc(26, 24, 58, 56, start=0, extent=180, fill=w, outline=w)
        c.create_rectangle(26, 40, 58, 62, fill=w, outline=w)
        for x0, x1 in ((26, 37), (36, 48), (47, 58)):
            c.create_arc(x0, 55, x1, 68, start=180, extent=180, fill=w, outline=w)
        c.create_oval(33, 37, 40, 46, fill=PANEL, outline=PANEL)
        c.create_oval(44, 37, 51, 46, fill=PANEL, outline=PANEL)

    def _header(self):
        h = tk.Frame(self.root, bg=PANEL); h.pack(fill="x")
        logo = tk.Canvas(h, width=84, height=84, bg=PANEL, highlightthickness=0)
        logo.pack(side="left", padx=(16, 10), pady=14); self._ghost(logo)
        box = tk.Frame(h, bg=PANEL); box.pack(side="left", anchor="w", pady=22)
        tk.Label(box, text="PHANTOM PANEL", bg=PANEL, fg=TEXT,
                 font=("Segoe UI Semibold", 17)).pack(anchor="w")
        tk.Label(box, text="anti-afk  ·  keep-awake  ·  v2", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Frame(self.root, bg=ACCENT, height=2).pack(fill="x")

    def _card(self, title):
        c = tk.Frame(self.root, bg=CARD); c.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(c, text=title, bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        return c

    def _chk(self, parent, var, text, cmd=None):
        return tk.Checkbutton(parent, text=text, variable=var, command=cmd,
                              bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD,
                              activeforeground=CYAN, font=("Segoe UI", 10),
                              anchor="w", padx=4)

    def _methods(self):
        c = self._card("METODOS  (pode marcar varios)")
        self._chk(c, self.m_sleep, "Impedir suspensao do PC  (API, sem input falso)",
                  self._sleep_toggle).pack(fill="x", padx=10)
        self._chk(c, self.m_key, "Tecla segura  (F15 — nao mexe em jogo)").pack(fill="x", padx=10)
        self._chk(c, self.m_jiggle, "Mouse: tremer  (3px e volta)").pack(fill="x", padx=10)
        self._chk(c, self.m_circle, "Mouse: circulo  (micro-giro e volta)").pack(fill="x", padx=10, pady=(0, 8))

    def _pace_row(self):
        c = self._card("RITMO")
        row = tk.Frame(c, bg=CARD); row.pack(fill="x", padx=10, pady=(0, 10))
        for name in PACES:
            tk.Radiobutton(row, text=name, value=name, variable=self.pace,
                           bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD,
                           activeforeground=CYAN, font=("Segoe UI", 10)).pack(side="left", padx=(0, 16))

    def _extras(self):
        c = self._card("EXTRAS")
        row = tk.Frame(c, bg=CARD); row.pack(fill="x", padx=10, pady=(0, 10))
        self._chk(row, self.topmost, "Sempre no topo", self._topmost_toggle).pack(side="left")
        tk.Label(row, text="atalho global:  F8  liga/desliga", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right")

    def _main_button(self):
        self.btn = tk.Button(self.root, text="▶   INICIAR", command=self.toggle,
                             bg=ACCENT, fg="white", activebackground="#6a3de0",
                             activeforeground="white", relief="flat",
                             font=("Segoe UI Semibold", 13), height=2, cursor="hand2")
        self.btn.pack(fill="x", padx=16, pady=(14, 0))

    def _status(self):
        c = self._card("STATUS")
        g = tk.Frame(c, bg=CARD); g.pack(fill="x", padx=12, pady=(0, 12))
        self.lbl_state = self._stat(g, 0, "Estado", "IDLE", OFF)
        self.lbl_count = self._stat(g, 1, "Acoes enviadas", "0", TEXT)

    def _stat(self, parent, col, name, val, color):
        f = tk.Frame(parent, bg=CARD); f.grid(row=0, column=col, padx=(0, 28))
        tk.Label(f, text=name, bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        lbl = tk.Label(f, text=val, bg=CARD, fg=color, font=("Consolas", 14, "bold"))
        lbl.pack(anchor="w")
        return lbl

    def _log_box(self):
        c = self._card("LOG")
        self.txt = tk.Text(c, height=6, bg=PANEL, fg=MUTED, relief="flat",
                           font=("Consolas", 9), wrap="word", state="disabled")
        self.txt.pack(fill="both", padx=12, pady=(0, 12))

    def _footer(self):
        tk.Label(self.root,
                 text="Mantem o sistema acordado. Nao move personagem em jogo nem burla anticheat.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(pady=8)

    # ---------- comportamento ----------
    def log(self, msg):
        self.txt.configure(state="normal")
        self.txt.insert("end", time.strftime("[%H:%M:%S] ") + msg + "\n")
        self.txt.see("end"); self.txt.configure(state="disabled")

    def _sleep_toggle(self):
        if self.running:
            prevent_sleep(self.m_sleep.get())

    def _topmost_toggle(self):
        self.root.attributes("-topmost", self.topmost.get())

    def _interval(self):
        base = PACES[self.pace.get()]
        return base * random.uniform(0.8, 1.2)  # jitter leve: sinal de atividade estavel

    def toggle(self):
        self.running = not self.running
        if self.running:
            self.count = 0
            if self.m_sleep.get():
                prevent_sleep(True)
            self.next_fire = time.time() + 2
            self.btn.configure(text="■   PARAR", bg=OFF, activebackground="#e23a57")
            self.lbl_state.configure(text="ACTIVE", fg=OK)
            self.log("Iniciado | ritmo=%s" % self.pace.get())
        else:
            prevent_sleep(False)
            self.btn.configure(text="▶   INICIAR", bg=ACCENT, activebackground="#6a3de0")
            self.lbl_state.configure(text="IDLE", fg=OFF)
            self.log("Parado.")

    def _fire(self):
        did = []
        if self.m_key.get():    tap_key();  did.append("F15")
        if self.m_jiggle.get(): jiggle();   did.append("tremer")
        if self.m_circle.get(): circle();   did.append("circulo")
        if did:
            self.count += 1
            self.lbl_count.configure(text=str(self.count))
            self.log("sinal: " + ", ".join(did) + ("" if IS_WIN else " [demo]"))
        self.next_fire = time.time() + self._interval()

    def _tick(self):
        # hotkey global F8 (deteccao de borda)
        down = f8_down()
        if down and not self._f8_prev:
            self.toggle()
        self._f8_prev = down

        if self.running and time.time() >= self.next_fire:
            self._fire()
        self.root.after(200, self._tick)


if __name__ == "__main__":
    root = tk.Tk()
    PhantomPanel(root)
    root.mainloop()
