# Akses Google Drive: lewat "Jembatan Drive" (Apps Script milik pemilik Drive) untuk daftar/hapus/unggah;
# unduh mentahan lewat tautan publik folder. Tanpa jembatan: hanya bisa daftar + unduh (folder harus dibagikan via link).
import os, re, html, json, subprocess, requests

URL = lambda: os.environ.get('JEMBATAN_URL', '').strip()
KUNCI = lambda: os.environ.get('JEMBATAN_KEY', '').strip()
MENTAH = lambda: os.environ.get('FOLDER_MENTAH', '1C5-fxsVmE0-x3fxsp9OxT75CvZkyMJNk')
JADI = lambda: os.environ.get('FOLDER_JADI', '1dp-tc-rmc6EGWYj8xPgZRE7xEMMCsf-L')
VIDEO = re.compile(r'\.(mp4|mov|m4v|3gp|mkv|avi|webm|mts)$', re.I)

def ada(): return bool(URL() and KUNCI())

def panggil(aksi, **kw):
    r = requests.post(URL(), json=dict(kunci=KUNCI(), aksi=aksi, **kw), timeout=180)
    r.raise_for_status()
    try: j = r.json()
    except Exception: raise RuntimeError('Jembatan Drive tidak menjawab JSON: ' + r.text[:200])
    if not j.get('ok'): raise RuntimeError(f'Jembatan Drive ({aksi}): {j.get("galat")} {j.get("isi", "")}')
    return j

def daftar_publik(folder):
    r = requests.get(f'https://drive.google.com/embeddedfolderview?id={folder}', timeout=60); r.raise_for_status()
    out = []
    for m in re.finditer(r'id="entry-([\w-]+)".*?<div class="flip-entry-title">(.*?)</div>', r.text, re.S):
        out.append(dict(id=m.group(1), nama=html.unescape(m.group(2)).strip(), mime='', ukuran=0, dibuat=''))
    return out

def daftar_mentah():
    fs = panggil('daftar', folder=MENTAH())['file'] if ada() else daftar_publik(MENTAH())
    return [f for f in fs if VIDEO.search(f['nama']) or str(f.get('mime', '')).startswith('video/')]

def unduh(fid, path, log=print):
    url = f'https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t'
    tmp = path + '.part'
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        if 'text/html' in r.headers.get('Content-Type', ''):
            raise RuntimeError('Drive menolak unduhan (folder mentah harus dibagikan "Siapa saja yang memiliki link")')
        with open(tmp, 'wb') as f:
            for ch in r.iter_content(8 << 20): f.write(ch)
    ok = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width', '-of', 'csv=p=0', tmp],
                        capture_output=True, text=True)
    if ok.returncode != 0 or not ok.stdout.strip():
        os.remove(tmp); raise RuntimeError('file rusak / bukan video')
    os.replace(tmp, path)
    return os.path.getsize(path)

def hapus(fid): return panggil('hapus', id=fid)

def folder(nama, induk=None, bagikan=False): return panggil('folder', nama=nama, induk=induk or JADI(), bagikan=bagikan)

def unggah(path, folder_id, nama=None):
    nama = nama or os.path.basename(path); n = os.path.getsize(path)
    sesi = panggil('unggah', folder=folder_id, nama=nama, ukuran=n, mime='video/mp4')['sesi']
    with open(path, 'rb') as f:
        r = requests.put(sesi, data=f, headers={'Content-Length': str(n), 'Content-Type': 'video/mp4'}, timeout=1800)
    r.raise_for_status()
    j = r.json()
    return dict(id=j.get('id'), url=j.get('webViewLink') or f"https://drive.google.com/file/d/{j.get('id')}/view")
