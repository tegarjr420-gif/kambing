import sherpa_onnx, numpy as np, sys, os, json
from scipy.io import wavfile
K='/tmp/claude-0/-home-claude/8530fe1f-175c-5546-b869-127bbb89636c/scratchpad/video-kit/asr/'
wh=sherpa_onnx.OfflineRecognizer.from_whisper(encoder=K+'sherpa-onnx-whisper-turbo/turbo-encoder.int8.onnx',decoder=K+'sherpa-onnx-whisper-turbo/turbo-decoder.int8.onnx',tokens=K+'sherpa-onnx-whisper-turbo/turbo-tokens.txt',language='id',task='transcribe',num_threads=2)
dm=K+'sherpa-onnx-dolphin-base-ctc-multi-lang-int8-2025-04-02/'
dol=sherpa_onnx.OfflineRecognizer.from_dolphin_ctc(model=dm+'model.int8.onnx',tokens=dm+'tokens.txt',num_threads=2)
for f in sys.argv[1:]:
    n=os.path.basename(f)[:-4]
    sr,y=wavfile.read(f); y=y.astype(np.float32)/32768; y*=min(0.5/(abs(y).max()+1e-9),30)
    s=wh.create_stream(); s.accept_waveform(16000,y); wh.decode_stream(s); txt=s.result.text.strip()
    d=dol.create_stream(); d.accept_waveform(16000,y); dol.decode_stream(d)
    toks=[[t,round(float(ts),2)] for t,ts in zip(d.result.tokens,d.result.timestamps)]
    json.dump({'dur':len(y)/16000,'whisper':txt,'tok':toks},open(f'asr/{n}.utuh.json','w'),ensure_ascii=False)
    print(n,'|',txt,'\n   D:',''.join(t for t,_ in toks).replace('▁',' '),flush=True)
