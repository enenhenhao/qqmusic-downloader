# -*- coding: utf-8 -*-
"""
浏览器抓包 v3：分析播放按钮 → 触发播放 → 记录真实 musicu/vkey 请求与音频
"""
import json
import os
import re
import time

BASE = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(BASE, "cookie.txt")
AUDIO_URL_FILE = os.path.join(BASE, "audio_url.txt")
VKEY_FILE = os.path.join(BASE, "vkey_capture.json")
MID = "0039MnYb0qxYhV"


def parse_cookies(text: str) -> list:
    out = []
    for part in text.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        out.append({"name": k.strip(), "value": v.strip(), "domain": ".qq.com", "path": "/"})
    return out


def main():
    from playwright.sync_api import sync_playwright

    with open(COOKIE_FILE, encoding="utf-8") as f:
        cookie_text = f.read().strip()
    cookies = parse_cookies(cookie_text)

    audio_hit = []
    vkey_reqs = []

    def on_request(req):
        u = req.url
        try:
            if "musicu.fcg" in u:
                rec = {"method": req.method, "url": u}
                if req.post_data:
                    rec["post"] = req.post_data[:4000]
                vkey_reqs.append(rec)
                with open(VKEY_FILE, "w", encoding="utf-8") as f:
                    json.dump(vkey_reqs, f, ensure_ascii=False, indent=1)
                print("musicu:", req.method, u[:200], flush=True)
            if re.search(r"stream\.qqmusic\.qq\.com|dl\.stream\.", u):
                audio_hit.append(u)
                with open(AUDIO_URL_FILE, "w", encoding="utf-8") as f:
                    f.write(u)
                print("*** AUDIO:", u[:250], flush=True)
        except Exception:  # noqa: BLE001
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False)
        context = browser.new_context(
            viewport={"width": 1500, "height": 950},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        )
        context.add_cookies(cookies)
        page = context.new_page()
        page.on("request", on_request)
        page.goto("https://y.qq.com/n/ryqq/songDetail/" + MID, timeout=60000)
        time.sleep(8)

        # 分析播放按钮候选
        cands = page.evaluate("""() => {
            const out = [];
            const els = document.querySelectorAll('a,button,div,span,i');
            for (const e of els) {
                const cls = (e.className && typeof e.className === 'string') ? e.className : '';
                const txt = (e.innerText || '').trim().slice(0, 20);
                if (/play/i.test(cls) || /播放|试听/.test(txt)) {
                    if (e.offsetParent !== null) {
                        out.push({tag: e.tagName, cls: cls.slice(0, 80), txt});
                    }
                }
            }
            return out.slice(0, 40);
        }""")
        print("播放按钮候选:", flush=True)
        for c in cands:
            print("  ", c, flush=True)

        # 页面 VIP 状态线索
        vip_text = page.evaluate("""() => {
            const t = document.body.innerText;
            const i = t.indexOf('绿钻');
            return i >= 0 ? t.slice(Math.max(0,i-60), i+60) : 'NO 绿钻 text';
        }""")
        print("绿钻线索:", vip_text.replace('\\n', ' ')[:200], flush=True)

        # 点击策略：优先含 play 的可点元素
        clicked = False
        for cand in cands:
            tag, cls, txt = cand["tag"], cand["cls"], cand["txt"]
            sel = f"{tag.lower()}[class='{cls}']"
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    loc.click(timeout=2000)
                    print("clicked:", tag, cls, txt, flush=True)
                    clicked = True
                    time.sleep(5)
                    if audio_hit:
                        break
            except Exception:  # noqa: BLE001
                continue
        if not clicked:
            print("未能点击任何播放按钮", flush=True)

        page.screenshot(path=os.path.join(BASE, "page_state.png"))

        deadline = time.time() + 90
        while time.time() < deadline and not audio_hit:
            time.sleep(3)
            print("waiting...", flush=True)

        print("DONE audio:", len(audio_hit), "musicu reqs:", len(vkey_reqs), flush=True)
        browser.close()


if __name__ == "__main__":
    main()
