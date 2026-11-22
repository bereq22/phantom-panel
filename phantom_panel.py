# language: Python 3.9+  | file: phantom_panel.py | target: Windows (modo demo em outros SOs)
# PHANTOM PANEL - utilitario anti-AFK / keep-awake de nivel de sistema.
# Manda um sinal inofensivo (tecla F15 e/ou micro-jiggle de mouse que retorna a
# posicao) para o SO e apps normais nao marcarem a sessao como ociosa.
# Mantem o COMPUTADOR acordado. Nao injeta input de gameplay e nao e bypass de anticheat.

import sys
import time
import random
import tkinter as tk

IS_WIN = sys.platform.startswith("win")

# ---------------- backend de input (Windows / ctypes SendInput) ----------------
if IS_WIN:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
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
    VK_F15 = 0x7E  # tecla "no-op": nao digita nada, so conta como atividade

    def tap_key(vk=VK_F15):
        extra = ctypes.c_ulong(0)
        down = INPUT(type=INPUT_KEYBOARD, u=_U(ki=KEYBDINPUT(vk, 0, 0, 0, ctypes.pointer(extra))))
        up = INPUT(type=INPUT_KEYBOARD, u=_U(ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))))
        user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
        user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))

    def jiggle_mouse(px=2):
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetCursorPos(pt.x + px, pt.y)
        time.sleep(0.03)
        user32.SetCursorPos(pt.x, pt.y)  # volta exatamente pra onde estava
else:  # fora do Windows: roda em modo demo (painel abre, sem input real)
    def tap_key(vk=0): pass
    def jiggle_mouse(px=2): pass

# ---------------- paleta ----------------
BG      = "#0d0f14"
PANEL   = "#151a23"
CARD    = "#1b212c"
TEXT    = "#e6e9ef"
MUTED   = "#8b93a7"
ACCENT  = "#7c4dff"
CYAN    = "#00e5ff"
OK      = "#28d17c"
OFF     = "#ff4d6d"

