#!/bin/bash
# Assemble the AssetForge demo video from captured segment frames.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

FF="$(.venv/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')"
OUT=video/build
mkdir -p "$OUT"

seg () {  # seg <dir> <in-framerate> <name>
  local dir="$1" rate="$2" name="$3"
  $FF -y -loglevel error -framerate "$rate" -i "video/frames/$dir/%03d.jpg" \
    -vf "fps=12,format=yuv420p" -c:v libx264 -preset medium -crf 20 \
    "$OUT/$name.mp4"
  echo "$OUT/$name.mp4"
}

seg segA       12   a_hook
seg segB        0.8 b_build
seg segC        0.9 c_fail
seg segD        1.6 d_collect
seg segE-swap   0.8 e_swap
seg segE-sweep   7   e_sweep
seg segF        1.0 f_verify
if ls video/frames/segG/*.jpg >/dev/null 2>&1; then seg segG 0.8 g_bench; fi
seg segH        0.7 h_close

rm -f "$OUT/list.txt"
for f in a_hook b_build c_fail d_collect e_swap e_sweep f_verify g_bench h_close; do
  [ -f "$OUT/$f.mp4" ] && echo "file '$PWD/$OUT/$f.mp4'" >> "$OUT/list.txt"
done

$FF -y -loglevel error -f concat -safe 0 -i "$OUT/list.txt" -c copy "$OUT/AssetForge-demo.mp4"
echo "FINAL -> $OUT/AssetForge-demo.mp4"
$FF -i "$OUT/AssetForge-demo.mp4" 2>&1 | grep -E "Duration|Stream.*Video" || true
