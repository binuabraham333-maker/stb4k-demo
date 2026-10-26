#!/usr/bin/env python3
"""Builds the 4-video stb4k Demo (2026-10-26): Showcase, Two Audio Languages, English Subtitles, 5.1 Surround Test.
Every picture and sound is generated here (FFmpeg test sources + text drawn with the open font Atkinson Hyperlegible,
OFL). No logo and no tagline in any video. Each video opens with a title card; its poster is a frame of that card.

build4.py <work dir> <repo dir>
"""
import json, os, shutil, subprocess, sys

WORK, REPO = sys.argv[1], sys.argv[2]
TOOLS = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(WORK, "fonts")
RENDER = os.path.join(TOOLS, "render")
PAGES = "https://binuabraham333-maker.github.io/stb4k-demo"
GROUP = "STB4K Demo"
W, H = 1920, 1080
FPS = 25
# The middle 2:3 part of the picture (the poster): title cards keep their text inside it.
POSTER_BOX = (600, 0, 720, 1080)


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


def title_card(lines, line):
    """Big title in the middle (inside the poster part), one smaller line under it."""
    items, y = [], 330 if len(lines) > 1 else 400
    for t in lines:
        items.append({"t": "text", "s": t, "x": W / 2, "y": y, "size": 104, "bold": True, "align": "center"})
        y += 128
    items.append({"t": "text", "s": line, "x": W / 2, "y": y + 40, "size": 40, "align": "center", "color": "#E6ECF5"})
    return items


def test_frame(title, line, sec, lower=True):
    """Test videos after the title card: the time top right and the title in a lower third (no logo).
    lower=False: no lower third (the subtitles film: its subtitle lines sit there)."""
    items = [{"t": "text", "s": clock(sec), "x": W - 60, "y": 62, "size": 54, "bold": True, "align": "right",
              "box": "#0B0F1AD0", "pad": 22}]
    if lower:
        items += [{"t": "rect", "x": 0, "y": H - 230, "w": W, "h": 230, "color": "#0B0F1AC8"},
                  {"t": "text", "s": title, "x": 80, "y": H - 200, "size": 76, "bold": True},
                  {"t": "text", "s": line, "x": 82, "y": H - 100, "size": 40, "color": "#C9D2E3"}]
    return items


def frames(name, seconds, make):
    """One transparent 1920×1080 picture per second (the texts that change)."""
    folder = os.path.join(WORK, "frames4", name)
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
    render([{"out": os.path.join(folder, "%03d.png" % s), "w": W, "h": H, "bg": None, "items": make(s)}
            for s in range(seconds)])
    return os.path.join(folder, "%03d.png")


VIDEO = ["-c:v", "libx264", "-preset", "slow", "-crf", "28", "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p",
         "-g", "50", "-keyint_min", "50", "-sc_threshold", "0", "-r", str(FPS)]


def video_inputs(background, overlay, seconds):
    return ["-f", "lavfi", "-i", "%s:s=%dx%d:r=%d:d=%d" % (background, W, H, FPS, seconds),
            "-framerate", "1", "-i", overlay]


def beep(freq, every, length=0.12, level=0.2):
    return "%g*sin(2*PI*%g*t)*lt(mod(t\\,%g)\\,%g)" % (level, freq, every, length)


def audio(expr, seconds, layout="stereo"):
    return ["-f", "lavfi", "-i", "aevalsrc=exprs=%s:s=48000:d=%d:c=%s" % (expr, seconds, layout)]


OVERLAY = ["-filter_complex", "[0][1]overlay=0:0:eof_action=repeat,format=yuv420p[v]", "-map", "[v]"]

# ------------------------------------------------------------------------------------------------------ Showcase

SHOWCASE = [("Showcase", "A short tour of the player"), ("Live TV", "Channels, TV guide and catch-up"),
            ("Films and series", "Posters, seasons and continue watching"), ("Two players", "Player 1 and Player 2"),
            ("Sound and subtitles", "5.1, audio languages and subtitles"), ("Ready to play", "")]
# One soft chord per scene (Hz): C, F, G, A minor, F, C.
CHORDS = [(261.6, 329.6, 392.0), (349.2, 440.0, 523.3), (392.0, 493.9, 587.3), (220.0, 261.6, 329.6),
          (349.2, 440.0, 523.3), (261.6, 329.6, 392.0)]


