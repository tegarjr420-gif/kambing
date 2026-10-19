# Dengarkan ulang hasil akhir: transkrip audio di jendela waktu tiap baris subtitle, bandingkan teksnya
import sys, re, subprocess, numpy as np, difflib, sherpa_onnx
K = '/tmp/claude-0/-home-claude/8530fe1f-175c-5546-b869-127bbb89636c/scratchpad/video-kit/asr/sherpa-onnx-whisper-turbo/'
wh = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=K+'turbo-encoder.int8.onnx', decoder=K+'turbo-decoder.int8.onnx', tokens=K+'turbo-tokens.txt', language='id', task='transcribe', num_threads=2)
mp4, ass = sys.argv[1], sys.argv[2]
raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', mp4, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout
y = np.frombuffer(raw, np.float32)
ts = lambda s: sum(float(x) * m for x, m in zip(s.split(':'), (3600, 60, 1)))
rows = []
for L in open(ass):
    if L.startswith('Dialogue: 2,'):
        p = L.split(',', 9); a, b = ts(p[1]), ts(p[2]); txt = re.sub(r'\{[^}]*\}', '', p[9]).strip()
        if not rows or rows[-1][2] != txt or abs(rows[-1][1] - a) > 0.05: rows.append([a, b, txt])
        else: rows[-1][1] = b
norm = lambda s: re.sub(r'[^a-z0-9 ]', '', s.lower()).split()
skor = []
for a, b, txt in rows:
    seg = y[int(max(0, a - 0.05) * 16000):int((b + 0.05) * 16000)] * 2
    s = wh.create_stream(); s.accept_waveform(16000, seg); wh.decode_stream(s); heard = s.result.text.strip()
    r = difflib.SequenceMatcher(None, norm(txt), norm(heard)).ratio(); skor.append(r)
    print(f'{a:6.2f}-{b:5.2f} {r:4.2f} | sub: {txt} | dengar: {heard}')
print('RATA-RATA KECOCOKAN', round(float(np.mean(skor)), 2))
