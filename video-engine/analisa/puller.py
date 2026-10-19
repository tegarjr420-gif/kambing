import json, subprocess, time, os, sys
D = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(f'{D}/chunks.json'))
exp = {c['nama'].split('/',1)[1]: c['end']-c['start']+1 for c in C}
os.makedirs(f'{D}/raw/parts', exist_ok=True)
got = {n for n in exp if os.path.exists(f'{D}/raw/parts/{n}') and os.path.getsize(f'{D}/raw/parts/{n}') == exp[n]}
t0 = time.time()
def assemble():
    base = {}
    for n in exp: base.setdefault(n.rsplit('.',1)[0], []).append(n)
    for b, parts in base.items():
        out = f'{D}/raw/{b}.mp4'
        if os.path.exists(out) or not all(p in got for p in parts): continue
        with open(out+'.tmp','wb') as f:
            for p in sorted(parts): f.write(open(f'{D}/raw/parts/{p}','rb').read())
        os.rename(out+'.tmp', out)
        for p in parts: os.remove(f'{D}/raw/parts/{p}')
        dur = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',out],capture_output=True,text=True).stdout.strip()
        print('SELESAI', b, dur, flush=True)
while len(got) < len(exp) and time.time()-t0 < 7200:
    try: lst = json.loads(subprocess.run([f'{D}/st.sh','ls'],capture_output=True,text=True).stdout or '[]')
    except Exception: lst = []
    for o in lst:
        n = o['name']; sz = (o.get('metadata') or {}).get('size')
        if n in exp and n not in got and sz == exp[n]:
            p = f'{D}/raw/parts/{n}'
            subprocess.run([f'{D}/st.sh','get',n,p])
            if os.path.exists(p) and os.path.getsize(p) == exp[n]:
                got.add(n); subprocess.run([f'{D}/st.sh','del',n],capture_output=True)
                print('ambil', n, len(got), '/', len(exp), flush=True)
        elif n in exp and sz is not None and sz != exp[n]:
            print('UKURAN SALAH', n, sz, exp[n], flush=True)
    assemble()
    time.sleep(8)
print('beres', len(got), '/', len(exp))
