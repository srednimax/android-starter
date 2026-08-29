"""Material Color Utilities: HCT (CAM16 + L*) and tonal palettes, enough to
generate a full M3 scheme from seed colours. Offline; no dependencies.

Ported from google/material-color-utilities (Apache-2.0), the pre-HctSolver
iterative gamut mapping, which is accurate to the same rounded 8-bit output.
"""
import math

# ---------- sRGB <-> XYZ (D65) ----------

SRGB_TO_XYZ = [
    [0.41233895, 0.35762064, 0.18051042],
    [0.2126, 0.7152, 0.0722],
    [0.01932141, 0.11916382, 0.95034478],
]
XYZ_TO_SRGB = [
    [3.2413774792388685, -1.5376652402851851, -0.49885366846268053],
    [-0.9691452513005321, 1.8758853451067872, 0.04156585616912061],
    [0.05562093689691305, -0.20395524564742123, 1.0571799111220335],
]
WHITE_POINT_D65 = [95.047, 100.0, 108.883]


def _linearized(rgb8):
    n = rgb8 / 255.0
    if n <= 0.040449936:
        return n / 12.92 * 100.0
    return ((n + 0.055) / 1.055) ** 2.4 * 100.0


def _delinearized(rgb_lin):
    n = rgb_lin / 100.0
    if n <= 0.0031308:
        v = n * 12.92
    else:
        v = 1.055 * (n ** (1.0 / 2.4)) - 0.055
    return max(0, min(255, round(v * 255.0)))


def argb_from_rgb(r, g, b):
    return (255 << 24) | (r << 16) | (g << 8) | b


def rgb_from_argb(argb):
    return ((argb >> 16) & 255, (argb >> 8) & 255, argb & 255)


def hex_from_argb(argb):
    r, g, b = rgb_from_argb(argb)
    return "%02X%02X%02X" % (r, g, b)


