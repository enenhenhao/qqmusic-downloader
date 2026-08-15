# -*- coding: utf-8 -*-
"""
浏览器登录 QQ 音乐（Playwright + 本机 Edge/Chrome）
- 使用持久化浏览器配置目录 browser_profile/：登录一次后，下次通常免登录
- 登录成功后自动校验登录态并写入 cookie.txt
"""
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "cookie.txt")
PROFILE = os.path.join(BASE, "browser_profile")


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("请先安装: pip install playwright")
        sys.exit(1)

    os.makedirs(PROFILE, exist_ok=True)
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=PROFILE, channel="msedge", headless=False,
                viewport={"width": 1400, "height": 900},
                args=["--start-maximized"],
            )
        except Exception:
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=PROFILE, channel="chrome", headless=False,
                    viewport={"width": 1400, "height": 900},
                )
            except Exception as e:
                print("启动浏览器失败:", e)
                sys.exit(1)

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://y.qq.com/", timeout=60000)
        print("浏览器已打开 y.qq.com", flush=True)

        # 检查是否已有登录态（持久化配置目录可能保留上次登录）
        cookies = context.cookies()
        names = {c["name"] for c in cookies}
        already = "uin" in names and any(n in names for n in ("qqmusic_key", "qm_keyst", "skey", "p_skey"))
        if already:
            print("检测到已保存的登录态，无需重新扫码。", flush=True)
        else:
            print("请在窗口内登录你的 QQ 音乐账号（扫码最快），登录成功后脚本自动继续...", flush=True)

        deadline = time.time() + 300
        login_ok = False
        while time.time() < deadline:
            time.sleep(2)
            try:
                cookies = context.cookies()
            except Exception:  # noqa: BLE001
                continue
            names = {c["name"] for c in cookies}
            uin_ok = any(n in names for n in ("uin", "wxuin"))
            key_ok = any(n in names for n in ("qqmusic_key", "qm_keyst", "skey", "p_skey"))
            if uin_ok and key_ok:
                login_ok = True
                break

        if not login_ok:
            print("等待登录超时。", flush=True)
            context.close()
            sys.exit(1)

        cookies = context.cookies()
        line = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("value"))
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(line)
        keys = sorted(c["name"] for c in cookies)
        print("Cookie 已写入:", OUT, flush=True)
        print("含 qqmusic_key:", "qqmusic_key" in keys, "| uin:", next((c["value"] for c in cookies if c["name"] == "uin"), ""), flush=True)

        # 自动校验登录态
        try:
            sys.path.insert(0, BASE)
            import qq_client_new as qc
            st = qc.check_login(line)
            mark = "[OK] 有效" if st["valid"] else "[!] 未通过"
            print(f"登录校验: {mark} (uin={st['uin']}, 昵称={st['nick'] or '?'})", flush=True)
        except Exception as e:  # noqa: BLE001
            print("登录校验跳过:", e, flush=True)

        time.sleep(1)
        context.close()


if __name__ == "__main__":
    main()
