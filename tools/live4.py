#!/usr/bin/env python3
"""The 3 Demo live channels (2026-10-27): the Demo films themselves, played again and again.
Nothing new is made: each film's picture and sound are copied into HLS pieces (no re-encoding). A static web site
cannot send a real live stream, so each channel is one long list (6 hours) of the same pieces, with a break mark
(#EXT-X-DISCONTINUITY) before every new round so picture and sound stay together.
Each channel has a main list with the picture and its sound track(s) as separate lists, so the Two Languages
channel offers English and Malayalam in the player's Audio list (iPhone, iPad and Android).

Also writes demo.m3u: the live channels first, then the 4 films.

live4.py <repo dir> [<web address> <playlist file>]   (the last two only to test from another address)
"""
import os, re, shutil, subprocess, sys

REPO = sys.argv[1]
PAGES = sys.argv[2] if len(sys.argv) > 2 else "https://binuabraham333-maker.github.io/stb4k-demo"
PLAYLIST = sys.argv[3] if len(sys.argv) > 3 else os.path.join(REPO, "demo.m3u")
HOURS = 6
LIVE_GROUP = "STB4K Demo Live"
FILM_GROUP = "STB4K Demo"

# (folder, channel name, film, poster used as the logo, sound tracks: (language, name))
LIVE = [
    ("showcase", "STB4K Live 1 · Showcase", "stb4k-showcase.mp4", "poster-showcase.jpg", [("eng", "English")]),
    ("languages", "STB4K Live 2 · Two Languages", "stb4k-two-audio-languages.mp4", "poster-languages.jpg",
     [("eng", "English"), ("mal", "Malayalam")]),
    ("surround", "STB4K Live 3 · 5.1 Surround", "stb4k-5.1-surround-test.mp4", "poster-5.1.jpg", [("eng", "5.1 test")]),
]
FILMS = [
    ("STB4K Showcase", "stb4k-showcase.mp4", "poster-showcase.jpg"),
    ("STB4K Two Audio Languages", "stb4k-two-audio-languages.mp4", "poster-languages.jpg"),
    ("STB4K English Subtitles", "stb4k-english-subtitles.mp4", "poster-subtitles.jpg"),
    ("STB4K 5.1 Surround Test", "stb4k-5.1-surround-test.mp4", "poster-5.1.jpg"),
]


def ffmpeg(args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args, check=True)


def build_channel(folder, film, tracks):
    out = os.path.join(REPO, "live", folder)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    stream_map = ["v:0,agroup:aud,name:video"] + [
        "a:%d,agroup:aud,language:%s,name:audio%d%s" % (i, lang, i, ",default:yes" if i == 0 else "")
        for i, (lang, _) in enumerate(tracks)]
    args = ["-i", os.path.join(REPO, "movie", film), "-map", "0:v:0"]
    for i in range(len(tracks)):
        args += ["-map", "0:a:%d" % i]
    ffmpeg(args + ["-c", "copy", "-f", "hls", "-hls_time", "6", "-hls_playlist_type", "vod",
                   "-hls_segment_type", "fmp4", "-hls_fmp4_init_filename", "init.mp4",
                   "-hls_segment_filename", os.path.join(out, "%v-%02d.m4s"),
                   "-master_pl_name", "index.m3u8", "-var_stream_map", " ".join(stream_map),
                   os.path.join(out, "%v.m3u8")])
    # The track names people see in the Audio list.
    master = open(os.path.join(out, "index.m3u8")).read()
    for i, (_, name) in enumerate(tracks):
        master = master.replace('NAME="audio_%d"' % (i + 1), 'NAME="%s"' % name)
    open(os.path.join(out, "index.m3u8"), "w").write(master)
    # One round of pieces → the same round again and again for HOURS hours.
    for name in os.listdir(out):
        if name.endswith(".m3u8") and name != "index.m3u8":
            loop(os.path.join(out, name))


def loop(path):
    text = open(path).read()
    head = text[:text.index("#EXTINF")]
    # The sound's last piece is one leftover sound frame (0.02 s) past the picture's end: left out.
    pieces = [p for p in re.findall(r"#EXTINF:[^\n]*\n[^\n]+\n", text)
              if float(re.match(r"#EXTINF:([\d.]+)", p).group(1)) >= 0.5]
    seconds = sum(float(re.match(r"#EXTINF:([\d.]+)", p).group(1)) for p in pieces)
    # Whole seconds, so the picture and every sound list have the same number of rounds.
    rounds = int(HOURS * 3600 // round(seconds))
    body = "#EXT-X-DISCONTINUITY\n".join("".join(pieces) for _ in range(rounds))
    open(path, "w").write(head + body + "#EXT-X-ENDLIST\n")


def build_playlist():
    m3u = ["#EXTM3U",
           "# STB4K Demo — every video, sound, poster and subtitle here is made by stb4k (no content from anyone else).",
           "# The live channels are the Demo films played again and again.",
           "# Details: %s/" % PAGES]
    for n, (folder, title, _, logo, _) in enumerate(LIVE, 1):
        m3u += ['#EXTINF:-1 tvg-chno="%d" tvg-logo="%s/images/%s" group-title="%s",%s' % (n, PAGES, logo, LIVE_GROUP, title),
                "%s/live/%s/index.m3u8" % (PAGES, folder)]
    for title, file, image in FILMS:
        m3u += ['#EXTINF:-1 tvg-logo="%s/images/%s" group-title="%s",%s' % (PAGES, image, FILM_GROUP, title),
                "%s/movie/%s" % (PAGES, file)]
    open(PLAYLIST, "w").write("\n".join(m3u) + "\n")


if __name__ == "__main__":
    if len(sys.argv) <= 2:
        for folder, _, film, _, tracks in LIVE:
            build_channel(folder, film, tracks)
    build_playlist()
    print("done")