def showcase_frame(s):
    title, line = SHOWCASE[min(s // 5, 5)]
    if s < 5:
        return title_card([title], line)
    items = [{"t": "text", "s": title, "x": W / 2, "y": 420, "size": 120, "bold": True, "align": "center"}]
    if line:
        items.append({"t": "text", "s": line, "x": W / 2, "y": 580, "size": 48, "align": "center", "color": "#E6ECF5"})
    return items


def showcase_sound():
    parts = []
    for n, chord in enumerate(CHORDS):
        start, end = 5 * n, 5 * n + 5
        # A gentle swell inside each 5-second scene (no clicks at the cuts).
        env = "between(t\\,%d\\,%d)*sin(PI*(t-%d)/5)" % (start, end, start)
        tones = "+".join("sin(2*PI*%g*t)" % f for f in chord)
        parts.append("0.09*(%s)*%s" % (tones, env))
    return "+".join(parts)


# ------------------------------------------------------------------------------------------------------- tests

def languages_frame(s):
    if s < 2:
        return title_card(["Two Audio", "Languages"], "English · Malayalam")
    return test_frame("Two Audio Languages", "Two audio tracks · change them in ⋯ → Audio", s) + [
        {"t": "text", "s": "Audio 1 · English: one low beep every second", "x": W / 2, "y": 330, "size": 56,
         "bold": True, "align": "center", "box": "#0B0F1AD0", "pad": 22},
        {"t": "text", "s": "Audio 2 · Malayalam: two high beeps every second", "x": W / 2, "y": 470, "size": 56,
         "bold": True, "align": "center", "box": "#0B0F1AD0", "pad": 22},
        {"t": "text", "s": "Second %d" % s, "x": W / 2, "y": 620, "size": 48, "align": "center", "color": "#C9D2E3"}]


SUBTITLES = [(0.5, "Welcome to the subtitle test."), (5.5, "This is scene two. Subtitles are working."),
             (10.5, "You can switch subtitles on and off in the player menu."),
             (15.5, "Scene four: the text changes every five seconds."),
             (20.5, "Scene five: check the timing matches the scene number."), (25.5, "End of test. Thank you for watching.")]


def subtitles_frame(s):
    if s < 2:
        return title_card(["English", "Subtitles"], "A subtitle track to try")
    return test_frame("English Subtitles", "", s, lower=False) + [
        {"t": "text", "s": "Turn subtitles on: ⋯ → Subtitles → English", "x": W / 2, "y": 470, "size": 44,
         "align": "center", "color": "#C9D2E3"},
        {"t": "text", "s": "Scene %d" % (s // 5 + 1), "x": W / 2, "y": 300, "size": 120, "bold": True, "align": "center",
         "box": "#0B0F1AB0", "pad": 30}]


def srt(path):
    def t(x):
        return "00:00:%02d,%03d" % (int(x), round((x % 1) * 1000))
    with open(path, "w") as f:
        for i, (start, text) in enumerate(SUBTITLES):
            f.write("%d\n%s --> %s\n%s\n\n" % (i + 1, t(start), t(start + 4), text))


SPEAKERS = [("Front Left", "FL"), ("Front Right", "FR"), ("Centre", "C"), ("Subwoofer (LFE)", "LFE"),
            ("Surround Left", "SL"), ("Surround Right", "SR")]
BOXES = {"FL": (560, 300), "C": (890, 260), "FR": (1220, 300), "SL": (500, 600), "LFE": (890, 640), "SR": (1280, 600)}
SURROUND_START, STEP = 3, 5          # 3 s title card, then 5 s per speaker, then all together until 36 s


def surround_frame(s):
    if s < SURROUND_START:
        return title_card(["5.1 Surround", "Test"], "Each speaker by name")
    step = (s - SURROUND_START) // STEP
    together = step >= len(SPEAKERS)
    items = test_frame("5.1 Surround Test", "Each speaker in turn, then all together", s)
    items.append({"t": "text", "s": "Now playing: " + ("All speakers" if together else SPEAKERS[step][0]),
                  "x": W / 2, "y": 170, "size": 58, "bold": True, "align": "center", "box": "#0B0F1AD0", "pad": 22})
    for index, (name, short) in enumerate(SPEAKERS):
        x, y = BOXES[short]
        active = together or step == index
        items.append({"t": "rect", "x": x, "y": y, "w": 140, "h": 110, "color": "#2F9BFFF0" if active else "#1A2133E0",
                      "stroke": "#FFFFFF" if active else "#5A6478", "r": 18})
        items.append({"t": "text", "s": short, "x": x + 70, "y": y + 30, "size": 46, "bold": True, "align": "center"})
    items.append({"t": "text", "s": "You", "x": 960, "y": 470, "size": 40, "align": "center", "color": "#C9D2E3"})
    return items


def surround_sound(seconds):
    exprs = []
    for index, (name, short) in enumerate(SPEAKERS):
        start = SURROUND_START + STEP * index
        tone = "0.5*sin(2*PI*50*t)" if short == "LFE" else "0.3*sin(2*PI*500*t)*lt(mod(t\\,1)\\,0.6)"
        together = SURROUND_START + STEP * len(SPEAKERS)
        exprs.append("%s*(between(t\\,%d\\,%g)+0.5*between(t\\,%d\\,%d))" % (tone, start, start + STEP - 0.5, together, seconds))
    return "|".join(exprs)


# --------------------------------------------------------------------------------------------------------- build

FILMS = [  # (title in the playlist, file, poster)
    ("STB4K Showcase", "stb4k-showcase.mp4", "poster-showcase.jpg"),
    ("STB4K Two Audio Languages", "stb4k-two-audio-languages.mp4", "poster-languages.jpg"),
    ("STB4K English Subtitles", "stb4k-english-subtitles.mp4", "poster-subtitles.jpg"),
    ("STB4K 5.1 Surround Test", "stb4k-5.1-surround-test.mp4", "poster-5.1.jpg"),
]


def build_films():
    out = os.path.join(REPO, "movie")
    dark = "gradients=c0=0x14213d:c1=0x0b0f1a:c2=0x1d3557:n=3:speed=0.01"

    seconds = 30
    overlay = frames("showcase", seconds, showcase_frame)
    ffmpeg(video_inputs("gradients=c0=0x3a0ca3:c1=0x0f5257:c2=0xe76f51:c3=0x1d3557:n=4:speed=0.02", overlay, seconds)
           + audio(showcase_sound() + "|" + showcase_sound(), seconds) + OVERLAY + ["-map", "2",
        *VIDEO, "-c:a", "aac", "-b:a", "128k", "-metadata:s:a:0", "language=eng",
        "-metadata", "title=STB4K Showcase", "-movflags", "+faststart", "-t", str(seconds),
        os.path.join(out, FILMS[0][1])])

    seconds = 30
    overlay = frames("languages", seconds, languages_frame)
    english = beep(440, 1, 0.15)
    malayalam = "0.2*sin(2*PI*660*t)*(lt(mod(t\\,1)\\,0.1)+between(mod(t\\,1)\\,0.22\\,0.32))"
    ffmpeg(video_inputs("gradients=c0=0x264653:c1=0x0b0f1a:c2=0x1d3557:n=3:speed=0.01", overlay, seconds)
           + audio(english + "|" + english, seconds) + audio(malayalam + "|" + malayalam, seconds) + OVERLAY
           + ["-map", "2", "-map", "3", *VIDEO, "-c:a", "aac", "-b:a", "96k",
        "-metadata:s:a:0", "language=eng", "-metadata:s:a:0", "title=English",
        "-metadata:s:a:1", "language=mal", "-metadata:s:a:1", "title=Malayalam",
        "-disposition:a:0", "default", "-disposition:a:1", "0",
        "-metadata", "title=STB4K Two Audio Languages", "-movflags", "+faststart", "-t", str(seconds),
        os.path.join(out, FILMS[1][1])])

    seconds = 30
    overlay = frames("subtitles", seconds, subtitles_frame)
    subs = os.path.join(WORK, "english4.srt")
    srt(subs)
    soft = beep(600, 2, 0.1, 0.12)
    ffmpeg(video_inputs("gradients=c0=0x6a4c93:c1=0x0b0f1a:c2=0x1d3557:n=3:speed=0.01", overlay, seconds)
           + audio(soft + "|" + soft, seconds) + ["-i", subs] + OVERLAY + ["-map", "2", "-map", "3",
        *VIDEO, "-c:a", "aac", "-b:a", "96k", "-c:s", "mov_text",
        "-metadata:s:a:0", "language=eng", "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=English",
        "-metadata", "title=STB4K English Subtitles", "-movflags", "+faststart", "-t", str(seconds),
        os.path.join(out, FILMS[2][1])])

    seconds = 36
    overlay = frames("surround", seconds, surround_frame)
    ffmpeg(video_inputs(dark, overlay, seconds) + audio(surround_sound(seconds), seconds, "5.1(side)") + OVERLAY + [
        "-map", "2", *VIDEO, "-c:a", "aac", "-b:a", "256k", "-metadata:s:a:0", "language=eng",
        "-metadata:s:a:0", "title=5.1 test", "-metadata", "title=STB4K 5.1 Surround Test", "-movflags", "+faststart",
        "-t", str(seconds), os.path.join(out, FILMS[3][1])])


def build_posters():
    """A frame of each title card (1 s in), the middle 2:3 part, 600 × 900."""
    x, y, w, h = POSTER_BOX
    for title, file, image in FILMS:
        ffmpeg(["-ss", "1", "-i", os.path.join(REPO, "movie", file), "-frames:v", "1",
                "-vf", "crop=%d:%d:%d:%d,scale=600:900" % (w, h, x, y), "-q:v", "3",
                os.path.join(REPO, "images", image)])


def build_playlist():
    m3u = ["#EXTM3U",
           "# STB4K Demo — every video, sound, poster and subtitle here is made by stb4k (no content from anyone else).",
           "# Details: %s/" % PAGES]
    for title, file, image in FILMS:
        m3u += ['#EXTINF:-1 tvg-logo="%s/images/%s" group-title="%s",%s' % (PAGES, image, GROUP, title),
                "%s/movie/%s" % (PAGES, file)]
    open(os.path.join(REPO, "demo.m3u"), "w").write("\n".join(m3u) + "\n")


if __name__ == "__main__":
    for folder in ["movie", "series", "live"]:
        shutil.rmtree(os.path.join(REPO, folder), ignore_errors=True)
    os.makedirs(os.path.join(REPO, "movie"))
    images = os.path.join(REPO, "images")
    for name in os.listdir(images):
        if name.startswith("poster-") or name.startswith("demo"):
            os.remove(os.path.join(images, name))
    build_films()
    build_posters()
    build_playlist()
    print("done")
