#!/bin/bash
# Sekali per sesi: font, soundfont, model suara, pustaka Python.
set -e; cd "$(dirname "$0")"
pip install --break-system-packages -q tinysoundfont --no-deps "opencv-python-headless<5" sherpa-onnx scipy numpy pillow
mkdir -p fonts && (cd /tmp && npm i --silent @expo-google-fonts/plus-jakarta-sans @expo-google-fonts/bricolage-grotesque @expo-google-fonts/montserrat @expo-google-fonts/anton @expo-google-fonts/poppins @expo-google-fonts/playfair-display @expo-google-fonts/caveat && find node_modules/@expo-google-fonts -name "*.ttf" | grep -v Italic | xargs -I{} cp {} "$OLDPWD/fonts/")
[ -f /home/claude/mrbumpy409/generaluser-gs/GeneralUser-GS.sf2 ] || GIT_LFS_SKIP_SMUDGE=1 git clone -q --depth 1 https://github.com/mrbumpy409/generaluser-gs /home/claude/mrbumpy409/generaluser-gs
echo "Model ASR: unduh sherpa-onnx-whisper-turbo dan sherpa-onnx-dolphin-base-ctc-multi-lang-int8-2025-04-02 dari github.com/k2-fsa/sherpa-onnx/releases (asr-models)"
