# -*- coding: utf-8 -*-
"""
VIP 歌曲下载：flac → 320 → 128 自动降级
- 启动时自动检查登录态（cookie 过期会自动拉起浏览器重新登录）
- 优先新协议（musics.fcg + ag-1 + sign），失败回退旧协议
用法：python vip_download.py "晴天 周杰伦" [--auto 0]
"""
import argparse
import os
import re
import subprocess
import sys
import time

import qqmusic_api as api
import qq_client_new as qc

BASE = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(BASE, "cookie.txt")
OUTDIR = os.path.join(BASE, "downloads")


def read_cookie(path=COOKIE_FILE) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        c = f.read()
    c = c.lstrip("\ufeff").strip()
    if c.startswith("#"):
        return ""
    return c


def ensure_login() -> str:
    """确保 cookie 有效；无效则自动打开浏览器重新登录"""
    cookie = read_cookie()
    if cookie:
        st = qc.check_login(cookie)
        mark = "[OK] 有效" if st["valid"] else "[FAIL] 无效/已过期"
        print(f"登录检查: {mark} (uin={st['uin']}, 昵称={st['nick'] or '?'})", flush=True)
        if st["valid"]:
            return cookie
    else:
        print("未找到有效 cookie.txt", flush=True)

    print("正在打开浏览器重新登录 —— 请在弹出的窗口中扫码登录 QQ 音乐...", flush=True)
    try:
        subprocess.run([sys.executable, os.path.join(BASE, "login_browser.py")], timeout=400)
    except Exception as e:  # noqa: BLE001
        print("自动登录启动失败，请手动运行: python login_browser.py |", e)
        sys.exit(1)

    cookie = read_cookie()
    if not cookie:
        print("登录未完成（cookie.txt 仍为空）。")
        sys.exit(1)
    st = qc.check_login(cookie)
    if not st["valid"]:
        print(f"重新登录后校验仍未通过 (code={st['code']})，请检查网络后重试。")
        sys.exit(1)
    print(f"重新登录成功: uin={st['uin']} 昵称={st['nick']}", flush=True)
    return cookie


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword")
    ap.add_argument("--auto", type=int, default=0)
    ap.add_argument("--cookie", default=COOKIE_FILE)
    ap.add_argument("--no-relogin", action="store_true", help="cookie 失效时不要自动重登")
    args = ap.parse_args()

    cookie = read_cookie(args.cookie)
    if not args.no_relogin:
        cookie = ensure_login()
    elif not cookie:
        print("cookie.txt 为空，且已指定 --no-relogin。")
        sys.exit(1)

    m = re.search(r"(?:^|;)\s*uin=(\d+)", cookie)
    uin = m.group(1) if m else "0"

    print("搜索:", args.keyword)
    results = api.search(args.keyword, 10)
    if not results:
        print("未找到歌曲")
        sys.exit(1)
    song = results[args.auto]
    print(f"选中: {song['songname']} - {song['singer']} (mid={song['songmid']}) payplay={song['payplay']}")

    os.makedirs(OUTDIR, exist_ok=True)
    safe_name = "".join(c for c in f"{song['songname']}_{song['singer']}" if c not in '\\/:*?"<>|')

    for quality in ("flac", "320", "128"):
        print(f"-- 尝试音质 {quality} ...", flush=True)
        purl = ""
        info = ""
        try:  # 新协议优先
            purl, info = qc.vkey_new(song["songmid"], quality, uin, cookie)
        except Exception as e:  # noqa: BLE001
            info = f"新协议异常: {e}"
        if not purl:  # 回退旧协议
            guid = api.gen_guid()
            try:
                purl = api.get_play_url(song["songmid"], guid, quality, uin, cookie)
            except Exception as e:  # noqa: BLE001
                info += f" | 旧协议异常: {e}"
        if not purl:
            print(f"  purl 为空（{info or '无权限或音质不可用'}）", flush=True)
            continue

        ext = {"m4a": "m4a", "128": "mp3", "320": "mp3", "flac": "flac"}[quality]
        path = os.path.join(OUTDIR, f"{safe_name}.{ext}")
        ok = False
        for cand in api.build_candidates(purl):
            try:
                n = api.download(cand, path, cookie)
                print(f"  下载成功: {path} ({n} 字节)", flush=True)
                ok = True
                break
            except Exception as e:  # noqa: BLE001
                print("  候选失败:", e, flush=True)
        if ok:
            # 魔数验证（按文件真实内容判断，与音质无关）
            with open(path, "rb") as f:
                head = f.read(16)
            if head[:4] == b"fLaC":
                print("  魔数验证: FLAC [OK]", flush=True)
            elif head[:3] == b"ID3" or head[:2] == b"\xff\xfb":
                print("  魔数验证: MP3 [OK]", flush=True)
            elif b"ftyp" in head[:12]:
                print("  魔数验证: MP4/M4A [OK]", flush=True)
            else:
                print("  魔数验证: 无法识别（文件可能仍可播放）", head[:16], flush=True)
            sys.exit(0)
    print("所有音质均失败。若为 VIP 歌曲，请确认账号有对应权限（绿钻）且 cookie 未过期。")
    sys.exit(2)


if __name__ == "__main__":
    main()
