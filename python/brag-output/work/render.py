"""Render the LinkTrial brag video by driving the real vitrine page frame by frame.
usage: python render.py stills <out_dir> t1 t2 ...  |  python render.py video <out.mp4>"""
import pathlib, subprocess, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE = (HERE.parents[1] / "data/linktrial_vitrine.html").as_uri()
FPS = 30

def open_page(p):
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 810}, device_scale_factor=4 / 3)
    pg.goto(PAGE + "#patients")
    pg.add_script_tag(path=str(HERE / "director.js"))
    pg.evaluate("Promise.all([document.fonts.load('800 40px Manrope'),document.fonts.load('400 16px \"DM Sans\"'),document.fonts.load('650 16px \"DM Sans\"')]).then(()=>document.fonts.ready)")
    pg.wait_for_timeout(300)
    return b, pg

def main():
    mode, target = sys.argv[1], pathlib.Path(sys.argv[2])
    with sync_playwright() as p:
        b, pg = open_page(p)
        if mode == "stills":
            target.mkdir(parents=True, exist_ok=True)
            for t in sorted(map(float, sys.argv[3:])):
                pg.evaluate(f"renderAt({t})")
                pg.screenshot(path=str(target / f"t{t:05.2f}.png"))
        else:
            n = round(pg.evaluate("DURATION") * FPS)
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                                   "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", str(target)],
                                  stdin=subprocess.PIPE)
            for i in range(n):
                pg.evaluate(f"renderAt({i / FPS})")
                ff.stdin.write(pg.screenshot(type="png"))
            ff.stdin.close(); ff.wait()
        b.close()

if __name__ == "__main__":
    main()
