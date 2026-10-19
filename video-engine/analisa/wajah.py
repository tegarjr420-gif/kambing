import cv2, glob, os, json
cas = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
prof = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
out = {}
names = sorted({os.path.basename(p).rsplit('_',1)[0] for p in glob.glob('px/*.jpg')})
for n in names:
    rows = []
    for p in sorted(glob.glob(f'px/{n}_*.jpg')):
        t = (int(os.path.basename(p).rsplit('_',1)[1][:4]) - 1) / 2
        im = cv2.imread(p); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY); H, W = g.shape
        f = cas.detectMultiScale(g, 1.1, 5, minSize=(int(W*0.03), int(W*0.03)))
        if len(f) == 0: f = prof.detectMultiScale(g, 1.1, 5, minSize=(int(W*0.03), int(W*0.03)))
        if len(f):
            x, y, w, h = max(f, key=lambda r: r[2]*r[3])
            rows.append([t, round((x+w/2)/W, 3), round((y+h/2)/H, 3), round(w/W, 3)])
    out[n] = rows
    print(n, len(rows), 'wajah', [r[1] for r in rows[:12]])
json.dump(out, open('wajah.json', 'w'))