def argb_from_hex(h):
    h = h.lstrip("#")
    return argb_from_rgb(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def xyz_from_argb(argb):
    r, g, b = rgb_from_argb(argb)
    lr, lg, lb = _linearized(r), _linearized(g), _linearized(b)
    return [
        SRGB_TO_XYZ[i][0] * lr + SRGB_TO_XYZ[i][1] * lg + SRGB_TO_XYZ[i][2] * lb
        for i in range(3)
    ]


def argb_from_xyz(x, y, z):
    out = []
    for i in range(3):
        out.append(XYZ_TO_SRGB[i][0] * x + XYZ_TO_SRGB[i][1] * y + XYZ_TO_SRGB[i][2] * z)
    return argb_from_rgb(*[_delinearized(v) for v in out])


def y_from_lstar(lstar):
    if lstar > 8.0:
        return ((lstar + 16.0) / 116.0) ** 3 * 100.0
    return lstar / 903.2962962962963 * 100.0


def lstar_from_y(y):
    yn = y / 100.0
    if yn <= 216.0 / 24389.0:
        return 903.2962962962963 * yn
    return 116.0 * (yn ** (1.0 / 3.0)) - 16.0


def lstar_from_argb(argb):
    return lstar_from_y(xyz_from_argb(argb)[1])


def argb_from_lstar(lstar):
    y = y_from_lstar(lstar)
    c = _delinearized(y)
    return argb_from_rgb(c, c, c)


def _signum(v):
    return -1 if v < 0 else (1 if v > 0 else 0)


# ---------- viewing conditions ----------

class ViewingConditions:
    def __init__(self):
        wp = WHITE_POINT_D65
        adapting_luminance = 200.0 / math.pi * y_from_lstar(50.0) / 100.0
        background_lstar = 50.0
        surround = 2.0
        discounting = False

        r_w = wp[0] * 0.401288 + wp[1] * 0.650173 + wp[2] * -0.051461
        g_w = wp[0] * -0.250268 + wp[1] * 1.204414 + wp[2] * 0.045854
        b_w = wp[0] * -0.002079 + wp[1] * 0.048952 + wp[2] * 0.953127

        f = 0.8 + surround / 10.0
        if f >= 0.9:
            t = (f - 0.9) * 10.0
            c = 0.59 + (0.69 - 0.59) * t
        else:
            t = (f - 0.8) * 10.0
            c = 0.525 + (0.59 - 0.525) * t
        if discounting:
            d = 1.0
        else:
            d = f * (1.0 - (1.0 / 3.6) * math.exp((-adapting_luminance - 42.0) / 92.0))
        d = max(0.0, min(1.0, d))
        nc = f
        rgb_d = [
            d * (100.0 / r_w) + 1.0 - d,
            d * (100.0 / g_w) + 1.0 - d,
            d * (100.0 / b_w) + 1.0 - d,
        ]
        k = 1.0 / (5.0 * adapting_luminance + 1.0)
        k4 = k ** 4
        k4f = 1.0 - k4
        fl = k4 * adapting_luminance + 0.1 * k4f * k4f * ((5.0 * adapting_luminance) ** (1.0 / 3.0))
        n = y_from_lstar(background_lstar) / wp[1]
        z = 1.48 + math.sqrt(n)
        nbb = 0.725 / (n ** 0.2)
        ncb = nbb
        rgb_a_factors = [
            ((fl * rgb_d[0] * r_w) / 100.0) ** 0.42,
            ((fl * rgb_d[1] * g_w) / 100.0) ** 0.42,
            ((fl * rgb_d[2] * b_w) / 100.0) ** 0.42,
        ]
        rgb_a = [
            (400.0 * rgb_a_factors[0]) / (rgb_a_factors[0] + 27.13),
            (400.0 * rgb_a_factors[1]) / (rgb_a_factors[1] + 27.13),
            (400.0 * rgb_a_factors[2]) / (rgb_a_factors[2] + 27.13),
        ]
        aw = (40.0 * rgb_a[0] + 20.0 * rgb_a[1] + rgb_a[2]) / 20.0 * nbb

        self.n = n
        self.aw = aw
        self.nbb = nbb
        self.ncb = ncb
        self.c = c
        self.nc = nc
        self.rgb_d = rgb_d
        self.fl = fl
        self.fl_root = fl ** 0.25
        self.z = z


VC = ViewingConditions()


# ---------- CAM16 ----------

class Cam16:
    def __init__(self, hue, chroma, j, m):
        self.hue = hue
        self.chroma = chroma
        self.j = j
        self.m = m

    @staticmethod
    def from_argb(argb):
        x, y, z = xyz_from_argb(argb)
        r_c = 0.401288 * x + 0.650173 * y - 0.051461 * z
        g_c = -0.250268 * x + 1.204414 * y + 0.045854 * z
        b_c = -0.002079 * x + 0.048952 * y + 0.953127 * z

        r_d = VC.rgb_d[0] * r_c
        g_d = VC.rgb_d[1] * g_c
        b_d = VC.rgb_d[2] * b_c

        r_af = ((VC.fl * abs(r_d)) / 100.0) ** 0.42
        g_af = ((VC.fl * abs(g_d)) / 100.0) ** 0.42
        b_af = ((VC.fl * abs(b_d)) / 100.0) ** 0.42
        r_a = _signum(r_d) * 400.0 * r_af / (r_af + 27.13)
        g_a = _signum(g_d) * 400.0 * g_af / (g_af + 27.13)
        b_a = _signum(b_d) * 400.0 * b_af / (b_af + 27.13)

        a = (11.0 * r_a + -12.0 * g_a + b_a) / 11.0
        b = (r_a + g_a - 2.0 * b_a) / 9.0
        u = (20.0 * r_a + 20.0 * g_a + 21.0 * b_a) / 20.0
        p2 = (40.0 * r_a + 20.0 * g_a + b_a) / 20.0

        atan_degrees = math.degrees(math.atan2(b, a))
        hue = atan_degrees % 360.0

        hue_rad = math.radians(hue)
        ac = p2 * VC.nbb
        j = 100.0 * ((ac / VC.aw) ** (VC.c * VC.z))
        hue_prime = hue + 360.0 if hue < 20.14 else hue
        e_hue = 0.25 * (math.cos(math.radians(hue_prime) + 2.0) + 3.8)
        p1 = 50000.0 / 13.0 * e_hue * VC.nc * VC.ncb
        t = p1 * math.hypot(a, b) / (u + 0.305)
        alpha = (t ** 0.9) * ((1.64 - (0.29 ** VC.n)) ** 0.73)
        c = alpha * math.sqrt(j / 100.0)
        m = c * VC.fl_root
        return Cam16(hue, c, j, m)

    @staticmethod
    def from_jch(j, c, h):
        m = c * VC.fl_root
        return Cam16(h, c, j, m)

    def to_argb(self):
        alpha = 0.0 if (self.chroma == 0.0 or self.j == 0.0) else self.chroma / math.sqrt(self.j / 100.0)
        t = (alpha / ((1.64 - (0.29 ** VC.n)) ** 0.73)) ** (1.0 / 0.9)
        h_rad = math.radians(self.hue)
        e_hue = 0.25 * (math.cos(h_rad + 2.0) + 3.8)
        ac = VC.aw * ((self.j / 100.0) ** (1.0 / VC.c / VC.z))
        p1 = e_hue * (50000.0 / 13.0) * VC.nc * VC.ncb
        p2 = ac / VC.nbb
        h_sin = math.sin(h_rad)
        h_cos = math.cos(h_rad)
        gamma = 23.0 * (p2 + 0.305) * t / (23.0 * p1 + 11.0 * t * h_cos + 108.0 * t * h_sin)
        a = gamma * h_cos
        b = gamma * h_sin
        r_a = (460.0 * p2 + 451.0 * a + 288.0 * b) / 1403.0
        g_a = (460.0 * p2 - 891.0 * a - 261.0 * b) / 1403.0
        b_a = (460.0 * p2 - 220.0 * a - 6300.0 * b) / 1403.0

        def inv(ca):
            base = max(0.0, (27.13 * abs(ca)) / (400.0 - abs(ca)))
            return _signum(ca) * (100.0 / VC.fl) * (base ** (1.0 / 0.42))

        r_c, g_c, b_c = inv(r_a), inv(g_a), inv(b_a)
        r_f = r_c / VC.rgb_d[0]
        g_f = g_c / VC.rgb_d[1]
        b_f = b_c / VC.rgb_d[2]

        x = 1.86206786 * r_f - 1.01125463 * g_f + 0.14918677 * b_f
        y = 0.38752654 * r_f + 0.62144744 * g_f - 0.00897398 * b_f
        z = -0.01584150 * r_f - 0.03412294 * g_f + 1.04996444 * b_f
        return argb_from_xyz(x, y, z)

    # CAM16-UCS coordinates: the perceptually uniform form, which is what
    # distance() must compare. Comparing raw J/M/hue instead silently breaks
    # the gamut search for low-chroma colours.
    @property
    def jstar(self):
        return (1.0 + 100.0 * 0.007) * self.j / (1.0 + 0.007 * self.j)

    @property
    def mstar(self):
        return 1.0 / 0.0228 * math.log(1.0 + 0.0228 * self.m)

    @property
    def astar(self):
        return self.mstar * math.cos(math.radians(self.hue))

    @property
    def bstar(self):
        return self.mstar * math.sin(math.radians(self.hue))

    def distance(self, other):
        d_j = self.jstar - other.jstar
        d_a = self.astar - other.astar
        d_b = self.bstar - other.bstar
        d_e_prime = math.sqrt(d_j * d_j + d_a * d_a + d_b * d_b)
        return 1.41 * (d_e_prime ** 0.63)


# ---------- HCT ----------

def _find_cam_by_j(hue, chroma, tone):
    low, high = 0.0, 100.0
    best_dl, best_de, best_cam = 1000.0, 1000.0, None
    while abs(low - high) > 0.01:
        mid = low + (high - low) / 2.0
        clipped = Cam16.from_jch(mid, chroma, hue).to_argb()
        clipped_lstar = lstar_from_argb(clipped)
        d_l = abs(tone - clipped_lstar)
        if d_l < 0.2:
            cam_clipped = Cam16.from_argb(clipped)
            d_e = cam_clipped.distance(Cam16.from_jch(cam_clipped.j, cam_clipped.chroma, hue))
            if d_e <= 1.0 and d_e <= best_de:
                best_dl, best_de, best_cam = d_l, d_e, cam_clipped
        if best_dl == 0.0 and best_de == 0.0:
            break
        if clipped_lstar < tone:
            low = mid
        else:
            high = mid
    return best_cam


def hct_to_argb(hue, chroma, tone):
    """Gamut-map (hue, chroma, tone) to the nearest displayable sRGB colour."""
    if chroma < 1.0 or round(tone) <= 0.0 or round(tone) >= 100.0:
        return argb_from_lstar(tone)
    hue = hue % 360.0
    high = chroma
    mid = chroma
    low = 0.0
    is_first = True
    answer = None
    while abs(low - high) >= 0.4:
        cam = _find_cam_by_j(hue, mid, tone)
        if is_first:
            if cam is not None:
                return cam.to_argb()
            is_first = False
            mid = low + (high - low) / 2.0
            continue
        if cam is None:
            high = mid
        else:
            answer = cam
            low = mid
        mid = low + (high - low) / 2.0
    if answer is None:
        return argb_from_lstar(tone)
    return answer.to_argb()


class TonalPalette:
    def __init__(self, hue, chroma):
        self.hue = hue
        self.chroma = chroma
        self._cache = {}

    @staticmethod
    def from_argb(argb):
        cam = Cam16.from_argb(argb)
        return TonalPalette(cam.hue, cam.chroma)

    @staticmethod
    def from_hue_and_chroma(hue, chroma):
        return TonalPalette(hue, chroma)

    def tone(self, t):
        if t not in self._cache:
            self._cache[t] = hct_to_argb(self.hue, self.chroma, float(t))
        return self._cache[t]

    def hexes(self, t):
        return hex_from_argb(self.tone(t))
