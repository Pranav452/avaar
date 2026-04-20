import tkinter as tk
from tkinter import ttk, messagebox
import math
import random

# ── Pastel Palette ───────────────────────────────────────────────
BG         = "#f0f4ff"
BG2        = "#e8edf8"
PANEL      = "#ffffff"
BORDER     = "#c8d3ee"
C_BLUE     = "#3b5bdb"; C_BLUE_L  = "#dbe4ff"
C_PURP     = "#6741d9"; C_PURP_L  = "#e5dbff"
C_GRN      = "#2f9e44"; C_GRN_L   = "#d3f9d8"
C_ORG      = "#e8590c"; C_ORG_L   = "#ffe8cc"
C_RED      = "#c92a2a"; C_RED_L   = "#ffe3e3"
C_TEAL     = "#0c8599"; C_TEAL_L  = "#c5f6fa"
TEXT_DARK  = "#1a1f36"; TEXT_MID  = "#4a5568"
TEXT_LIGHT = "#8a94a6"; WHITE     = "#ffffff"

FT  = ("Trebuchet MS", 17, "bold")
FH  = ("Trebuchet MS", 10, "bold")
FB  = ("Trebuchet MS", 10)
FM  = ("Courier New",  10)
FMB = ("Courier New",  11, "bold")
FS  = ("Trebuchet MS",  9)


class PagingSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Paging Simulator — Logical to Physical Address Mapping")
        self.configure(bg=BG)
        self.geometry("1280x840")
        self.resizable(True, True)

        self.page_size    = tk.IntVar(value=256)
        self.num_frames   = tk.IntVar(value=16)
        self.logical_addr = tk.StringVar(value="")
        self.page_table   = {}
        self.tlb          = {}
        self.tlb_max      = 4
        self.anim_step    = 0
        self.anim_data    = None
        self.frame_usage  = {}   # frame_no -> page_no (for memory snapshot)

        # stats
        self.stat_total   = 0
        self.stat_hits    = 0
        self.stat_misses  = 0
        self.stat_faults  = 0

        self._setup_style()
        self._build_ui()
        self._init_page_table()

    # ────────────────────────────────────────────────────────────
    #  STYLE
    # ────────────────────────────────────────────────────────────
    def _setup_style(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TCombobox", fieldbackground=BG2, background=BG2,
                    foreground=TEXT_DARK, font=FB)
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", font=FH, padding=[14, 6],
                    background=BG2, foreground=TEXT_MID)
        s.map("TNotebook.Tab",
              background=[("selected", WHITE)],
              foreground=[("selected", C_BLUE)])
        s.configure("Treeview", background=PANEL, foreground=TEXT_DARK,
                    rowheight=26, fieldbackground=PANEL,
                    borderwidth=0, font=FM)
        s.configure("Treeview.Heading", background=BG2,
                    foreground=C_BLUE, relief="flat",
                    font=("Trebuchet MS", 10, "bold"))
        s.map("Treeview",
              background=[("selected", C_BLUE_L)],
              foreground=[("selected", C_BLUE)])

    # ────────────────────────────────────────────────────────────
    #  UI BUILD
    # ────────────────────────────────────────────────────────────
    def _build_ui(self):
        # header
        hdr = tk.Frame(self, bg=C_BLUE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⬡  Paging Simulator", font=FT,
                 bg=C_BLUE, fg=WHITE, padx=20, pady=10).pack(side="left")
        tk.Label(hdr,
                 text="SY Computer Engineering  |  Operating Systems  |  Self Learning Activity",
                 font=FS, bg=C_BLUE, fg="#a5c0ff").pack(side="left", padx=4)
        tk.Button(hdr, text="⟳  Reset All", font=FH,
                  bg="#1a3ab0", fg=WHITE, relief="flat",
                  cursor="hand2", bd=0, padx=14, pady=8,
                  command=self._reset_all).pack(side="right", padx=16, pady=8)

        # tabs
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=10)

        t1 = tk.Frame(self.nb, bg=BG)
        t2 = tk.Frame(self.nb, bg=BG)
        t3 = tk.Frame(self.nb, bg=BG)
        t4 = tk.Frame(self.nb, bg=BG)
        t5 = tk.Frame(self.nb, bg=BG)

        self.nb.add(t1, text="  Address Translator  ")
        self.nb.add(t2, text="  TLB Demo  ")
        self.nb.add(t3, text="  Binary Breakdown  ")
        self.nb.add(t4, text="  Memory Snapshot  ")
        self.nb.add(t5, text="  Statistics  ")

        self._build_tab_translator(t1)
        self._build_tab_tlb(t2)
        self._build_tab_binary(t3)
        self._build_tab_memory(t4)
        self._build_tab_stats(t5)

    # ════════════════════════════════════════════════════════════
    #  TAB 1 — Address Translator
    # ════════════════════════════════════════════════════════════
    def _build_tab_translator(self, parent):
        left = tk.Frame(parent, bg=BG, width=320)
        right = tk.Frame(parent, bg=BG)
        left.pack(side="left", fill="y", padx=(10, 6), pady=10)
        left.pack_propagate(False)
        right.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # config
        box = self._card(left, "⚙  Configuration", C_BLUE)
        self._combo_row(box, "Page / Frame Size (bytes)",
                        self.page_size, [64, 128, 256, 512, 1024])
        self._combo_row(box, "Number of Frames",
                        self.num_frames, [4, 8, 16, 32])
        self._btn(box, "↺  Reinitialise Page Table", C_BLUE, self._init_page_table)

        # translate
        box2 = self._card(left, "🔍  Address Translation", C_PURP)
        tk.Label(box2, text="Logical Address (decimal):",
                 font=FS, bg=PANEL, fg=TEXT_MID).pack(anchor="w", pady=(4, 2))
        row = tk.Frame(box2, bg=PANEL)
        row.pack(fill="x")
        self.entry = tk.Entry(row, textvariable=self.logical_addr,
                              font=FMB, bg=BG2, fg=TEXT_DARK,
                              relief="flat", bd=6, width=11,
                              insertbackground=C_BLUE)
        self.entry.pack(side="left", padx=(0, 6))
        self.entry.bind("<Return>", lambda e: self._start_translate())
        self._btn_inline(row, "Translate", C_GRN, self._start_translate)

        self.res_var = tk.StringVar(value="Enter an address and click Translate.")
        self.res_lbl = tk.Label(box2, textvariable=self.res_var,
                                font=FM, bg=C_BLUE_L, fg=TEXT_DARK,
                                justify="left", anchor="w",
                                padx=10, pady=8, wraplength=270)
        self.res_lbl.pack(fill="x", pady=(10, 0))

        self.anim_var = tk.StringVar(value="")
        tk.Label(box2, textvariable=self.anim_var,
                 font=FS, bg=PANEL, fg=C_PURP,
                 justify="left", anchor="w").pack(fill="x", pady=(4, 0))

        # formula
        box3 = self._card(left, "📐  Formula Reference", C_ORG)
        for lbl, f in [
            ("Page No.",      "= Logical Addr  ÷  Page Size"),
            ("Offset",        "= Logical Addr  mod  Page Size"),
            ("Physical Addr", "= Frame No  ×  Page Size  +  Offset"),
        ]:
            tk.Label(box3, text=lbl, font=("Trebuchet MS", 9, "bold"),
                     bg=PANEL, fg=C_ORG).pack(anchor="w", pady=(6, 0))
            tk.Label(box3, text=f, font=FM, bg=C_ORG_L,
                     fg=TEXT_DARK, padx=8, pady=3,
                     anchor="w").pack(fill="x")

        # diagram
        dbox = self._card(right, "📊  Visual Mapping Diagram", C_BLUE, expand=True)
        self.canvas = tk.Canvas(dbox, bg=PANEL, highlightthickness=0, height=320)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw_diagram())

        # history
        hbox = self._card(right, "📜  Translation History", C_PURP)
        cols = ("Logical", "Page No.", "Offset", "Frame No.", "Physical", "TLB?")
        self.tree = ttk.Treeview(hbox, columns=cols, show="headings", height=5)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=95, anchor="center")
        self.tree.pack(fill="both", expand=True)
        tk.Button(hbox, text="Clear", font=FS, bg=BG2, fg=TEXT_LIGHT,
                  relief="flat", cursor="hand2", bd=0, padx=8, pady=3,
                  command=self._clear_history).pack(anchor="e", pady=(4, 0))

    # ════════════════════════════════════════════════════════════
    #  TAB 2 — TLB
    # ════════════════════════════════════════════════════════════
    def _build_tab_tlb(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=16)

        info = self._card(wrap, "⚡  TLB — Translation Lookaside Buffer", C_TEAL)
        tk.Label(info,
                 text="The TLB is a small, fast cache storing recent page→frame mappings.\n"
                      "TLB Hit  → physical address found instantly (no page table lookup needed).\n"
                      "TLB Miss → page table consulted, result stored in TLB for next time.",
                 font=FB, bg=PANEL, fg=TEXT_MID,
                 justify="left", wraplength=900).pack(anchor="w", pady=(0, 6))

        tbox = self._card(wrap, "🗃  Current TLB Contents", C_TEAL)
        cols = ("Slot", "Page No.", "Frame No.", "Status")
        self.tlb_tree = ttk.Treeview(tbox, columns=cols, show="headings", height=5)
        for c in cols:
            self.tlb_tree.heading(c, text=c)
            self.tlb_tree.column(c, width=180, anchor="center")
        self.tlb_tree.pack(fill="x")

        lbox = self._card(wrap, "📋  TLB Access Log", C_TEAL, expand=True)
        self.tlb_log = tk.Text(lbox, font=FM, bg=C_TEAL_L,
                               fg=TEXT_DARK, relief="flat",
                               height=8, state="disabled",
                               wrap="word", padx=10, pady=8)
        self.tlb_log.pack(fill="both", expand=True)
        self._btn(wrap, "Clear TLB Cache", C_TEAL, self._clear_tlb)

    # ════════════════════════════════════════════════════════════
    #  TAB 3 — Binary Breakdown
    # ════════════════════════════════════════════════════════════
    def _build_tab_binary(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=16)

        info = self._card(wrap, "🔢  Binary Address Breakdown", C_PURP)
        tk.Label(info,
                 text="A logical address is split into:   [ Page Number bits ]  +  [ Offset bits ]\n"
                      "Offset bits = log₂(Page Size)     |     Page bits = Total bits − Offset bits\n"
                      "Translate an address in Tab 1 to see its binary breakdown here.",
                 font=FB, bg=PANEL, fg=TEXT_MID,
                 justify="left", wraplength=900).pack(anchor="w", pady=(0, 4))

        self.bin_canvas = tk.Canvas(wrap, bg=PANEL, height=180,
                                    highlightthickness=0)
        self.bin_canvas.pack(fill="x", pady=(0, 10))

        self.bin_info = tk.Label(wrap, text="", font=FM,
                                 bg=C_PURP_L, fg=TEXT_DARK,
                                 justify="left", anchor="w",
                                 padx=14, pady=10)
        self.bin_info.pack(fill="x")

    # ════════════════════════════════════════════════════════════
    #  TAB 4 — Memory Snapshot
    # ════════════════════════════════════════════════════════════
    def _build_tab_memory(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=16)

        info = self._card(wrap, "🧠  Physical Memory Snapshot", C_GRN)
        tk.Label(info,
                 text="Each box below represents one physical memory frame.\n"
                      "Grey = Free frame   |   Coloured = Occupied (shows which page is loaded)\n"
                      "The highlighted frame glows green when you perform a translation.",
                 font=FB, bg=PANEL, fg=TEXT_MID,
                 justify="left", wraplength=900).pack(anchor="w", pady=(0, 4))

        # legend
        leg = tk.Frame(info, bg=PANEL)
        leg.pack(anchor="w", pady=(4, 0))
        for col, label in [(BG2, "Free"), (C_GRN_L, "Occupied"), (C_GRN, "Last Accessed")]:
            f = tk.Frame(leg, bg=col, width=18, height=18,
                         relief="solid", bd=1)
            f.pack(side="left", padx=(0, 4))
            tk.Label(leg, text=label, font=FS,
                     bg=PANEL, fg=TEXT_MID).pack(side="left", padx=(0, 14))

        grid_box = self._card(wrap, "Physical Memory Frames", C_GRN, expand=True)
        self.mem_canvas = tk.Canvas(grid_box, bg=PANEL,
                                    highlightthickness=0)
        self.mem_canvas.pack(fill="both", expand=True)
        self.mem_canvas.bind("<Configure>", lambda e: self._draw_memory())

    # ════════════════════════════════════════════════════════════
    #  TAB 5 — Statistics Dashboard
    # ════════════════════════════════════════════════════════════
    def _build_tab_stats(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=16)

        info = self._card(wrap, "📈  Statistics Dashboard", C_PURP)
        tk.Label(info,
                 text="Live counters updated every time you perform a translation.",
                 font=FB, bg=PANEL, fg=TEXT_MID).pack(anchor="w")

        # big stat cards row
        cards_row = tk.Frame(wrap, bg=BG)
        cards_row.pack(fill="x", pady=(0, 10))

        self.sv_total  = tk.StringVar(value="0")
        self.sv_hits   = tk.StringVar(value="0")
        self.sv_misses = tk.StringVar(value="0")
        self.sv_faults = tk.StringVar(value="0")
        self.sv_rate   = tk.StringVar(value="0.0%")

        stat_defs = [
            ("Total Translations", self.sv_total,  C_BLUE,  C_BLUE_L),
            ("TLB Hits",           self.sv_hits,   C_GRN,   C_GRN_L),
            ("TLB Misses",         self.sv_misses, C_ORG,   C_ORG_L),
            ("Page Faults",        self.sv_faults, C_RED,   C_RED_L),
            ("TLB Hit Rate",       self.sv_rate,   C_PURP,  C_PURP_L),
        ]
        for label, var, fg, bg in stat_defs:
            self._stat_card(cards_row, label, var, fg, bg)

        # bar chart canvas
        chart_box = self._card(wrap, "📊  Hit / Miss / Fault Chart", C_PURP, expand=True)
        self.chart_canvas = tk.Canvas(chart_box, bg=PANEL,
                                      highlightthickness=0, height=260)
        self.chart_canvas.pack(fill="both", expand=True)
        self.chart_canvas.bind("<Configure>", lambda e: self._draw_chart())

    def _stat_card(self, parent, label, var, fg, bg):
        card = tk.Frame(parent, bg=bg, bd=0)
        card.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        tk.Label(card, text=label, font=FS, bg=bg,
                 fg=fg).pack(pady=(10, 2))
        tk.Label(card, textvariable=var,
                 font=("Trebuchet MS", 28, "bold"),
                 bg=bg, fg=fg).pack(pady=(0, 10))

    # ════════════════════════════════════════════════════════════
    #  LOGIC
    # ════════════════════════════════════════════════════════════
    def _init_page_table(self):
        ps  = self.page_size.get()
        nf  = self.num_frames.get()
        num_pages = 12
        random.seed(9)
        pool = list(range(nf)) * (num_pages // nf + 2)
        random.shuffle(pool)
        self.page_table  = {i: pool[i] for i in range(num_pages)}
        self.tlb         = {}
        self.frame_usage = {}
        self._draw_diagram()
        self._draw_memory()
        self._refresh_tlb_tree()
        self.res_var.set(
            f"Page table ready.\n"
            f"Page size : {ps} B   |   Frames: {nf}\n"
            f"Pages     : {num_pages}"
        )
        self.res_lbl.config(bg=C_GRN_L, fg=C_GRN)

    def _start_translate(self):
        raw = self.logical_addr.get().strip()
        if not raw.isdigit():
            messagebox.showerror("Input Error", "Enter a valid positive integer.")
            return
        la      = int(raw)
        ps      = self.page_size.get()
        page_no = la // ps
        offset  = la % ps
        self.anim_data = dict(la=la, ps=ps, page_no=page_no, offset=offset)
        self.anim_step = 0
        self._animate()

    def _animate(self):
        d  = self.anim_data
        la = d["la"]; ps = d["ps"]
        pn = d["page_no"]; off = d["offset"]
        steps = [
            f"Step 1 ▶  Logical address = {la}",
            f"Step 2 ▶  Page No = {la} ÷ {ps} = {pn}",
            f"Step 3 ▶  Offset  = {la} mod {ps} = {off}",
            f"Step 4 ▶  Checking TLB for page {pn}...",
        ]
        if self.anim_step < len(steps):
            self.anim_var.set(steps[self.anim_step])
            self.anim_step += 1
            self.after(550, self._animate)
        else:
            self._finish_translate(d)

    def _finish_translate(self, d):
        la = d["la"]; ps = d["ps"]
        pn = d["page_no"]; off = d["offset"]
        self.stat_total += 1

        if pn not in self.page_table:
            self.stat_faults += 1
            self.res_var.set(
                f"PAGE FAULT!\n"
                f"Page {pn} is not loaded in memory.\n"
                f"The OS must load it from disk first."
            )
            self.res_lbl.config(bg=C_RED_L, fg=C_RED)
            self.anim_var.set(f"Step 5 ▶  Page Fault on page {pn}!")
            self._log_tlb(f"[FAULT]  Page {pn} — not in memory.\n")
            self._update_stats()
            return

        tlb_hit = pn in self.tlb
        if tlb_hit:
            frame_no = self.tlb[pn]
            self.stat_hits += 1
            self.anim_var.set(f"Step 5 ▶  TLB Hit! Frame {frame_no} found instantly.")
            self._log_tlb(f"[HIT ]  Page {pn} -> Frame {frame_no}\n")
        else:
            frame_no = self.page_table[pn]
            self.stat_misses += 1
            if len(self.tlb) >= self.tlb_max:
                oldest = next(iter(self.tlb))
                del self.tlb[oldest]
            self.tlb[pn] = frame_no
            self.anim_var.set(
                f"Step 5 ▶  TLB Miss. Page table → Frame {frame_no}. TLB updated.")
            self._log_tlb(f"[MISS]  Page {pn} -> Frame {frame_no}  (TLB updated)\n")

        physical = frame_no * ps + off
        la_bin   = format(la, '016b')

        self.res_var.set(
            f"Logical Address  : {la}\n"
            f"Binary           : {la_bin}\n"
            f"────────────────────────────\n"
            f"Page Number      : {pn}\n"
            f"Offset           : {off}\n"
            f"Frame Number     : {frame_no}\n"
            f"────────────────────────────\n"
            f"Physical Address : {physical}\n"
            f"  = {frame_no} × {ps} + {off}"
        )
        self.res_lbl.config(bg=C_BLUE_L, fg=C_BLUE)
        self.tree.insert("", 0,
                         values=(la, pn, off, frame_no, physical,
                                 "✔ Hit" if tlb_hit else "✘ Miss"))

        # update frame usage for memory snapshot
        self.frame_usage[frame_no] = {"page": pn, "last": True}
        for f, v in self.frame_usage.items():
            if f != frame_no:
                v["last"] = False

        self._draw_diagram(highlight=pn)
        self._draw_memory(highlight=frame_no)
        self._draw_binary(la, ps)
        self._refresh_tlb_tree()
        self._update_stats()

    # ── stats ─────────────────────────────────────────────────────
    def _update_stats(self):
        self.sv_total.set(str(self.stat_total))
        self.sv_hits.set(str(self.stat_hits))
        self.sv_misses.set(str(self.stat_misses))
        self.sv_faults.set(str(self.stat_faults))
        total_tlb = self.stat_hits + self.stat_misses
        rate = (self.stat_hits / total_tlb * 100) if total_tlb > 0 else 0
        self.sv_rate.set(f"{rate:.1f}%")
        self._draw_chart()

    def _draw_chart(self):
        c = self.chart_canvas
        c.delete("all")
        W = c.winfo_width() or 700
        H = c.winfo_height() or 260

        data = [
            ("TLB Hits",   self.stat_hits,   C_GRN),
            ("TLB Misses", self.stat_misses, C_ORG),
            ("Page Faults",self.stat_faults, C_RED),
        ]
        total = max(sum(d[1] for d in data), 1)
        pad_l = 60; pad_r = 40; pad_t = 30; pad_b = 50
        chart_h = H - pad_t - pad_b
        chart_w = W - pad_l - pad_r
        bar_w   = chart_w // (len(data) * 2)

        # y axis
        c.create_line(pad_l, pad_t, pad_l, H - pad_b,
                      fill=BORDER, width=2)
        c.create_line(pad_l, H - pad_b, W - pad_r, H - pad_b,
                      fill=BORDER, width=2)

        # gridlines
        for i in range(1, 5):
            y = H - pad_b - (chart_h * i // 4)
            c.create_line(pad_l, y, W - pad_r, y,
                          fill=BORDER, dash=(4, 4))
            val = int(total * i / 4)
            c.create_text(pad_l - 8, y, text=str(val),
                          font=FS, fill=TEXT_LIGHT, anchor="e")

        for i, (label, value, color) in enumerate(data):
            bh  = int(chart_h * value / total)
            x1  = pad_l + i * (chart_w // len(data)) + bar_w // 2
            x2  = x1 + bar_w
            y1  = H - pad_b - bh
            y2  = H - pad_b

            # shadow
            c.create_rectangle(x1 + 4, y1 + 4, x2 + 4, y2,
                               fill=BORDER, outline="")
            # bar
            c.create_rectangle(x1, y1, x2, y2,
                               fill=color, outline="")
            # value label
            c.create_text((x1 + x2) // 2, y1 - 10,
                          text=str(value),
                          font=("Trebuchet MS", 11, "bold"),
                          fill=color, anchor="center")
            # x label
            c.create_text((x1 + x2) // 2, H - pad_b + 16,
                          text=label, font=FS,
                          fill=TEXT_MID, anchor="center")

        c.create_text(W // 2, 12,
                      text="Translation Statistics",
                      font=FH, fill=TEXT_DARK, anchor="center")

    # ── memory snapshot ───────────────────────────────────────────
    def _draw_memory(self, highlight=None):
        c  = self.mem_canvas
        c.delete("all")
        W  = c.winfo_width()  or 800
        H  = c.winfo_height() or 400
        nf = self.num_frames.get()

        cols  = max(8, min(16, W // 80))
        rows  = math.ceil(nf / cols)
        box_w = min(90, (W - 40) // cols)
        box_h = min(70, (H - 40) // max(rows, 1))
        x0    = (W - cols * box_w) // 2
        y0    = 20

        for fr in range(nf):
            col = fr % cols
            row = fr // cols
            x   = x0 + col * box_w
            y   = y0 + row * box_h

            info    = self.frame_usage.get(fr)
            is_last = info and info.get("last")

            if is_last:
                bg_c  = C_GRN
                fg_c  = WHITE
                brd_c = C_GRN
                bw    = 3
            elif info:
                bg_c  = C_GRN_L
                fg_c  = C_GRN
                brd_c = C_GRN
                bw    = 2
            else:
                bg_c  = BG2
                fg_c  = TEXT_LIGHT
                brd_c = BORDER
                bw    = 1

            c.create_rectangle(x + 4, y + 4, x + box_w - 4, y + box_h - 4,
                               fill=bg_c, outline=brd_c, width=bw)
            c.create_text(x + box_w // 2, y + box_h // 2 - 10,
                          text=f"Frame {fr}",
                          font=("Trebuchet MS", 9, "bold"),
                          fill=fg_c, anchor="center")
            if info:
                c.create_text(x + box_w // 2, y + box_h // 2 + 8,
                              text=f"← Page {info['page']}",
                              font=("Courier New", 8),
                              fill=fg_c, anchor="center")
            else:
                c.create_text(x + box_w // 2, y + box_h // 2 + 8,
                              text="Free",
                              font=FS, fill=TEXT_LIGHT, anchor="center")

        # footer
        used = len(self.frame_usage)
        c.create_text(W // 2, H - 12,
                      text=f"Frames Used: {used} / {nf}   |   "
                           f"Free: {nf - used}",
                      font=FS, fill=TEXT_LIGHT, anchor="center")

    # ── diagram ───────────────────────────────────────────────────
    def _draw_diagram(self, highlight=None):
        c = self.canvas
        c.delete("all")
        W = c.winfo_width() or 750
        H = c.winfo_height() or 320

        pages = min(len(self.page_table), 10)
        ps    = self.page_size.get()
        pad   = 28
        col   = (W - pad * 2) // 3
        rh    = max(22, (H - 68) // pages)
        y0    = 46

        for x, title, cc in [
            (pad + col // 2,          "Logical Pages",   C_BLUE),
            (pad + col + col // 2,    "Page Table",      C_PURP),
            (pad + col * 2 + col // 2,"Physical Frames", C_ORG),
        ]:
            c.create_rectangle(x - col // 2 + 6, 4,
                               x + col // 2 - 6, 34,
                               fill=cc, outline="")
            c.create_text(x, 19, text=title, fill=WHITE,
                          font=("Trebuchet MS", 10, "bold"),
                          anchor="center")

        for pg in range(pages):
            fr  = self.page_table.get(pg, "—")
            y   = y0 + pg * rh
            ym  = y + rh // 2
            hi  = (pg == highlight)
            bg_ = C_GRN_L  if hi else BG2
            tc_ = C_GRN    if hi else TEXT_DARK
            brd = C_GRN    if hi else BORDER
            bw  = 2 if hi else 1

            x1, x2 = pad, pad + col - 14
            c.create_rectangle(x1, y+2, x2, y+rh-2,
                               fill=bg_, outline=brd, width=bw)
            c.create_text((x1+x2)//2, ym,
                          text=f"Page {pg}   [{pg*ps} – {(pg+1)*ps-1}]",
                          fill=tc_, font=FM, anchor="center")
            c.create_line(x2, ym, x2+14, ym,
                          fill=C_BLUE if hi else TEXT_LIGHT,
                          width=2, arrow="last")

            x3, x4 = pad + col, pad + col * 2 - 14
            c.create_rectangle(x3, y+2, x4, y+rh-2,
                               fill=bg_, outline=brd, width=bw)
            c.create_text((x3+x4)//2, ym,
                          text=f"[{pg}]  ->  Frame {fr}",
                          fill=tc_, font=FM, anchor="center")
            c.create_line(x4, ym, x4+14, ym,
                          fill=C_BLUE if hi else TEXT_LIGHT,
                          width=2, arrow="last")

            x5, x6 = pad + col * 2, W - pad
            pa = fr * ps if isinstance(fr, int) else "—"
            c.create_rectangle(x5, y+2, x6, y+rh-2,
                               fill=bg_, outline=brd, width=bw)
            c.create_text((x5+x6)//2, ym,
                          text=f"Frame {fr}   [PA: {pa}]",
                          fill=tc_, font=FM, anchor="center")

        c.create_text(W//2, H-10,
                      text=f"Page Size: {ps} B   |   "
                           f"Offset bits: {int(math.log2(ps))}   |   "
                           f"Frames: {self.num_frames.get()}",
                      fill=TEXT_LIGHT, font=FS, anchor="center")

    # ── binary breakdown ──────────────────────────────────────────
    def _draw_binary(self, la, ps):
        c    = self.bin_canvas
        c.delete("all")
        W    = c.winfo_width() or 800
        bits = 16
        ob   = int(math.log2(ps))
        pb   = bits - ob
        la_b = format(la, f'0{bits}b')

        box_w = min(46, (W - 80) // bits)
        box_h = 52
        x0    = (W - bits * box_w) // 2
        y0    = 40

        for i, bit in enumerate(la_b):
            x   = x0 + i * box_w
            col = C_BLUE_L if i < pb else C_ORG_L
            brd = C_BLUE   if i < pb else C_ORG
            c.create_rectangle(x, y0, x + box_w, y0 + box_h,
                               fill=col, outline=brd, width=1)
            c.create_text(x + box_w // 2, y0 + box_h // 2,
                          text=bit,
                          font=("Courier New", 13, "bold"),
                          fill=C_BLUE if i < pb else C_ORG,
                          anchor="center")

        mx_page = x0 + pb * box_w // 2
        mx_off  = x0 + pb * box_w + ob * box_w // 2
        c.create_text(mx_page, y0 - 18,
                      text=f"Page Number  ({pb} bits)",
                      fill=C_BLUE, font=FH)
        c.create_text(mx_off, y0 - 18,
                      text=f"Offset  ({ob} bits)",
                      fill=C_ORG, font=FH)

        c.create_line(x0, y0 + box_h + 8,
                      x0 + pb * box_w, y0 + box_h + 8,
                      fill=C_BLUE, width=3)
        c.create_line(x0 + pb * box_w, y0 + box_h + 8,
                      x0 + bits * box_w, y0 + box_h + 8,
                      fill=C_ORG, width=3)

        pn  = la // ps
        off = la % ps
        self.bin_info.config(
            text=(
                f"Logical Address  : {la}   (binary: {la_b})\n"
                f"Page Number bits : {la_b[:pb]}   = {pn}\n"
                f"Offset bits      : {la_b[pb:]}   = {off}"
            )
        )

    # ── TLB helpers ───────────────────────────────────────────────
    def _refresh_tlb_tree(self):
        for r in self.tlb_tree.get_children():
            self.tlb_tree.delete(r)
        for slot, (pg, fr) in enumerate(self.tlb.items()):
            self.tlb_tree.insert("", "end",
                                 values=(slot, pg, fr, "Valid"))

    def _log_tlb(self, msg):
        self.tlb_log.config(state="normal")
        self.tlb_log.insert("end", msg)
        self.tlb_log.see("end")
        self.tlb_log.config(state="disabled")

    def _clear_tlb(self):
        self.tlb = {}
        self._refresh_tlb_tree()
        self.tlb_log.config(state="normal")
        self.tlb_log.delete("1.0", "end")
        self.tlb_log.config(state="disabled")

    def _clear_history(self):
        for r in self.tree.get_children():
            self.tree.delete(r)

    def _reset_all(self):
        self.stat_total = self.stat_hits = self.stat_misses = self.stat_faults = 0
        self.frame_usage = {}
        self._init_page_table()
        self._clear_history()
        self._clear_tlb()
        self.logical_addr.set("")
        self.anim_var.set("")
        self.res_var.set("Enter an address and click Translate.")
        self.res_lbl.config(bg=C_BLUE_L, fg=C_BLUE)
        self.bin_canvas.delete("all")
        self.bin_info.config(text="")
        self._update_stats()

    # ════════════════════════════════════════════════════════════
    #  HELPERS
    # ════════════════════════════════════════════════════════════
    def _card(self, parent, title, accent, expand=False):
        outer = tk.Frame(parent, bg=BORDER)
        outer.pack(fill="both", expand=expand, pady=(0, 10))
        top = tk.Frame(outer, bg=accent, padx=12, pady=6)
        top.pack(fill="x")
        tk.Label(top, text=title, font=FH, bg=accent, fg=WHITE).pack(anchor="w")
        inner = tk.Frame(outer, bg=PANEL, padx=12, pady=10)
        inner.pack(fill="both", expand=expand, padx=1, pady=(0, 1))
        return inner

    def _combo_row(self, parent, label, var, values):
        tk.Label(parent, text=label, font=FS,
                 bg=PANEL, fg=TEXT_MID).pack(anchor="w", pady=(8, 2))
        cb = ttk.Combobox(parent, textvariable=var,
                          values=values, state="readonly")
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", lambda e: self._init_page_table())

    def _btn(self, parent, text, color, cmd):
        tk.Button(parent, text=text, font=FB,
                  bg=color, fg=WHITE, relief="flat",
                  cursor="hand2", bd=0, padx=10, pady=6,
                  command=cmd).pack(fill="x", pady=(8, 0))

    def _btn_inline(self, parent, text, color, cmd):
        tk.Button(parent, text=text, font=FB,
                  bg=color, fg=WHITE, relief="flat",
                  cursor="hand2", bd=0, padx=10, pady=5,
                  command=cmd).pack(side="left")


if __name__ == "__main__":
    app = PagingSimulator()
    app.mainloop()
