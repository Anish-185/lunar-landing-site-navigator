#!/usr/bin/env bash
# Build the 28 s demo video from frames captured by scripts_demo_capture.mjs (+ title/end cards), with ffmpeg.
# Usage: scripts_demo_video.sh <frames_dir>   (needs frames_dir/{cards,sun,pole,athena,verdicts,replan})
# Output: public/demo/gnomon_demo.mp4 (1080p, H.264, subtitles burned in from public/demo/gnomon_demo.vtt)
set -euo pipefail
F="$1"; HERE="$(cd "$(dirname "$0")" && pwd)"; OUT="$HERE/public/demo"; T="$F/segs"; mkdir -p "$T"
V="-c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 -an"
fit="scale=1920:1080:flags=lanczos,setsar=1"
# a sequence of N stills played over D seconds, blended to 30 fps
seq() { local dir=$1 d=$2 out=$3; local n; n=$(ls "$F/$dir"/*.png | wc -l)
  ffmpeg -hide_banner -loglevel error -y -framerate "$n/$d" -i "$F/$dir/%04d.png" \
    -vf "$fit,framerate=fps=30:interp_start=0:interp_end=255:scene=100" -t "$d" $V "$T/$out.mp4"; }
# one still with a slow push-in
still() { local img=$1 d=$2 out=$3 z=${4:-0.04}
  ffmpeg -hide_banner -loglevel error -y -loop 1 -framerate 30 -i "$img" \
    -vf "scale=3840:2160:flags=lanczos,zoompan=z='1+$z*on/($d*30)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30,setsar=1" \
    -t "$d" $V "$T/$out.mp4"; }
still "$F/cards/title.png" 3 s1 0.03
seq sun 6 s2
seq pole 5 s3
seq athena 5 s4
still "$F/verdicts/0000.png" 2.6 s5a 0.05
# replan: the slip moves, cards and grid re-rank (crossfaded stills)
ffmpeg -hide_banner -loglevel error -y -framerate 4/3.4 -i "$F/replan/%04d.png" -vf "$fit,framerate=fps=30:interp_start=80:interp_end=175:scene=100" -t 3.4 $V "$T/s5b.mp4"
still "$F/cards/end.png" 3 s6 0.02
printf "file '%s'\n" "$T"/s1.mp4 "$T"/s2.mp4 "$T"/s3.mp4 "$T"/s4.mp4 "$T"/s5a.mp4 "$T"/s5b.mp4 "$T"/s6.mp4 > "$T/list.txt"
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$T/list.txt" -c copy "$T/joined.mp4"
# burn the subtitles (same cues as the .vtt); fade in/out
ffmpeg -hide_banner -loglevel error -y -i "$OUT/gnomon_demo.vtt" "$T/subs.ass"
sed -i -e 's/^PlayResX:.*/PlayResX: 1920/' -e 's/^PlayResY:.*/PlayResY: 1080/' \
  -e 's/^Style: Default,.*/Style: Default,Adwaita Sans,44,\&H00F2EAED,\&H000000FF,\&H50060506,\&H50060506,0,0,0,0,100,100,0,0,3,14,0,2,60,60,52,1/' "$T/subs.ass"
ffmpeg -hide_banner -loglevel error -y -i "$T/joined.mp4" -vf "ass=$T/subs.ass,fade=t=in:st=0:d=0.4,fade=t=out:st=27.5:d=0.5" -t 28 \
  -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p -r 30 -movflags +faststart -an "$OUT/gnomon_demo.mp4"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height -of default=nw=1 "$OUT/gnomon_demo.mp4"
