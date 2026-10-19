# Membuat LUT .cube (33^3) untuk grading: komersial, sinematik, hangat, natural
import numpy as np, os
N = 33
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aset', 'lut')
os.makedirs(D, exist_ok=True)
def scurve(x, k):  # kontras filmik: toe & shoulder lembut
    return x + k * (x - 0.5) * (1 - np.abs(2*x - 1)) * 1.0
def luma(r, g, b): return 0.2126*r + 0.7152*g + 0.0722*b
def sat(r, g, b, s):
    y = luma(r, g, b); return y + (r-y)*s, y + (g-y)*s, y + (b-y)*s
def split(r, g, b, sh, hi, amt):
    y = luma(r, g, b); ws = np.clip(1 - y*2, 0, 1)**1.5; wh = np.clip(y*2 - 1, 0, 1)**1.2
    return (r + amt*(ws*sh[0] + wh*hi[0]), g + amt*(ws*sh[1] + wh*hi[1]), b + amt*(ws*sh[2] + wh*hi[2]))
def skin_protect(r0, g0, b0, r, g, b):
    # kurangi efek di rona kulit (r>g>b, hue oranye) agar warna kulit tetap wajar
    y = luma(r0, g0, b0) + 1e-6; h = (r0 > g0) & (g0 > b0) & ((r0 - b0) / y > 0.15) & ((r0 - b0) / y < 0.9)
    w = np.where(h, 0.55, 0.0)
    return r*(1-w) + r0*w*0.3 + r*w*0.7, g*(1-w) + g0*w*0.3 + g*w*0.7, b*(1-w) + b0*w*0.3 + b*w*0.7
LOOKS = {
    'komersial': dict(k=0.18, s=1.08, sh=(-0.01, 0.0, 0.02), hi=(0.03, 0.01, -0.02), amt=1.0, lift=0.01, gain=1.0),
    'sinematik': dict(k=0.28, s=0.92, sh=(-0.03, 0.01, 0.05), hi=(0.05, 0.015, -0.04), amt=1.0, lift=0.025, gain=0.97),
    'hangat':    dict(k=0.15, s=1.02, sh=(0.01, 0.0, -0.01), hi=(0.04, 0.02, -0.03), amt=1.0, lift=0.03, gain=0.99),
    'natural':   dict(k=0.10, s=1.04, sh=(0, 0, 0.01), hi=(0.01, 0.005, -0.005), amt=1.0, lift=0.0, gain=1.0),
}
g = np.linspace(0, 1, N)
B, G, R = np.meshgrid(g, g, g, indexing='ij')  # urutan .cube: R berubah paling cepat
for name, L in LOOKS.items():
    r, gg, b = R.copy(), G.copy(), B.copy()
    r, gg, b = [L['lift'] + (1 - L['lift']) * scurve(c, L['k']) * L['gain'] for c in (r, gg, b)]
    r, gg, b = split(r, gg, b, L['sh'], L['hi'], L['amt'])
    r, gg, b = sat(r, gg, b, L['s'])
    r, gg, b = skin_protect(R, G, B, r, gg, b)
    out = np.clip(np.stack([r, gg, b], -1), 0, 1).reshape(-1, 3)
    with open(f'{D}/{name}.cube', 'w') as f:
        f.write(f'TITLE "Barokah {name}"\nLUT_3D_SIZE {N}\n')
        for v in out: f.write(f'{v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n')
    print(name, 'ok')
