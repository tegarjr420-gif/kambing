# Deteksi wajah di video hasil: laporkan posisi x tiap 0.5 dtk (ideal 0.3-0.7)
import cv2, sys, subprocess, glob, os
f = sys.argv[1]; d = '/tmp/cw'; os.makedirs(d, exist_ok=True)
for p in glob.glob(d + '/*.jpg'): os.remove(p)
subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', f, '-vf', 'fps=2,scale=360:640', d + '/f_%03d.jpg'])
cas = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
bad = []
for p in sorted(glob.glob(d + '/*.jpg')):
    t = (int(p[-7:-4]) - 1) / 2; g = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2GRAY)
    fs = [r for r in cas.detectMultiScale(g, 1.1, 6, minSize=(50, 50))]
    if fs:
        x, y, w, h = max(fs, key=lambda r: r[2]*r[3]); cx = (x + w/2) / 360
        flag = '' if 0.28 <= cx <= 0.72 and x > 0 and x + w < 360 else '  <-- TEPI'
        if flag: bad.append(t)
        print(f'{t:5.1f}s wajah x={cx:.2f}{flag}')
print('TEPI:', bad)
