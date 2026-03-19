#!/usr/bin/env python3
"""
飞书Wiki极简备份 - 最终版
直接调用OpenClaw飞书工具，Token自动刷新
"""
import os
import json
import subprocess
import time
import hashlib
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("~/.openclaw/workspace").expanduser()
CONFIG_FILE = WORKSPACE / "feishu-wiki-backup-config.json"
WIKI_NODE = "ZpB0w0DPqiNKohkNlOUc66Ign9e"

DEFAULT_FILES = ["AGENTS.md", "SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md", "TOOLS.md", "HEARTBEAT.md"]

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return None

def calc_md5(path):
    try:
        md5_hash = hashlib.md5()
        with open(path, "rb") as f:
            while chunk := f.read(4096):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except:
        return None

def create_doc_via_openclaw(title, content, wiki_node=WIKI_NODE):
    """直接调用OpenClaw飞书工具创建文档"""
    # 限制内容长度
    content = content[:40000]
    # 转义引号
    content = content.replace('"', '\\"').replace('\n', '\\n')
    
    cmd = f'openclaw call feishu_create_doc --title "{title}" --markdown "{content}" --wiki_node {wiki_node}'
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0 and "error" not in result.stdout.lower():
        return True
    return False

def sync_files():
    success = 0
    failed = 0
    
    print("\n📁 同步核心文件...")
    
    for filename in DEFAULT_FILES:
        filepath = WORKSPACE / filename
        
        if not filepath.exists():
            print(f"  ⚠️ 跳过: {filename}")
            continue
        
        content = read_file(filepath)
        if not content:
            continue
        
        # 添加MD5
        local_md5 = calc_md5(filepath)
        content = content.strip() + f"\n\n---\n<!-- MD5: {local_md5} -->"
        
        print(f"  🔄 {filename}")
        
        # 调用OpenClaw工具
        if create_doc_via_openclaw(filename, content):
            success += 1
        else:
            failed += 1
        
        time.sleep(0.5)
    
    # 日报
    print("\n📋 同步工作报...")
    daily_dir = WORKSPACE / "memory/daily-reports"
    if daily_dir.exists():
        for md_file in sorted(daily_dir.glob("*.md"))[:3]:
            content = read_file(md_file)
            if content:
                print(f"  🔄 {md_file.name}")
                if create_doc_via_openclaw(md_file.name, content):
                    success += 1
                else:
                    failed += 1
                time.sleep(0.5)
    
    return success, failed

def main():
    print("🔄 飞书Wiki极简备份")
    print("="*40)
    
    success, failed = sync_files()
    
    # 保存
    config = {"node_token": WIKI_NODE, "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M"), "file_count": success}
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    print("\n" + "="*40)
    print(f"✅ 备份完成！")
    print(f"   成功: {success} 个")
    print(f"   失败: {failed} 个")
    print(f"📁 位置: https://pq1dheaf25k.feishu.cn/wiki/{WIKI_NODE}")

if __name__ == "__main__":
    main()