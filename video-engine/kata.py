# Waktu per kata: teks Whisper (akurat) + waktu token Dolphin CTC (presisi), diselaraskan.
# kata_klip(nama) -> [{'w': 'Kenalin,', 't0': 0.31, 't1': 0.72}, ...] waktu relatif sumber.
import json, os, re, difflib
ANA = os.environ.get('ANA', '/tmp/claude-0/-home-claude/8530fe1f-175c-5546-b869-127bbb89636c/scratchpad/ana')
KOREKSI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'koreksi.json')

def norm(w):
    return re.sub(r'[^0-9a-z]', '', w.lower())

def dolphin_words(tok):
    ws = []
    for t, ts in tok:
        if t.startswith('▁') or not ws:
            ws.append([t.replace('▁', ''), ts, ts])
        else:
            ws[-1][0] += t; ws[-1][2] = ts
    out = []
    for i, (w, a, b) in enumerate(ws):
        nxt = ws[i+1][1] if i+1 < len(ws) else b + 0.35
        out.append({'w': w, 't0': a, 't1': min(nxt, b + 0.35)})
    return [x for x in out if norm(x['w'])]

def align(text, tok, t0, t1):
    W = text.split()
    D = dolphin_words(tok)
    a = [norm(w) for w in W]; b = [norm(d['w']) for d in D]
    res = [None]*len(W)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for blk in sm.get_opcodes():
        tag, i1, i2, j1, j2 = blk
        if tag == 'equal':
            for k in range(i2-i1): res[i1+k] = (D[j1+k]['t0'], D[j1+k]['t1'])
        elif tag == 'replace' and j2 > j1:
            # bagi rentang waktu dolphin secara proporsional panjang huruf
            s, e = D[j1]['t0'], D[j2-1]['t1']; L = sum(max(1, len(a[i])) for i in range(i1, i2)); acc = 0
            for i in range(i1, i2):
                l = max(1, len(a[i])); res[i] = (s + (e-s)*acc/L, s + (e-s)*(acc+l)/L); acc += l
    # isi celah dengan interpolasi
    known = [i for i, r in enumerate(res) if r]
    if not known:
        L = sum(max(1, len(x)) for x in a); acc = 0
        for i in range(len(W)):
            l = max(1, len(a[i])); res[i] = (t0 + (t1-t0)*acc/L, t0 + (t1-t0)*(acc+l)/L); acc += l
    else:
        for i in range(len(W)):
            if res[i]: continue
            p = max([k for k in known if k < i], default=None); n = min([k for k in known if k > i], default=None)
            s = res[p][1] if p is not None else t0; e = res[n][0] if n is not None else t1
            gap = [k for k in range(i, len(W)) if not res[k] and (n is None or k < n)]
            m = len(gap); idx = gap.index(i) if i in gap else 0
            res[i] = (s + (e-s)*idx/m, s + (e-s)*(idx+1)/m)
    return [{'w': w, 't0': round(r[0], 3), 't1': round(max(r[1], r[0]+0.08), 3)} for w, r in zip(W, res)]

def koreksi():
    try: return json.load(open(KOREKSI_PATH))
    except Exception: return {}

def perbaiki(txt, K):
    for a, b in K.get('_kata', {}).items():
        txt = re.sub(r'\b' + re.escape(a) + r'\b', b, txt)
    return txt

def kata_klip(nama):
    K = koreksi()
    u = f'{ANA}/asr/{nama}.utuh.json'
    if os.path.exists(u):
        J = json.load(open(u))
        txt = K.get('_teks', {}).get(nama) or J['whisper']
        return align(perbaiki(txt, K), J['tok'], 0.0, J['dur'])
    J = json.load(open(f'{ANA}/asr/{nama}.json'))
    ov = K.get('_klip', {}).get(nama)
    out = []
    segs = J['segs']
    if ov:  # teks pengganti per segmen (indeks) atau buang segmen
        segs = []
        for i, s in enumerate(J['segs']):
            v = ov.get(str(i), s['whisper'])
            if v is None: continue
            s = dict(s); s['whisper'] = v; segs.append(s)
    for s in segs:
        out += align(perbaiki(s['whisper'], K), s['tok'], s['t0'], s['t1'])
    return out

if __name__ == '__main__':
    import sys
    for n in sys.argv[1:]:
        for w in kata_klip(n): print(f"{w['t0']:6.2f} {w['t1']:6.2f} {w['w']}")
