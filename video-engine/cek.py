# python3 cek.py out/file.mp4 [langkah_detik] -> cek/<nama>.jpg (contact sheet) + info loudness
import sys, subprocess, os, glob, re
from PIL import Image, ImageDraw
f = sys.argv[1]; step = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
n = os.path.basename(f)[:-4]; d = f'cek/{n}'; os.makedirs(d, exist_ok=True)
for p in glob.glob(f'{d}/*.jpg'): os.remove(p)
subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', f, '-vf', f'fps=1/{step},scale=270:480', '-q:v', '4', f'{d}/f_%03d.jpg'])
fr = sorted(glob.glob(f'{d}/f_*.jpg')); cols = 8; rows = (len(fr)+cols-1)//cols
S = Image.new('RGB', (cols*270, rows*496), 'black'); dr = ImageDraw.Draw(S)
for i, p in enumerate(fr):
    x, y = (i % cols)*270, (i//cols)*496
    S.paste(Image.open(p), (x, y+16)); dr.text((x+4, y+2), f'{i*step:.1f}s', fill='yellow')
S.save(f'cek/{n}.jpg', quality=82)
o = subprocess.run(['ffmpeg', '-hide_banner', '-i', f, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
print(n, 'I', re.findall(r'I:\s+(-?[\d.]+) LUFS', o)[-1], 'LRA', re.findall(r'LRA:\s+([\d.]+)', o)[-1], 'peak', re.findall(r'Peak:\s+(-?[\d.]+)', o)[-1], 'frames', len(fr))
