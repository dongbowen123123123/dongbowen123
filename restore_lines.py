"""把交付的 index.html 恢复成多行（LF 换行），并做完整性校验。

原因：此前写文件时用了 CRLF，经下载/传输环节后换行被丢弃，整份文件变成一行。
改用 LF 可以如实保留换行结构。
"""
import re
from pathlib import Path

DESKTOP = Path(r"C:\Users\25391\Desktop")
BACKUP_DIR = Path(r"C:\Users\25391\Documents\deepseek-harness\default-workspace")

# 找到实际的那份成品（可能是 index.html、index(7).html 等）
candidates = sorted(DESKTOP.glob("index*.html"))
if not candidates:
    raise SystemExit("桌面上找不到 index*.html")

# 选体积最大的那份（成品约 98KB）
src = max(candidates, key=lambda p: p.stat().st_size)
raw = src.read_bytes()
print(f"源文件: {src.name}  ({len(raw):,} 字节)")

text = raw.decode("utf-8")

# 1) 统一换行
text = text.replace("\r\n", "\n").replace("\r", "\n")

# 2) 如果已经被压成一行，按标签恢复结构（仅当换行数异常少时）
line_count = text.count("\n") + 1
print(f"当前行数: {line_count}")
if line_count < 50:
    print("检测到结构被压平，正在按标签嵌套重新排版…")

    # 保护 <style> / <script> 内容
    style_m = re.search(r"<style>(.*?)</style>", text, re.S)
    script_m = re.search(r"<script>(.*?)</script>", text, re.S)
    style_body = style_m.group(1)
    script_body = script_m.group(1)
    text = text.replace(style_body, "\x00S\x00", 1)
    text = text.replace(script_body, "\x00J\x00", 1)

    BLOCK = ("html", "head", "body", "style", "script", "meta", "link", "title",
             "div", "section", "aside", "main", "nav", "ul", "ol", "li", "template",
             "svg", "defs", "g", "clipPath", "header", "footer", "h1", "h2", "h3",
             "p", "button", "audio", "source", "canvas")

    text = re.sub(r"<(" + "|".join(BLOCK) + r")(?=[\s>/])",
                  lambda m: "\n<" + m.group(1), text, flags=re.I)
    text = re.sub(r"</(" + "|".join(BLOCK) + r")>",
                  lambda m: "\n</" + m.group(1) + ">", text, flags=re.I)

    text = text.replace("\x00S\x00", style_body, 1).replace("\x00J\x00", script_body, 1)

    # 去掉空行
    lines = [ln.rstrip() for ln in text.split("\n")]
    out = []
    for ln in lines:
        if ln.strip() == "" and out and out[-1].strip() == "":
            continue
        out.append(ln)
    text = "\n".join(out)

# 3) 写入桌面（覆盖成品名），LF 换行
target = DESKTOP / "index.html"
target.write_bytes(text.encode("utf-8"))
print(f"已写入: {target}")

# 4) 同步一份到工作区
BACKUP_DIR.joinpath("index-page.html").write_bytes(text.encode("utf-8"))

# 5) 清理旧的重复下载文件
for p in candidates:
    if p.name != "index.html":
        p.unlink()
        print(f"已清理旧的重复文件: {p.name}")

# 6) 校验
final = target.read_bytes().decode("utf-8")
checks = {
    "多行结构": final.count("\n") + 1 > 100,
    "头像 data URI": "data:image/webp;base64" in final,
    "头像回退模板": 'id="avatarFallback"' in final,
    "流星画布": 'id="meteors"' in final,
    "流星函数": "spawnMeteor" in final and "startMeteors" in final,
    "黑洞入场动画": 'id="blackhole"' in final,
    "背景音乐": "outer/url?id=2723752193" in final,
    "audio 无 crossorigin": re.search(r"<audio[^>]*crossorigin\s*=", final) is None,
    "单曲循环": re.search(r"<audio[^>]*\bloop\b", final) is not None,
    "侧栏 5 个导航": final.count('class="nav-item') == 5,
    "5 个内容分区": final.count('id="view-') == 5,
    "姓名=拾光": ">拾光<" in final,
    "无真实姓名": "董博文" not in final,
    "脱敏邮箱": "2539****15@qq.com" in final,
    "CSS 大括号平衡": final.count("{") == final.count("}"),
}
print(f"\n行数: {final.count(chr(10)) + 1}   字节: {len(final.encode('utf-8')):,}")
print("=" * 46)
allok = True
for k, v in checks.items():
    print(f"  {'✓' if v else '✗'} {k}")
    allok &= v
print("=" * 46)
print("全部通过 ✓" if allok else "存在问题 ✗")
