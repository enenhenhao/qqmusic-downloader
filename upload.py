# -*- coding: utf-8 -*-
"""维护工具：通过 GitHub Contents API 上传本目录（github_release/）白名单文件
用法（任选其一）:
  set GH_TOKEN=<token> && python upload.py
  gh auth login 后直接: python upload.py
注意：只上传 WHITELIST 中的文件，绝不包含 cookie.txt 等敏感文件。
"""
import base64
import json
import os
import subprocess
import urllib.request

REPO = "enenhenhao/qqmusic-downloader"
HERE = os.path.dirname(os.path.abspath(__file__))
WHITELIST = ["README.md", "LICENSE", ".gitignore", "capture.py", "dl_js.py",
             "download.py", "login_browser.py", "qq_client_new.py", "qq_crypto.js",
             "qqmusic_api.py", "vip_download.py", "upload.py"]


def api(url, method="GET", data=None, token=""):
    headers = {"User-Agent": "upload-script", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    if not token:
        raise SystemExit("未找到 token：设置 GH_TOKEN 或先 gh auth login")

    branch = api(f"https://api.github.com/repos/{REPO}", token=token).get("default_branch", "main")
    print("默认分支:", branch)

    for fn in WHITELIST:
        p = os.path.join(HERE, fn)
        if not os.path.isfile(p):
            print("跳过（不存在）:", fn)
            continue
        with open(p, "rb") as f:
            content = f.read()
        data = {"message": f"update {fn}", "content": base64.b64encode(content).decode(), "branch": branch}
        try:
            api(f"https://api.github.com/repos/{REPO}/contents/{fn}", method="PUT", data=data, token=token)
            print("OK:", fn)
        except Exception as e:  # noqa: BLE001
            print("FAIL:", fn, e)


if __name__ == "__main__":
    main()
