"""Regenerate every PNG: 7 screens x (en, ar), 1920x1080, device scale factor 2, light mode. Uses the INSTALLED Chrome (no browser download).
    python screenshot.py [screens ...]        e.g.  python screenshot.py 1 2
The page files are rebuilt first (python build_data.py && python build_html.py) when the replays change."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
NAMES = {1: "plant", 2: "hydrai", 3: "alert", 4: "trace", 5: "whowhen", 6: "fleet", 7: "intercooler"}
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if __name__ == "__main__":
    screens = [int(a) for a in sys.argv[1:]] or list(NAMES)
    (HERE / "png").mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--force-color-profile=srgb", "--disable-lcd-text"])
        for lang in ("en", "ar"):
            ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2, color_scheme="light", locale="ar-SA" if lang == "ar" else "en-GB")
            for s in screens:
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.on("requestfailed", lambda r: errs.append("request " + r.url))
                page.goto((HERE / f"hydrai_dashboard_{lang}.html").as_uri() + f"?screen={s}")
                page.wait_for_timeout(300)
                out = HERE / "png" / f"s{s}_{NAMES[s]}_{lang}.png"
                page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1920, "height": 1080})
                print(out.name, "ERRORS: " + "; ".join(errs) if errs else "ok")
                page.close()
            ctx.close()
        b.close()
