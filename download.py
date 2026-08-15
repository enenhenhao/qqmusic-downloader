# -*- coding: utf-8 -*-
"""
QQ 音乐下载 CLI
用法：
  python download.py "雨滴咖啡馆"            # 搜索并交互选择，默认免费音质
  python download.py "晴天 周杰伦" --quality 320 --cookie cookie.txt
  python download.py "晴天 周杰伦" --quality flac --cookie cookie.txt --auto 0
参数：
  --quality 128|320|flac   音质（320/flac 需要登录 cookie + VIP/绿钻）
  --cookie  <文件路径>      登录 Cookie 文件（内容为 Cookie 头字符串，如 uin=xxx; qqmusic_key=xxx;）
  --auto <序号>            跳过交互，直接选搜索结果第 N 条（从 0 开始）
  --outdir <目录>          输出目录，默认 ./downloads
"""
import argparse
import os
import sys

import qqmusic_api as api


def parse_cookie(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().lstrip("\ufeff").strip()


def pick_result(results, auto):
    if auto is not None:
        return results[auto]
    print("\n搜索结果：")
    for i, s in enumerate(results):
        vip = " [VIP]" if s["payplay"] else ""
        print(f"  [{i}] {s['songname']} - {s['singer']} | {s['album']}{vip}")
    idx = input("输入序号下载（回车默认 0）：").strip()
    return results[int(idx) if idx else 0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword")
    ap.add_argument("--quality", default="128", choices=["128", "320", "flac"])
    ap.add_argument("--cookie", default="")
    ap.add_argument("--auto", type=int, default=None)
    ap.add_argument("--outdir", default="downloads")
    args = ap.parse_args()

    cookie = parse_cookie(args.cookie) if args.cookie else ""
    uin = "0"
    if cookie:
        import re
        m = re.search(r"(?:^|;)\s*uin=(\d+)", cookie)
        uin = m.group(1) if m else "0"

    print(f"搜索：{args.keyword}")
    results = api.search(args.keyword)
    if not results:
        print("未找到歌曲。")
        sys.exit(1)
    song = pick_result(results, args.auto)
    print(f"选中：{song['songname']} - {song['singer']} (mid={song['songmid']})")

    os.makedirs(args.outdir, exist_ok=True)
    print(f"获取播放地址（音质 {args.quality}）...")
    # 优先新协议（musics.fcg + ag-1 + sign），失败回退旧协议
    import qq_client_new as qc
    purl = ""
    try:
        purl, info = qc.vkey_new(song["songmid"], args.quality, uin, cookie)
        print("新协议:", info)
    except Exception as e:  # noqa: BLE001
        print("新协议失败:", e)
    if not purl:
        guid = api.gen_guid()
        purl = api.get_play_url(song["songmid"], guid, args.quality, uin, cookie)
    if not purl:
        if song["payplay"]:
            print("purl 为空：该歌曲为 VIP，需要提供有效的登录 Cookie（--cookie）后再试。")
        else:
            print("purl 为空：可能音质不可用，尝试 128。")
        sys.exit(2)

    ext = {"m4a": "m4a", "128": "mp3", "320": "mp3", "flac": "flac"}[args.quality]
    safe_name = "".join(c for c in f"{song['songname']}_{song['singer']}" if c not in '\\/:*?"<>|')
    path = os.path.join(args.outdir, f"{safe_name}.{ext}")

    last_err = None
    for cand in api.build_candidates(purl):
        try:
            n = api.download(cand, path, cookie)
            print(f"下载成功：{path}（{n} 字节）")
            sys.exit(0)
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"候选失败：{cand[:60]}... -> {e}")
    print(f"所有候选 URL 均失败：{last_err}")
    sys.exit(3)


if __name__ == "__main__":
    main()
