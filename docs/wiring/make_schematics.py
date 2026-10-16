"""Draws the Vanitra wiring schematics (docs/wiring/*.svg + *.png).

    pip install cairosvg        # only needed for the PNG copies
    python docs/wiring/make_schematics.py

Pins are copied from firmware/glove_unit/config.h and firmware/wristband_unit/config.h.
If you change a pin there, change it here and re-run.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "Arial, Helvetica, sans-serif"
INK, MUTED, PAPER, PANEL = "#16202a", "#5b6670", "#ffffff", "#f3f6f9"
ACCENT, BOARD, BOARD_TXT = "#0e7c86", "#13213a", "#eef3f8"
NET = {"3V3": "#d93025", "5V": "#e8710a", "VBAT": "#b3261e", "GND": "#202124", "SDA": "#1a73e8",
       "SCL": "#188038", "ANA": "#00838f", "SIG": "#8e24aa", "I2S": "#3949ab", "PWR": "#6d4c41"}


class Sheet:
    def __init__(self, w, h, title, subtitle):
        self.w, self.h, self.o = w, h, []
        self.o.append(f'<rect width="{w}" height="{h}" fill="{PAPER}"/>')
        self.o.append(f'<rect width="{w}" height="8" fill="{ACCENT}"/>')
        self.text(40, 52, title, 26, INK, weight=700)
        self.text(40, 78, subtitle, 14, MUTED)

    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight=400, italic=False):
        s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        st = ' font-style="italic"' if italic else ""
        self.o.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
                      f'text-anchor="{anchor}" font-weight="{weight}"{st}>{s}</text>')

    def wire(self, pts, net, width=2.4, dash=False):
        d = " ".join(f"{x},{y}" for x, y in pts)
        da = ' stroke-dasharray="7 5"' if dash else ""
        self.o.append(f'<polyline points="{d}" fill="none" stroke="{NET[net]}" stroke-width="{width}" '
                      f'stroke-linejoin="round" stroke-linecap="round"{da}/>')

    def dot(self, x, y, net):
        self.o.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{NET[net]}"/>')

    def box(self, x, y, w, h, title, sub="", fill=PANEL, dash=False, title_size=15):
        da = ' stroke-dasharray="8 6"' if dash else ""
        self.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{INK}" stroke-width="2"{da}/>')
        self.text(x + w / 2, y + 24, title, title_size, INK, "middle", 700)
        if sub:
            self.text(x + w / 2, y + 42, sub, 11.5, MUTED, "middle")

    def pin(self, x, y, label, side):
        self.o.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" fill="#fff" stroke="{INK}" stroke-width="1.5"/>')
        dx, dy, anc = {"l": (10, 4, "start"), "r": (-10, 4, "end"), "t": (0, 18, "middle"), "b": (0, -10, "middle")}[side]
        self.text(x + dx, y + dy, label, 11.5, INK, anc, 600)

    def tag(self, x, y, name, net, side="r"):
        """Net label flag: wires with the same tag are connected."""
        c, w = NET[net], 14 + 7.4 * len(name)
        if side == "r":
            pts = f"{x},{y} {x+10},{y-11} {x+10+w},{y-11} {x+10+w},{y+11} {x+10},{y+11}"
            tx = x + 10 + w / 2
        else:
            pts = f"{x},{y} {x-10},{y-11} {x-10-w},{y-11} {x-10-w},{y+11} {x-10},{y+11}"
            tx = x - 10 - w / 2
        self.o.append(f'<polygon points="{pts}" fill="#fff" stroke="{c}" stroke-width="2"/>')
        self.text(tx, y + 4, name, 11.5, c, "middle", 700)

    def vcc(self, x, y, net="3V3"):
        c = NET[net]
        self.o.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-14}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x-11}" y1="{y-14}" x2="{x+11}" y2="{y-14}" stroke="{c}" stroke-width="3"/>')
        self.text(x, y - 20, net, 11, c, "middle", 700)

    def gnd(self, x, y):
        c = NET["GND"]
        self.o.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y+9}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x-11}" y1="{y+9}" x2="{x+11}" y2="{y+9}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x-6}" y1="{y+14}" x2="{x+6}" y2="{y+14}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x-2}" y1="{y+19}" x2="{x+2}" y2="{y+19}" stroke="{c}" stroke-width="2.4"/>')

    def resistor(self, x, y, length, vertical, label, net, label_side=1):
        c, n, amp = NET[net], 6, 6
        lead = (length - 30) / 2
        if vertical:
            pts = [(x, y), (x, y + lead)] + [(x + (amp if i % 2 == 0 else -amp), y + lead + 3 + i * 4.5) for i in range(n)]
            pts += [(x, y + lead + 30), (x, y + length)]
            self.text(x + 12 * label_side, y + length / 2 + 4, label, 11.5, INK, "start" if label_side > 0 else "end", 700)
            end = (x, y + length)
        else:
            pts = [(x, y), (x + lead, y)] + [(x + lead + 3 + i * 4.5, y + (amp if i % 2 == 0 else -amp)) for i in range(n)]
            pts += [(x + lead + 30, y), (x + length, y)]
            self.text(x + length / 2, y - 11, label, 11.5, INK, "middle", 700)
            end = (x + length, y)
        self.wire(pts, net, 2)
        return end

    def flex(self, x, y, length, label):
        """Flex sensor = variable resistor (box with an arrow), horizontal."""
        mid = x + length / 2
        self.wire([(x, y), (mid - 30, y)], "3V3", 2)
        self.wire([(mid + 30, y), (x + length, y)], "ANA", 2)
        self.o.append(f'<rect x="{mid-30}" y="{y-9}" width="60" height="18" rx="3" fill="#fff" stroke="{INK}" stroke-width="2"/>'
                      f'<line x1="{mid-22}" y1="{y+14}" x2="{mid+22}" y2="{y-14}" stroke="{INK}" stroke-width="1.6"/>'
                      f'<polygon points="{mid+22},{y-14} {mid+12},{y-12} {mid+18},{y-5}" fill="{INK}"/>')
        self.text(mid, y - 16, label, 11.5, INK, "middle", 700)

    def speaker(self, x, y):
        self.o.append(f'<rect x="{x}" y="{y-14}" width="14" height="28" fill="#fff" stroke="{INK}" stroke-width="2"/>'
                      f'<polygon points="{x+14},{y-14} {x+36},{y-32} {x+36},{y+32} {x+14},{y+14}" fill="#fff" stroke="{INK}" stroke-width="2"/>'
                      f'<path d="M{x+46},{y-14} q10,14 0,28 M{x+54},{y-22} q16,22 0,44" stroke="{MUTED}" stroke-width="2" fill="none"/>')

    def motor(self, x, y):
        self.o.append(f'<circle cx="{x}" cy="{y}" r="20" fill="#fff" stroke="{INK}" stroke-width="2.2"/>')
        self.text(x, y + 5, "M", 16, INK, "middle", 700)

    def diode(self, x, y, vertical=True):  # cathode at top
        if vertical:
            self.o.append(f'<polygon points="{x-10},{y+10} {x+10},{y+10} {x},{y-6}" fill="{INK}"/>'
                          f'<line x1="{x-10}" y1="{y-7}" x2="{x+10}" y2="{y-7}" stroke="{INK}" stroke-width="2.4"/>')

    def mosfet(self, x, y):
        """N-MOSFET, gate on the left at (x, y). Returns (drain, source) points."""
        c = INK
        self.o.append(f'<line x1="{x}" y1="{y}" x2="{x+22}" y2="{y}" stroke="{c}" stroke-width="2.2"/>'
                      f'<line x1="{x+22}" y1="{y-20}" x2="{x+22}" y2="{y+20}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x+30}" y1="{y-22}" x2="{x+30}" y2="{y+22}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x+30}" y1="{y-16}" x2="{x+50}" y2="{y-16}" stroke="{c}" stroke-width="2.2"/>'
                      f'<line x1="{x+30}" y1="{y+16}" x2="{x+50}" y2="{y+16}" stroke="{c}" stroke-width="2.2"/>'
                      f'<line x1="{x+50}" y1="{y-16}" x2="{x+50}" y2="{y-40}" stroke="{c}" stroke-width="2.2"/>'
                      f'<line x1="{x+50}" y1="{y+16}" x2="{x+50}" y2="{y+40}" stroke="{c}" stroke-width="2.2"/>'
                      f'<polygon points="{x+32},{y+16} {x+42},{y+11} {x+42},{y+21}" fill="{c}"/>')
        self.text(x + 58, y + 4, "AO3400", 11.5, INK, "start", 700)
        return (x + 50, y - 40), (x + 50, y + 40)

    def button(self, x, y, label):
        c = INK
        self.o.append(f'<line x1="{x}" y1="{y}" x2="{x+20}" y2="{y}" stroke="{c}" stroke-width="2.2"/>'
                      f'<line x1="{x+50}" y1="{y}" x2="{x+70}" y2="{y}" stroke="{c}" stroke-width="2.2"/>'
                      f'<circle cx="{x+20}" cy="{y}" r="3" fill="#fff" stroke="{c}" stroke-width="2"/>'
                      f'<circle cx="{x+50}" cy="{y}" r="3" fill="#fff" stroke="{c}" stroke-width="2"/>'
                      f'<line x1="{x+14}" y1="{y-12}" x2="{x+56}" y2="{y-12}" stroke="{c}" stroke-width="2.2"/>'
                      f'<line x1="{x+35}" y1="{y-12}" x2="{x+35}" y2="{y-22}" stroke="{c}" stroke-width="2.2"/>')
        self.text(x + 35, y - 28, label, 12, INK, "middle", 700)
        return (x + 70, y)

    def note(self, x, y, lines, w=380):
        h = 24 + 19 * len(lines)
        self.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#e8f6f7" stroke="{ACCENT}" stroke-width="2"/>')
        for i, s in enumerate(lines):
            self.text(x + 14, y + 23 + 19 * i, s, 12.5, INK, weight=700 if i == 0 else 400)

    def legend(self, x, y, nets):
        self.text(x, y + 4, "WIRES:", 11, MUTED, weight=700)
        xx = x + 60
        for net, lab in nets:
            self.wire([(xx, y), (xx + 26, y)], net, 3)
            self.text(xx + 34, y + 4, lab, 12, INK)
            xx += 52 + 7.0 * len(lab)

    def save(self, name):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}">' + "".join(self.o) + "</svg>")
        path = os.path.join(HERE, name + ".svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(HERE, name + ".png"), output_width=self.w)
            print("wrote", name + ".svg/.png")
        except ImportError:
            print("wrote", name + ".svg (pip install cairosvg for PNG)")


def board(s, x, y, w, h, title, sub, left, right):
    """Dev board with pins. left/right: list of (dy, label). Returns label -> outer pin point."""
    s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{BOARD}"/>')
    s.text(x + w / 2, y + 34, title, 16, BOARD_TXT, "middle", 700)
    s.text(x + w / 2, y + 54, sub, 11.5, "#7fd3d9", "middle", 600)
    P = {}
    for side, pins in (("l", left), ("r", right)):
        for dy, lab in pins:
            px = x if side == "l" else x + w
            py = y + dy
            s.o.append(f'<rect x="{px-5}" y="{py-5}" width="10" height="10" fill="#7fd3d9"/>')
            s.text(px + (12 if side == "l" else -12), py + 4, lab, 12, BOARD_TXT, "start" if side == "l" else "end", 600)
            P[lab] = (px - 5, py) if side == "l" else (px + 5, py)
    return P


def power_block(s, x, y, board_name, extra=""):
    """LiPo -> TP4056 -> switch -> MT3608 5 V. Drawn with net tags."""
    s.text(x, y - 14, "POWER  (same on both units)", 13, ACCENT, weight=700)
    s.box(x, y, 150, 70, "LiPo 3.7 V", "1S, 1000 mAh")
    s.box(x + 200, y, 170, 70, "TP4056 USB-C", "charger + protection")
    s.box(x + 430, y, 120, 70, "Switch", "slide SPDT")
    s.box(x + 600, y, 170, 70, "MT3608 boost", "set to 5.0 V first!")
    s.wire([(x + 150, y + 25), (x + 200, y + 25)], "VBAT")
    s.text(x + 175, y + 18, "B+", 11, NET["VBAT"], "middle", 700)
    s.wire([(x + 150, y + 50), (x + 200, y + 50)], "GND")
    s.wire([(x + 370, y + 25), (x + 430, y + 25)], "VBAT")
    s.text(x + 400, y + 18, "OUT+", 11, NET["VBAT"], "middle", 700)
    s.wire([(x + 550, y + 25), (x + 600, y + 25)], "VBAT")
    s.wire([(x + 770, y + 25), (x + 800, y + 25)], "5V")
    s.tag(x + 800, y + 25, "5V", "5V")
    s.wire([(x + 370, y + 50), (x + 380, y + 50), (x + 380, y + 100)], "GND")
    s.gnd(x + 380, y + 100)
    s.wire([(x + 400, y + 25), (x + 400, y + 110), (x + 470, y + 110)], "VBAT")
    s.dot(x + 400, y + 25, "VBAT")
    end = s.resistor(x + 470, y + 110, 100, False, "100k", "VBAT")
    s.dot(end[0], end[1], "VBAT")
    s.wire([end, (end[0] + 20, end[1])], "ANA")
    s.tag(end[0] + 20, end[1], "VBAT/2", "ANA")
    s.resistor(end[0], end[1], 60, True, "100k", "GND")
    s.gnd(end[0], end[1] + 60)
    s.text(x, y + 125, f"5V tag -> {board_name} 5V pin{extra}.", 12, MUTED)
    s.text(x, y + 143, "Never plug USB and the 5V boost in at the same time without a diode.", 12, MUTED, italic=True)


# ===================================================================== glove
def glove():
    s = Sheet(1900, 1390, "Vanitra glove unit — wiring schematic",
              "ESP32-S3-DevKitC-1 N16R8 · 5 flex + 4 SS49E Hall (analog, ADC1) · MPU6050 + OLED on I2C · "
              "MAX98357A I2S speaker amp · pins from firmware/glove_unit/config.h")
    bx, by = 760, 150
    fl_y = [140, 210, 280, 350, 420]
    ha_y = [520, 590, 660, 730]
    P = board(s, bx, by, 320, 900, "ESP32-S3-DevKitC-1", "N16R8 · glove (worn on the wrist)",
              left=[(60, "3V3")] + [(d, f"GPIO{g}") for d, g in zip(fl_y, [4, 5, 6, 7, 8])]
                   + [(d, f"GPIO{g}") for d, g in zip(ha_y, [9, 10, 1, 2])] + [(810, "GPIO3"), (860, "GND")],
              right=[(60, "5V"), (150, "GPIO16  SDA"), (200, "GPIO17  SCL"), (420, "GPIO12  BCLK"),
                     (470, "GPIO13  LRC"), (520, "GPIO14  DOUT"), (570, "GPIO21  AMP SD"),
                     (720, "GPIO0  BOOT btn (on board)"), (770, "GPIO48  RGB LED (on board)"), (860, "GND ")])

    # 3V3 rail on the far left
    rail_x = 110
    x3, y3 = P["3V3"]
    s.wire([(x3, y3), (rail_x, y3), (rail_x, by + ha_y[-1] + 10)], "3V3", 3)
    s.vcc(rail_x, y3)

    s.text(150, by + 105, "FLEX SENSORS  (2.2\" / 4.5\" Spectra-type)  3V3 -> flex -> pin -> 47 kΩ -> GND", 12.5, ACCENT, weight=700)
    fingers = ["thumb", "index", "middle", "ring", "little"]
    for (dy, g, name) in zip(fl_y, [4, 5, 6, 7, 8], fingers):
        y = by + dy
        s.dot(rail_x, y, "3V3")
        s.flex(rail_x, y, 230, f"Flex {name}")
        node = (440, y)
        s.wire([(rail_x + 230, y), node, P[f"GPIO{g}"]], "ANA")
        s.dot(*node, "ANA")
        s.resistor(node[0], y, 34, True, "47k", "GND")
        s.gnd(node[0], y + 34)

    s.text(150, by + 488, "SS49E LINEAR HALL SENSORS  (magnets on fingertips)  OUT -> ADC", 12.5, ACCENT, weight=700)
    places = ["H1 thumb tip", "H2 thumb side", "H3 palm centre", "H4 index-middle"]
    for (dy, g, name) in zip(ha_y, [9, 10, 1, 2], places):
        y = by + dy
        bx0 = 300
        s.o.append(f'<rect x="{bx0}" y="{y-24}" width="170" height="48" rx="6" fill="{PANEL}" stroke="{INK}" stroke-width="2"/>')
        s.text(bx0 + 85, y - 6, "SS49E", 13, INK, "middle", 700)
        s.text(bx0 + 85, y + 12, name, 11, MUTED, "middle")
        s.pin(bx0, y - 10, "VCC", "l")
        s.pin(bx0, y + 12, "GND", "l")
        s.pin(bx0 + 170, y, "OUT", "r")
        s.dot(rail_x, y - 10, "3V3")
        s.wire([(rail_x, y - 10), (bx0 - 4, y - 10)], "3V3")
        s.wire([(bx0 - 4, y + 12), (250, y + 12), (250, y + 22)], "GND")
        s.gnd(250, y + 22)
        s.wire([(bx0 + 174, y), P[f"GPIO{g}"]], "ANA")

    # battery sense + GND
    xg, yg = P["GPIO3"]
    s.wire([(xg, yg), (640, yg)], "ANA")
    s.tag(640, yg, "VBAT/2", "ANA", side="l")
    xg, yg = P["GND"]
    s.wire([(xg, yg), (700, yg), (700, yg + 16)], "GND")
    s.gnd(700, yg + 16)

    # 5V
    x5, y5 = P["5V"]
    s.wire([(x5, y5), (x5 + 40, y5)], "5V")
    s.tag(x5 + 40, y5, "5V", "5V")

    # I2C bus
    sda, scl = P["GPIO16  SDA"], P["GPIO17  SCL"]
    bus_x1, bus_x2 = 1180, 1205
    s.wire([sda, (bus_x1, sda[1]), (bus_x1, 420)], "SDA", 3)
    s.wire([scl, (bus_x2, scl[1]), (bus_x2, 420)], "SCL", 3)
    for i, (t, sub, dash) in enumerate([("MPU6050 (GY-521)", "accel + gyro · 0x68 · back of hand", False),
                                         ("SSD1306 OLED 0.96\"", "128×64 · 0x3C · optional", True)]):
        mx, my = 1290, 190 + i * 130
        s.box(mx, my, 300, 100, t, sub, dash=dash)
        for j, lab in enumerate(["VCC", "GND", "SCL", "SDA"]):
            py = my + 58 + j * 11 if False else my + 30 + j * 18
            s.pin(mx, py, lab, "l")
        s.wire([(mx - 4, my + 30), (mx - 40, my + 30)], "3V3", 2)
        s.vcc(mx - 40, my + 30)
        s.wire([(mx - 4, my + 48), (mx - 60, my + 48), (mx - 60, my + 60)], "GND", 2)
        s.gnd(mx - 60, my + 60)
        s.wire([(mx - 4, my + 66), (bus_x2, my + 66)], "SCL", 2)
        s.dot(bus_x2, my + 66, "SCL")
        s.wire([(mx - 4, my + 84), (bus_x1, my + 84)], "SDA", 2)
        s.dot(bus_x1, my + 84, "SDA")
    s.text(1290, 470, "MPU6050 AD0 -> GND (address 0x68). GY-521 has its own pull-ups.", 11.5, MUTED)

    # MAX98357A
    ax, ay = 1290, 540
    s.box(ax, ay, 300, 250, "MAX98357A", "I2S 3 W class-D amplifier")
    labs = ["BCLK", "LRC", "DIN", "SD", "GAIN", "VIN", "GND"]
    for j, lab in enumerate(labs):
        s.pin(ax, ay + 70 + j * 26, lab, "l")
    for lab, py in (("GPIO12  BCLK", ay + 70), ("GPIO13  LRC", ay + 96), ("GPIO14  DOUT", ay + 122), ("GPIO21  AMP SD", ay + 148)):
        p = P[lab]
        mid = 1150 + (py - ay) * 0.3
        s.wire([p, (mid, p[1]), (mid, py), (ax - 4, py)], "I2S")
    s.text(ax - 12, ay + 178, "open = 9 dB", 11, MUTED, "end")
    s.wire([(ax - 4, ay + 200), (ax - 60, ay + 200)], "5V")
    s.tag(ax - 60, ay + 200, "5V", "5V", side="l")
    s.wire([(ax - 4, ay + 226), (ax - 30, ay + 226), (ax - 30, ay + 240)], "GND")
    s.gnd(ax - 30, ay + 240)
    s.pin(ax + 300, ay + 100, "OUT+", "r")
    s.pin(ax + 300, ay + 160, "OUT−", "r")
    s.wire([(ax + 304, ay + 100), (ax + 350, ay + 100), (ax + 350, ay + 115)], "SIG")
    s.wire([(ax + 304, ay + 160), (ax + 350, ay + 160), (ax + 350, ay + 145)], "SIG")
    s.speaker(ax + 350, ay + 130)
    s.text(ax + 360, ay + 190, "speaker 4–8 Ω, 1–3 W", 11.5, MUTED)
    s.text(ax + 360, ay + 206, "at the cuff, facing out", 11.5, MUTED)

    s.note(1290, 830, ["Notes",
                       "• Only ADC1 pins are used for sensors (ADC2 is unreliable).",
                       "• Run the flex/Hall wires along the fingers with strain relief.",
                       "• Test each part first: firmware/tests/glove_sensor_monitor,",
                       "  i2c_scan, speaker_test.  Then calibrate: hold BOOT 2 s."], w=520)
    power_block(s, 150, 1150, "glove", " and MAX98357A VIN")
    s.legend(1060, 1240, [("3V3", "3V3"), ("5V", "5V"), ("VBAT", "battery"), ("GND", "GND"), ("ANA", "analog"),
                          ("SDA", "SDA"), ("SCL", "SCL"), ("I2S", "I2S")])
    s.save("glove_unit")


# ===================================================================== wristband
def wristband():
    s = Sheet(1700, 1220, "Vanitra wristband unit — wiring schematic",
              "ESP32-S3-DevKitC-1 N16R8 (PSRAM needed for ESP-SR) · INMP441 I2S mic · vibration motor on a MOSFET · "
              "button · optional OLED · pins from firmware/wristband_unit/config.h")
    bx, by = 640, 150
    P = board(s, bx, by, 320, 700, "ESP32-S3-DevKitC-1", "N16R8 · wristband",
              left=[(60, "3V3"), (170, "GPIO17  SCK"), (220, "GPIO47  WS"), (270, "GPIO16  SD in"),
                    (420, "GPIO5  button"), (560, "GPIO1  VBAT/2"), (640, "GND")],
              right=[(60, "5V"), (170, "GPIO8  SDA"), (220, "GPIO9  SCL"), (380, "GPIO4  PWM"),
                     (560, "GPIO48  RGB LED (on board)"), (640, "GND ")])

    # INMP441 — signal pins line up with the board pins
    mx, my = 150, 270
    s.box(mx, my, 260, 200, "INMP441", "I2S MEMS mic · hole facing out")
    for lab, bl in (("SCK", "GPIO17  SCK"), ("WS", "GPIO47  WS"), ("SD", "GPIO16  SD in")):
        py = P[bl][1]
        s.pin(mx + 260, py, lab, "r")
        s.wire([(mx + 264, py), P[bl]], "I2S")
    for j, (lab, net) in enumerate((("VDD", "3V3"), ("L/R", "GND"), ("GND", "GND"))):
        py = my + 90 + j * 34
        s.pin(mx, py, lab, "l")
        s.wire([(mx - 4, py), (mx - 40, py)], net, 2)
        if net == "3V3":
            s.vcc(mx - 40, py)
        else:
            s.wire([(mx - 40, py), (mx - 40, py + 12)], "GND", 2)
            s.gnd(mx - 40, py + 12)
    s.text(mx + 10, my + 190, "L/R -> GND = left channel", 11, MUTED)

    # button
    bp = P["GPIO5  button"]
    s.wire([bp, (520, bp[1])], "SIG")
    end = s.button(450, bp[1], "LISTEN button")
    s.wire([(450, bp[1]), (430, bp[1]), (430, bp[1] + 20)], "GND")
    s.gnd(430, bp[1] + 20)
    s.text(300, bp[1] + 50, "internal pull-up · tap / double tap / hold", 11, MUTED)

    # power pins
    x3, y3 = P["3V3"]
    s.wire([(x3, y3), (x3 - 40, y3)], "3V3")
    s.tag(x3 - 40, y3, "3V3", "3V3", side="l")
    vb = P["GPIO1  VBAT/2"]
    s.wire([vb, (vb[0] - 40, vb[1])], "ANA")
    s.tag(vb[0] - 40, vb[1], "VBAT/2", "ANA", side="l")
    g = P["GND"]
    s.wire([g, (g[0] - 30, g[1]), (g[0] - 30, g[1] + 14)], "GND")
    s.gnd(g[0] - 30, g[1] + 14)
    x5, y5 = P["5V"]
    s.wire([(x5, y5), (x5 + 40, y5)], "5V")
    s.tag(x5 + 40, y5, "5V", "5V")
    g2 = P["GND "]
    s.wire([g2, (g2[0] + 30, g2[1]), (g2[0] + 30, g2[1] + 14)], "GND")
    s.gnd(g2[0] + 30, g2[1] + 14)

    # OLED
    ox, oy = 1150, 270
    s.box(ox, oy, 300, 110, "SSD1306 OLED 0.96\"", "0x3C · optional (shows the text)", dash=True)
    for j, lab in enumerate(["VCC", "GND", "SCL", "SDA"]):
        s.pin(ox, oy + 38 + j * 18, lab, "l")
    s.wire([(ox - 4, oy + 38), (ox - 40, oy + 38)], "3V3", 2)
    s.vcc(ox - 40, oy + 38)
    s.wire([(ox - 4, oy + 56), (ox - 60, oy + 56), (ox - 60, oy + 70)], "GND", 2)
    s.gnd(ox - 60, oy + 70)
    sda, scl = P["GPIO8  SDA"], P["GPIO9  SCL"]
    s.wire([scl, (1080, scl[1]), (1080, oy + 74), (ox - 4, oy + 74)], "SCL")
    s.wire([sda, (1100, sda[1]), (1100, oy + 92), (ox - 4, oy + 92)], "SDA")

    # haptic driver
    gp = P["GPIO4  PWM"]
    gx, gy = 1150, gp[1] + 120
    s.wire([gp, (1040, gp[1]), (1040, gy)], "SIG")
    r_end = s.resistor(1040, gy, 70, False, "100 Ω", "SIG")
    s.wire([r_end, (gx, gy)], "SIG")
    s.dot(1080, gy, "SIG")
    s.resistor(1080, gy, 70, True, "100k", "GND", label_side=-1)
    s.gnd(1080, gy + 70)
    drain, source = s.mosfet(gx, gy)
    s.wire([source, (source[0], source[1] + 10)], "GND")
    s.gnd(source[0], source[1] + 10)
    my_ = drain[1] - 60
    s.wire([drain, (drain[0], my_ + 20)], "PWR")
    s.motor(drain[0], my_)
    s.wire([(drain[0], my_ - 20), (drain[0], my_ - 70)], "3V3")
    s.vcc(drain[0], my_ - 70)
    dx = drain[0] + 80
    s.wire([(drain[0], my_ - 45), (dx, my_ - 45), (dx, my_ - 8)], "3V3", 2)
    s.diode(dx, my_)
    s.wire([(dx, my_ + 10), (dx, drain[1] + 10), (drain[0], drain[1] + 10)], "PWR", 2)
    s.dot(drain[0], drain[1] + 10, "PWR")
    s.dot(drain[0], my_ - 45, "3V3")
    s.text(dx + 16, my_ + 4, "1N4148 / 1N5819", 11.5, INK, weight=700)
    s.text(drain[0] - 28, my_ - 4, "coin ERM 3 V", 11.5, INK, "end", weight=700)
    s.text(drain[0] - 28, my_ + 12, "10 mm, inner wrist", 11, MUTED, "end")
    s.text(1040, gy + 100, "Logic-level N-MOSFET (AO3400 / SI2302).  2N2222 + 1 kΩ base resistor also works.", 11.5, MUTED)

    s.note(1040, 790, ["Notes",
                      "• ESP-SR needs the N16R8 board (8 MB PSRAM) and the",
                      "  'ESP SR 16M' partition — see docs/setup.md.",
                      "• Keep the mic away from the motor; the firmware",
                      "  pauses listening while the motor vibrates.",
                      "• Test: mic_level_test, haptic_test, i2c_scan (8/9)."], w=430)
    power_block(s, 150, 950, "wristband")
    s.legend(1000, 1110, [("3V3", "3V3"), ("5V", "5V"), ("GND", "GND"), ("I2S", "I2S"), ("SIG", "signal"),
                          ("SDA", "SDA"), ("SCL", "SCL")])
    s.save("wristband_unit")


# ===================================================================== overview
def overview():
    s = Sheet(1680, 560, "Vanitra — system overview",
              "Two independent wearables, both fully offline. Glove: signer -> listener. Wristband: listener -> signer.")

    def flow(y, title, items, colour):
        s.text(60, y - 18, title, 15, colour, weight=700)
        x = 60
        for i, (t, sub) in enumerate(items):
            w = 222
            s.box(x, y, w, 64, t, sub, title_size=14)
            if i < len(items) - 1:
                s.o.append(f'<line x1="{x+w}" y1="{y+32}" x2="{x+w+34}" y2="{y+32}" stroke="{colour}" stroke-width="3"/>'
                           f'<polygon points="{x+w+34},{y+24} {x+w+46},{y+32} {x+w+34},{y+40}" fill="{colour}"/>')
            x += w + 46

    flow(150, "GLOVE UNIT — sign to speech (ESP32-S3 #1)", [
        ("Sensors @ 50 Hz", "5 flex · 4 Hall · MPU6050"),
        ("Calibrate", "flex 0..1 · Hall 0/1 · gyro bias"),
        ("0.5 s window", "16 features (shape + motion)"),
        ("Neural net", "16-32-21 on chip, <1 ms"),
        ("Gate", "p ≥ 0.85 · 3× stable · cooldown"),
        ("Speak", "WAV clip -> MAX98357A + OLED")], ACCENT)
    flow(290, "WRISTBAND UNIT — speech to touch (ESP32-S3 #2)", [
        ("INMP441 mic", "16 kHz I2S"),
        ("WakeNet", "\"Hi ESP\" or LISTEN button"),
        ("MultiNet", "49 phrases -> 22 meanings"),
        ("Short code", "\"are you okay\" -> OK?"),
        ("Morse timeline", "dot 90/120/160 ms"),
        ("Vibrate", "ERM motor + OLED text")], "#3949ab")
    s.note(60, 400, ["Design choices (details in docs/decisions.md)",
                     "• No cloud, no phone: all recognition runs on the two ESP32-S3 chips.",
                     "• Wristband recognises a fixed phrase list (ESP-SR), not open dictation — reliable offline.",
                     "• Messages are vibrated as short codes (HI, OK?, WATER?), not full sentences: 1-8 s each at normal speed."], w=820)
    s.save("system_overview")


if __name__ == "__main__":
    overview()
    glove()
    wristband()
