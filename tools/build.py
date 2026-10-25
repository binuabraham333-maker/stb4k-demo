#!/usr/bin/env python3
"""Builds the whole stb4k Demo (videos, posters, logos, demo.m3u) from scratch: every picture and sound is generated
here (FFmpeg test sources + text drawn with the open font Atkinson Hyperlegible, OFL). Nothing from anyone else.

build.py <work dir> <repo dir>
"""
import json, os, shutil, subprocess, sys

WORK, REPO = sys.argv[1], sys.argv[2]
TOOLS = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(WORK, "fonts")
RENDER = os.path.join(TOOLS, "render")
LOGO = os.path.join(REPO, "images", "stb4k-logo.png")
PAGES = "https://binuabraham333-maker.github.io/stb4k-demo"
W, H = 1920, 1080
FPS = 25


def render(specs):
    path = os.path.join(WORK, "specs.jsonl")
    with open(path, "w") as f:
        for s in specs:
            f.write(json.dumps(s) + "\n")
    subprocess.run([RENDER, FONTS, path], check=True)


def ffmpeg(args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args, check=True)


def clock(sec):
    return "%02d:%02d:%02d" % (sec // 3600, sec // 60 % 60, sec % 60)


def frame_base(title, line, sec, badge=None, corner=None):
    """Logo top left, clock (and badge) top right, title in a lower third: the same on every video."""
    items = [
        {"t": "rect", "x": 40, "y": 36, "w": 420, "h": 110, "color": "#0B0F1AD0", "r": 22},
        {"t": "img", "path": LOGO, "x": 70, "y": 66, "w": 360},
        {"t": "text", "s": corner or clock(sec), "x": W - 60, "y": 62, "size": 54, "bold": True, "align": "right",
         "box": "#0B0F1AD0", "pad": 22},
        {"t": "rect", "x": 0, "y": H - 230, "w": W, "h": 230, "color": "#0B0F1AC8"},
        {"t": "text", "s": title, "x": 80, "y": H - 200, "size": 76, "bold": True},
        {"t": "text", "s": line, "x": 82, "y": H - 100, "size": 40, "color": "#C9D2E3"},
    ]
    if badge:
        items.append({"t": "text", "s": badge, "x": W - 60, "y": 170, "size": 54, "bold": True, "align": "right",
                      "box": "#E0262DE6", "pad": 22})
    return items


def frames(name, seconds, make):
    """One transparent 1920×1080 picture per second (the clock and the changing texts)."""
    folder = os.path.join(WORK, "frames", name)
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
    render([{"out": os.path.join(folder, "%03d.png" % s), "w": W, "h": H, "bg": None, "items": make(s)}
            for s in range(seconds)])
    return os.path.join(folder, "%03d.png")


VIDEO = ["-c:v", "libx264", "-preset", "slow", "-crf", "30", "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p",
         "-g", "50", "-keyint_min", "50", "-sc_threshold", "0", "-r", str(FPS)]


def video_inputs(background, overlay, seconds):
    joiner = ":" if "=" in background else "="
    return ["-f", "lavfi", "-i", "%s%ss=%dx%d:r=%d:d=%d" % (background, joiner, W, H, FPS, seconds),
            "-framerate", "1", "-i", overlay]


def beep(freq, every, length=0.12, level=0.2):
    return "%g*sin(2*PI*%g*t)*lt(mod(t\\,%g)\\,%g)" % (level, freq, every, length)


def audio(expr, seconds, layout="stereo"):
    return ["-f", "lavfi", "-i", "aevalsrc=exprs=%s:s=48000:d=%d:c=%s" % (expr, seconds, layout)]


# ---------------------------------------------------------------------------------------------------- live channels

LIVE = [
    ("demo1", "stb4k Demo 1", "smptehdbars", "Colour bars · a short beep every second", beep(1000, 1)),
    ("demo2", "stb4k Demo 2", "testsrc2", "Moving test pattern · a beep every two seconds", beep(800, 2)),
    ("demo3", "stb4k Demo 3", "gradients=c0=0x1d3557:c1=0x2a9d8f:c2=0xe76f51:n=3:speed=0.03",
     "Moving colours · a low beep every three seconds", beep(500, 3)),
]
LOOP = 60          # seconds of picture, played again and again
REPEATS = 240      # 4 hours before the playlist ends (the app then connects again by itself)


def build_live():
    for key, title, background, line, sound in LIVE:
        overlay = frames(key, LOOP, lambda s: frame_base(title, "Live demo channel made by stb4k · " + line, s,
                                                          badge="LIVE DEMO", corner="Loop time " + clock(s)))
        out = os.path.join(REPO, "live", key)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        ffmpeg(video_inputs(background, overlay, LOOP) + audio(sound + "|" + sound, LOOP) + [
            "-filter_complex", "[0][1]overlay=0:0:eof_action=repeat,format=yuv420p[v]", "-map", "[v]", "-map", "2",
            *VIDEO, "-c:a", "aac", "-b:a", "96k", "-t", str(LOOP),
            "-f", "hls", "-hls_time", "6", "-hls_playlist_type", "vod", "-hls_segment_type", "fmp4",
            "-hls_fmp4_init_filename", "init.mp4", "-hls_segment_filename", os.path.join(out, "seg%02d.m4s"),
            os.path.join(out, "once.m3u8")])
        # The same minute again and again (a static web site cannot make a real live stream).
        lines = open(os.path.join(out, "once.m3u8")).read().splitlines()
        head = [l for l in lines if l.startswith("#EXT-X-TARGETDURATION") or l.startswith("#EXT-X-VERSION")]
        mapping = next(l for l in lines if l.startswith("#EXT-X-MAP"))
        segments = [(lines[i], lines[i + 1]) for i, l in enumerate(lines) if l.startswith("#EXTINF")]
        playlist = ["#EXTM3U"] + head + ["#EXT-X-MEDIA-SEQUENCE:0", "#EXT-X-PLAYLIST-TYPE:VOD", "#EXT-X-INDEPENDENT-SEGMENTS", mapping]
        for n in range(REPEATS):
            if n:
                playlist.append("#EXT-X-DISCONTINUITY")
            for inf, uri in segments:
                playlist += [inf, uri]
        playlist.append("#EXT-X-ENDLIST")
        open(os.path.join(out, "index.m3u8"), "w").write("\n".join(playlist) + "\n")
        os.remove(os.path.join(out, "once.m3u8"))


# ------------------------------------------------------------------------------------------------------------ films

SPEAKERS = [("Front Left", 0, "FL"), ("Front Right", 1, "FR"), ("Centre", 2, "C"), ("Subwoofer (LFE)", 3, "LFE"),
            ("Surround Left", 4, "SL"), ("Surround Right", 5, "SR")]
BOXES = {"FL": (560, 300), "C": (890, 260), "FR": (1220, 300), "SL": (500, 600), "LFE": (890, 640), "SR": (1280, 600)}


def surround_frame(s):
    step = (s - 8) // 12 if 8 <= s < 80 else None
    now = SPEAKERS[step][0] if step is not None else ("All speakers" if 80 <= s < 90 else "")
    items = frame_base("stb4k 5.1 Audio Test", "Each speaker in turn, then all together · made by stb4k", s)
    items.append({"t": "text", "s": "Now playing: " + now if now else ("5.1 sound check — listen to each speaker"
                                                                          if s < 8 else "End of the test"),
                  "x": W / 2, "y": 170, "size": 58, "bold": True, "align": "center", "box": "#0B0F1AD0", "pad": 22})
    for name, index, short in SPEAKERS:
        x, y = BOXES[short]
        active = (step == index) or (80 <= s < 90)
        items.append({"t": "rect", "x": x, "y": y, "w": 140 if short != "LFE" else 140, "h": 110,
                      "color": "#2F9BFFF0" if active else "#1A2133E0", "stroke": "#FFFFFF" if active else "#5A6478", "r": 18})
        items.append({"t": "text", "s": short, "x": x + 70, "y": y + 30, "size": 46, "bold": True, "align": "center"})
    items.append({"t": "text", "s": "You", "x": 960, "y": 470, "size": 40, "align": "center", "color": "#C9D2E3"})
    return items


def surround_sound():
    exprs = []
    for name, index, short in SPEAKERS:
        start = 8 + 12 * index
        if short == "LFE":
            tone = "0.5*sin(2*PI*50*t)"
        else:
            tone = "0.3*sin(2*PI*500*t)*lt(mod(t\\,1)\\,0.6)"
        exprs.append("%s*(between(t\\,%d\\,%d)+0.5*between(t\\,80\\,90))" % (tone, start, start + 11.5))
    return "|".join(exprs)


def languages_frame(s):
    items = frame_base("stb4k Two Audio Languages", "Two audio tracks · change them in ⋯ → Audio · made by stb4k", s)
    items += [
        {"t": "text", "s": "Audio 1 · English: one low beep every second", "x": W / 2, "y": 330, "size": 56,
         "bold": True, "align": "center", "box": "#0B0F1AD0", "pad": 22},
        {"t": "text", "s": "Audio 2 · Malayalam: two high beeps every second", "x": W / 2, "y": 470, "size": 56,
         "bold": True, "align": "center", "box": "#0B0F1AD0", "pad": 22},
        {"t": "text", "s": "Second %d" % s, "x": W / 2, "y": 620, "size": 48, "align": "center", "color": "#C9D2E3"},
    ]
    return items


SUBTITLES = ["Hello! This is the stb4k subtitle test.", "Subtitles are a separate track in this film.",
             "Turn them on in ⋯ → Subtitles → English.", "Change their size and colour in Settings.",
             "This is line five of ten.", "Every line stays on screen for five seconds.",
             "The picture shows which scene you are in.", "Subtitles and audio are made by stb4k.",
             "Almost done: this is line nine.", "The end. Thank you for watching!"]


def subtitles_frame(s):
    items = frame_base("stb4k English Subtitles", "An English subtitle track · ⋯ → Subtitles → English · made by stb4k", s)
    scene = min(s // 7 + 1, 10)
    items.append({"t": "text", "s": "Scene %d" % scene, "x": W / 2, "y": 300, "size": 120, "bold": True, "align": "center",
                  "box": "#0B0F1AB0", "pad": 30})
    return items


def srt(path):
    def t(x):
        return "00:%02d:%02d,000" % (x // 60, x % 60)
    with open(path, "w") as f:
        for i, text in enumerate(SUBTITLES):
            start = 5 + i * 7
            f.write("%d\n%s --> %s\n%s\n\n" % (i + 1, t(start), t(start + 5), text))


EPISODES = [("Red", "0xb5172f", "0x3a0610"), ("Green", "0x1f8a4c", "0x072615"), ("Blue", "0x1d5fd6", "0x06163a")]


def build_films():
    out = os.path.join(REPO, "movie")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    films = os.path.join(REPO, "series")
    shutil.rmtree(films, ignore_errors=True)
    os.makedirs(films)
    dark = "gradients=c0=0x14213d:c1=0x0b0f1a:c2=0x1d3557:n=3:speed=0.01"

    seconds = 98
    overlay = frames("surround", seconds, surround_frame)
    ffmpeg(video_inputs(dark, overlay, seconds) + audio(surround_sound(), seconds, "5.1(side)") + [
        "-filter_complex", "[0][1]overlay=0:0:eof_action=repeat,format=yuv420p[v]", "-map", "[v]", "-map", "2",
        *VIDEO, "-c:a", "aac", "-b:a", "256k", "-metadata:s:a:0", "language=eng", "-metadata:s:a:0", "title=5.1 test",
        "-metadata", "title=stb4k 5.1 Audio Test", "-movflags", "+faststart", "-t", str(seconds),
        os.path.join(out, "stb4k-5.1-audio-test.mp4")])

    seconds = 70
    overlay = frames("languages", seconds, languages_frame)
    english = beep(440, 1, 0.15)
    malayalam = "0.2*sin(2*PI*660*t)*(lt(mod(t\\,1)\\,0.1)+between(mod(t\\,1)\\,0.22\\,0.32))"
    ffmpeg(video_inputs(dark, overlay, seconds) + audio(english + "|" + english, seconds)
           + audio(malayalam + "|" + malayalam, seconds) + [
        "-filter_complex", "[0][1]overlay=0:0:eof_action=repeat,format=yuv420p[v]", "-map", "[v]", "-map", "2", "-map", "3",
        *VIDEO, "-c:a", "aac", "-b:a", "96k",
        "-metadata:s:a:0", "language=eng", "-metadata:s:a:0", "title=English",
        "-metadata:s:a:1", "language=mal", "-metadata:s:a:1", "title=Malayalam",
        "-disposition:a:0", "default", "-disposition:a:1", "0",
        "-metadata", "title=stb4k Two Audio Languages", "-movflags", "+faststart", "-t", str(seconds),
        os.path.join(out, "stb4k-two-audio-languages.mp4")])

    seconds = 76
    overlay = frames("subtitles", seconds, subtitles_frame)
    subs = os.path.join(WORK, "english.srt")
    srt(subs)
    soft = beep(600, 2, 0.1, 0.12)
    ffmpeg(video_inputs(dark, overlay, seconds) + audio(soft + "|" + soft, seconds) + ["-i", subs,
        "-filter_complex", "[0][1]overlay=0:0:eof_action=repeat,format=yuv420p[v]", "-map", "[v]", "-map", "2", "-map", "3",
        *VIDEO, "-c:a", "aac", "-b:a", "96k", "-c:s", "mov_text",
        "-metadata:s:a:0", "language=eng", "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=English",
        "-metadata", "title=stb4k English Subtitles", "-movflags", "+faststart", "-t", str(seconds),
        os.path.join(out, "stb4k-english-subtitles.mp4")])

    seconds = 40
    for n, (colour, c0, c1) in enumerate(EPISODES, 1):
        overlay = frames("episode%d" % n, seconds, lambda s, n=n, colour=colour: frame_base(
            "stb4k Demo Series · Episode %d" % n, "Episode %d of 3: %s · made by stb4k" % (n, colour), s))
        sound = beep(400 + 100 * n, 1, 0.08, 0.12)
        ffmpeg(video_inputs("gradients=c0=%s:c1=%s:n=2:speed=0.02" % (c0, c1), overlay, seconds)
               + audio(sound + "|" + sound, seconds) + [
            "-filter_complex", "[0][1]overlay=0:0:eof_action=repeat,format=yuv420p[v]", "-map", "[v]", "-map", "2",
            *VIDEO, "-c:a", "aac", "-b:a", "96k", "-metadata:s:a:0", "language=eng",
            "-metadata", "title=stb4k Demo Series S01E%02d" % n, "-movflags", "+faststart", "-t", str(seconds),
            os.path.join(films, "stb4k-demo-series-s01e%02d.mp4" % n)])


# --------------------------------------------------------------------------------------------- posters and logos

def poster(out, title_lines, line, top, bottom):
    items = [{"t": "img", "path": LOGO, "x": 120, "y": 90, "w": 360}]
    y = 380
    for t in title_lines:
        items.append({"t": "text", "s": t, "x": 300, "y": y, "size": 78, "bold": True, "align": "center"})
        y += 96
    items += [{"t": "text", "s": line, "x": 300, "y": 760, "size": 34, "align": "center", "color": "#E6ECF5"},
              {"t": "text", "s": "Made by stb4k", "x": 300, "y": 830, "size": 28, "align": "center", "color": "#AEB8CA"}]
    return {"out": out, "w": 600, "h": 900, "bg": [top, bottom], "items": items}


def channel_logo(out, number, top, bottom):
    return {"out": out, "w": 512, "h": 512, "bg": [top, bottom], "items": [
        {"t": "img", "path": LOGO, "x": 76, "y": 110, "w": 360},
        {"t": "text", "s": "Demo %d" % number, "x": 256, "y": 250, "size": 104, "bold": True, "align": "center"},
        {"t": "text", "s": "LIVE", "x": 256, "y": 392, "size": 44, "bold": True, "align": "center", "box": "#E0262D", "pad": 14}]}


def build_images():
    images = os.path.join(REPO, "images")
    render([
        channel_logo(os.path.join(images, "demo1.png"), 1, "#3A0CA3", "#7209B7"),
        channel_logo(os.path.join(images, "demo2.png"), 2, "#0F5257", "#12A4A4"),
        channel_logo(os.path.join(images, "demo3.png"), 3, "#9C3D1E", "#E76F51"),
        poster(os.path.join(images, "poster-5.1.jpg"), ["5.1 Audio", "Test"], "Each speaker by name", "#1D3557", "#0B0F1A"),
        poster(os.path.join(images, "poster-languages.jpg"), ["Two Audio", "Languages"], "English · Malayalam", "#264653", "#0B0F1A"),
        poster(os.path.join(images, "poster-subtitles.jpg"), ["English", "Subtitles"], "A subtitle track to try", "#6A4C93", "#0B0F1A"),
        poster(os.path.join(images, "poster-series.jpg"), ["Demo", "Series"], "3 episodes: Red, Green, Blue", "#B5172F", "#1D5FD6"),
    ])


def build_playlist():
    m3u = ["#EXTM3U",
           "# stb4k Demo — every video, sound, picture and logo here is made by stb4k (no content from anyone else).",
           "# Details: %s/" % PAGES]
    for n, (key, title, *_rest) in enumerate(LIVE, 1):
        m3u += ['#EXTINF:-1 tvg-chno="%d" tvg-logo="%s/images/demo%d.png" group-title="Demo Live",%s' % (n, PAGES, n, title),
                "%s/live/%s/index.m3u8" % (PAGES, key)]
    for title, file, image in [("stb4k 5.1 Audio Test", "stb4k-5.1-audio-test.mp4", "poster-5.1.jpg"),
                               ("stb4k Two Audio Languages", "stb4k-two-audio-languages.mp4", "poster-languages.jpg"),
                               ("stb4k English Subtitles", "stb4k-english-subtitles.mp4", "poster-subtitles.jpg")]:
        m3u += ['#EXTINF:-1 tvg-logo="%s/images/%s" group-title="Demo Movies",%s' % (PAGES, image, title),
                "%s/movie/%s" % (PAGES, file)]
    for n, (colour, *_rest) in enumerate(EPISODES, 1):
        m3u += ['#EXTINF:-1 tvg-logo="%s/images/poster-series.jpg" group-title="Demo Series",stb4k Demo Series S01E%02d %s'
                % (PAGES, n, colour), "%s/series/stb4k-demo-series-s01e%02d.mp4" % (PAGES, n)]
    open(os.path.join(REPO, "demo.m3u"), "w").write("\n".join(m3u) + "\n")


if __name__ == "__main__":
    os.makedirs(os.path.join(REPO, "images"), exist_ok=True)
    build_images()
    build_live()
    build_films()
    build_playlist()
    print("done")
