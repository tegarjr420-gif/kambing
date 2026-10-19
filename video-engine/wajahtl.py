# Peta wajah pada video hasil (sebelum teks dibakar): dipakai agar tulisan tidak menutupi muka.
import subprocess, json, os, numpy as np, cv2

E = os.path.dirname(os.path.abspath(__file__))
MODEL = f'{E}/aset/model/yunet.onnx'

def peta_wajah(video, W, H, fps=5.0, lebar=480):
    """-> list (t, [[x0,y0,x1,y1], ...]) dalam piksel kanvas W x H; kotak sudah diperluas (rambut, dagu)."""
    w = lebar if W >= H else int(lebar * W / H) // 2 * 2
    h = int(round(w * H / W)) // 2 * 2
    raw = subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-i', video, '-vf', f'fps={fps},scale={w}:{h}',
                          '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    det = cv2.FaceDetectorYN.create(MODEL, '', (w, h), score_threshold=0.62, nms_threshold=0.3, top_k=20)
    sx, sy = W / w, H / h; out = []
    for i in range(n):
        fr = np.frombuffer(raw, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3)
        _, fs = det.detect(fr)
        boxes = []
        for f in (fs if fs is not None else []):
            x, y, bw, bh = [float(v) for v in f[:4]]
            if bw * bh < (w * h) * 0.0012: continue           # wajah sangat kecil di latar: abaikan
            if bh > 0.42 * h or bw > 0.6 * w: continue         # deteksi raksasa = salah (biasanya saat transisi)
            x0 = (x - 0.30 * bw) * sx; x1 = (x + 1.30 * bw) * sx  # perluas: telinga, rambut, topi, dagu
            y0 = (y - 0.55 * bh) * sy; y1 = (y + 1.25 * bh) * sy
            boxes.append([round(max(0, x0)), round(max(0, y0)), round(min(W, x1)), round(min(H, y1))])
        out.append((round(i / fps, 2), boxes))
    # buang deteksi sesaat (muncul di 1 sampel saja, tanpa tetangga yang tumpang-tindih)
    def dekat(b, bs): return any(min(b[2], c[2]) > max(b[0], c[0]) and min(b[3], c[3]) > max(b[1], c[1]) for c in bs)
    bersih = []
    for i, (t, bs) in enumerate(out):
        tet = (out[i-1][1] if i else []) + (out[i+1][1] if i + 1 < len(out) else [])
        bersih.append((t, [b for b in bs if dekat(b, tet)]))
    return bersih

def tabrakan(peta, a, b, kotak):
    """rata-rata luas tumpang-tindih (relatif luas kotak teks) selama a..b"""
    X0, Y0, X1, Y1 = kotak; luas = max(1.0, (X1 - X0) * (Y1 - Y0)); tot = 0.0; n = 0
    for t, bs in peta:
        if t < a - 0.1 or t > b + 0.1: continue
        n += 1
        for x0, y0, x1, y1 in bs:
            ix = max(0, min(X1, x1) - max(X0, x0)); iy = max(0, min(Y1, y1) - max(Y0, y0))
            tot += ix * iy / luas
    return tot / n if n else 0.0

if __name__ == '__main__':
    import sys
    W, H = int(sys.argv[2]), int(sys.argv[3])
    p = peta_wajah(sys.argv[1], W, H)
    print(json.dumps(p[:20])); print(len(p), 'sampel,', sum(1 for _, b in p if b), 'dengan wajah')

_bk = {}
def keramaian(video, W, H, t, kotak, lebar=480):
    """0..1 seberapa ramai (banyak tepi/detail) latar di dalam kotak pada detik t; teks lebih terbaca di area tenang"""
    key = round(t, 1)
    if key not in _bk:
        h = int(round(lebar * H / W)) // 2 * 2
        raw = subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-ss', f'{t:.2f}', '-i', video, '-frames:v', '1',
                              '-vf', f'scale={lebar}:{h},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
        if len(raw) < lebar * h: return 0.0
        g = np.frombuffer(raw, np.uint8, lebar * h).reshape(h, lebar).astype(np.float32)
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        _bk[key] = (np.sqrt(gx * gx + gy * gy), lebar / W)
    mag, s = _bk[key]
    x0, y0, x1, y1 = [int(max(0, v * s)) for v in kotak]
    m = mag[y0:max(y0 + 1, y1), x0:max(x0 + 1, x1)]
    return float(min(1.0, m.mean() / 120.0)) if m.size else 0.0
