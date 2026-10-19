# Mesin video Barokah Farm (Otomaya) — server otomatis di Railway
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 TZ=Asia/Jakarta \
    MODELS=/models SF2=/models/GeneralUser-GS.sf2 DATA=/data PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg python3 python3-pip curl ca-certificates bzip2 tzdata nodejs npm \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt \
 && pip3 install --break-system-packages --no-cache-dir --no-deps tinysoundfont==0.3.7 \
 && python3 -c "import tinysoundfont, sherpa_onnx, cv2; print(cv2.__version__)"
# model suara-ke-teks (Whisper turbo int8 + Dolphin CTC) dan soundfont musik
RUN mkdir -p /models && cd /models \
 && curl -fsSL https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-turbo.tar.bz2 \
    | tar xj --wildcards '*turbo-encoder.int8.onnx' '*turbo-decoder.int8.onnx' '*turbo-tokens.txt' \
 && curl -fsSL https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-dolphin-base-ctc-multi-lang-int8-2025-04-02.tar.bz2 \
    | tar xj --wildcards '*model.int8.onnx' '*tokens.txt' \
 && curl -fsSL -o GeneralUser-GS.sf2 https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main/GeneralUser-GS.sf2 \
 && ls -laR /models | head -30
# kartu penutup dibuat dengan Chromium (Playwright)
RUN npm init -y >/dev/null && npm i playwright@1.64.1 && npx playwright install --with-deps --only-shell chromium && rm -rf /root/.npm
COPY . .
RUN python3 lut.py 2>/dev/null || true; ls aset/lut
EXPOSE 8080
CMD ["python3", "server.py"]