class PhantomPanel:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.mode = tk.StringVar(value="key")   # key | mouse | both
        self.count = 0
        self.next_fire = 0.0
        self.start_t = 0.0

        root.title("Phantom Panel")
        root.configure(bg=BG)
        root.geometry("440x600")
        root.resizable(False, False)

        self._build_header()
        self._build_controls()
        self._build_stats()
        self._build_log()
        self._build_footer()

        self.log("Phantom Panel pronto." if IS_WIN else "Modo DEMO (nao-Windows): painel ativo, sem envio de input.")
        self._tick()

    # ---------- logo desenhada ----------
    def _draw_ghost(self, c):
        c.create_oval(6, 6, 78, 78, outline=ACCENT, width=2)          # anel externo
        c.create_oval(12, 12, 72, 72, outline=CYAN, width=1)          # anel interno
        w = "#eef1f7"
        c.create_arc(26, 24, 58, 56, start=0, extent=180, fill=w, outline=w)   # cupula
        c.create_rectangle(26, 40, 58, 62, fill=w, outline=w)                  # corpo
        c.create_arc(26, 55, 37, 68, start=180, extent=180, fill=w, outline=w) # pe 1
        c.create_arc(36, 55, 48, 68, start=180, extent=180, fill=w, outline=w) # pe 2
        c.create_arc(47, 55, 58, 68, start=180, extent=180, fill=w, outline=w) # pe 3
        c.create_oval(33, 37, 40, 46, fill=PANEL, outline=PANEL)              # olho E
        c.create_oval(44, 37, 51, 46, fill=PANEL, outline=PANEL)              # olho D

    def _build_header(self):
        head = tk.Frame(self.root, bg=PANEL)
        head.pack(fill="x")
        logo = tk.Canvas(head, width=84, height=84, bg=PANEL, highlightthickness=0)
        logo.pack(side="left", padx=(16, 10), pady=14)
        self._draw_ghost(logo)
        box = tk.Frame(head, bg=PANEL)
        box.pack(side="left", anchor="w", pady=20)
        tk.Label(box, text="PHANTOM PANEL", bg=PANEL, fg=TEXT,
                 font=("Segoe UI Semibold", 17)).pack(anchor="w")
        tk.Label(box, text="anti-afk  ·  keep-awake utility", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Frame(self.root, bg=ACCENT, height=2).pack(fill="x")

    def _card(self, title):
        card = tk.Frame(self.root, bg=CARD)
        card.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(card, text=title, bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        return card

    def _build_controls(self):
        card = self._card("MODO DE ATIVIDADE")
        row = tk.Frame(card, bg=CARD); row.pack(fill="x", padx=12, pady=(0, 10))
        for val, label in (("key", "Tecla F15"), ("mouse", "Mouse"), ("both", "Ambos")):
            tk.Radiobutton(row, text=label, value=val, variable=self.mode,
                           bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD,
                           activeforeground=CYAN, font=("Segoe UI", 10),
                           indicatoron=True).pack(side="left", padx=(0, 14))

        card2 = self._card("INTERVALO (segundos, aleatorio entre min e max)")
        r2 = tk.Frame(card2, bg=CARD); r2.pack(fill="x", padx=12, pady=(0, 10))
        self.min_s = tk.Scale(r2, from_=5, to=300, orient="horizontal", label="min",
                              bg=CARD, fg=TEXT, troughcolor=PANEL, highlightthickness=0,
                              font=("Segoe UI", 8), length=180)
        self.min_s.set(30); self.min_s.pack(side="left", padx=(0, 10))
        self.max_s = tk.Scale(r2, from_=5, to=300, orient="horizontal", label="max",
                              bg=CARD, fg=TEXT, troughcolor=PANEL, highlightthickness=0,
                              font=("Segoe UI", 8), length=180)
        self.max_s.set(90); self.max_s.pack(side="left")

        self.btn = tk.Button(self.root, text="▶   INICIAR", command=self.toggle,
                             bg=ACCENT, fg="white", activebackground="#6a3de0",
                             activeforeground="white", relief="flat",
                             font=("Segoe UI Semibold", 13), height=2, cursor="hand2")
        self.btn.pack(fill="x", padx=16, pady=(16, 0))

    def _build_stats(self):
        card = self._card("STATUS")
        grid = tk.Frame(card, bg=CARD); grid.pack(fill="x", padx=12, pady=(0, 12))
        self.lbl_state = self._stat(grid, 0, "Estado", "IDLE", OFF)
        self.lbl_count = self._stat(grid, 1, "Acoes", "0", TEXT)
        self.lbl_next  = self._stat(grid, 2, "Proxima", "--", TEXT)
        self.lbl_up    = self._stat(grid, 3, "Uptime", "00:00", TEXT)

    def _stat(self, parent, col, name, val, color):
        f = tk.Frame(parent, bg=CARD); f.grid(row=0, column=col, padx=(0, 18))
        tk.Label(f, text=name, bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        lbl = tk.Label(f, text=val, bg=CARD, fg=color, font=("Consolas", 13, "bold"))
        lbl.pack(anchor="w")
        return lbl

    def _build_log(self):
        card = self._card("LOG")
        self.txt = tk.Text(card, height=7, bg=PANEL, fg=MUTED, relief="flat",
                           font=("Consolas", 9), wrap="word", state="disabled",
                           insertbackground=TEXT)
        self.txt.pack(fill="both", padx=12, pady=(0, 12))

    def _build_footer(self):
        tk.Label(self.root,
                 text="Mantem o sistema acordado. Nao e game bot nem bypass de anticheat.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(pady=10)

    # ---------- logica ----------
    def log(self, msg):
        self.txt.configure(state="normal")
        self.txt.insert("end", time.strftime("[%H:%M:%S] ") + msg + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def toggle(self):
        self.running = not self.running
        if self.running:
            self.start_t = time.time()
            self.count = 0
            self._schedule_next(initial=True)
            self.btn.configure(text="■   PARAR", bg=OFF, activebackground="#e23a57")
            self.lbl_state.configure(text="ACTIVE", fg=OK)
            self.log("Iniciado | modo=%s | intervalo=%d-%ds" %
                     (self.mode.get(), self.min_s.get(), self.max_s.get()))
        else:
            self.btn.configure(text="▶   INICIAR", bg=ACCENT, activebackground="#6a3de0")
            self.lbl_state.configure(text="IDLE", fg=OFF)
            self.lbl_next.configure(text="--")
            self.log("Parado.")

    def _schedule_next(self, initial=False):
        lo, hi = sorted((self.min_s.get(), self.max_s.get()))
        delay = 2 if initial else random.uniform(lo, hi)
        self.next_fire = time.time() + delay

    def _fire(self):
        m = self.mode.get()
        if m in ("key", "both"):
            tap_key()
        if m in ("mouse", "both"):
            jiggle_mouse()
        self.count += 1
        self.lbl_count.configure(text=str(self.count))
        self.log("sinal enviado (%s)" % m + ("" if IS_WIN else " [demo]"))
        self._schedule_next()

    def _tick(self):
        if self.running:
            now = time.time()
            rem = self.next_fire - now
            if rem <= 0:
                self._fire()
            else:
                self.lbl_next.configure(text="%2ds" % int(rem))
            up = int(now - self.start_t)
            self.lbl_up.configure(text="%02d:%02d" % (up // 60, up % 60))
        self.root.after(250, self._tick)


if __name__ == "__main__":
    root = tk.Tk()
    PhantomPanel(root)
    root.mainloop()
