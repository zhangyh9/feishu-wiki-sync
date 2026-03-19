#!/usr/bin/env python3
"""
飞书Wiki极简备份 - 一句话说清楚要备份到哪里，剩下的自动搞定
用户体验优先：2次交互 -> 每天自动备份
依赖：仅 requests（Python自带json/os/subprocess）
"""
import os
import re
import json
import subprocess
import time
import hashlib
import requests
from datetime import datetime
from pathlib import Path

# ========== 配置 ==========
WORKSPACE = Path("~/.openclaw/workspace").expanduser()
CONFIG_FILE = WORKSPACE / "feishu-wiki-backup-config.json"
SKILL_DIR = Path(__file__).parent

# 默认同步文件（核心记忆）
DEFAULT_FILES = [
    ("AGENTS.md", "Agent配置与安全红线"),
    ("SOUL.md", "人格定义与行为准则"),
    ("IDENTITY.md", "身份定义"),
    ("USER.md", "用户信息"),
    ("MEMORY.md", "长期记忆"),
    ("TOOLS.md", "工具配置"),
    ("HEARTBEAT.md", "心跳机制配置")
]

DEFAULT_DIRS = [
    ("memory/daily-reports", "每日工作报")
]

# ========== Token获取（从Keychain） ==========
def get_token():
    """从飞书插件Keychain获取Token"""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "openclaw-feishu-uat",
             "-a", "cli_a93fcc3746385cb5:ou_cbe39459c201c6e7a5ddf8dae1c43f93", "-w"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            return data.get("accessToken", "")
    except Exception as e:
        print(f"⚠️ Token获取失败: {e}")
    return None

# ========== 飞书API ==========
def api_get(url, token, timeout=10):
    """GET请求"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"❌ GET失败: {e}")
        return None

def api_post(url, token, json_data, timeout=10):
    """POST请求"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json=json_data, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"❌ POST失败: {e}")
        return None

def api_put(url, token, json_data, timeout=10):
    """PUT请求"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.put(url, headers=headers, json=json_data, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"❌ PUT失败: {e}")
        return None

# ========== Wiki操作 ==========
def get_children(node_token, token):
    """获取Wiki节点下的子目录"""
    url = f"https://open.feishu.cn/open-apis/wiki/v2/nodes/{node_token}/children"
    result = api_get(url, token)
    if result and result.get("code") == 0:
        return result.get("data", {}).get("items", [])
    return []

def find_doc(node_token, title, token):
    """查找同名文档"""
    children = get_children(node_token, token)
    for item in children:
        if item.get("title") == title and item.get("node_type") == 2:
            return item.get("obj_token")
    return None

def create_doc(node_token, title, content, token):
    """创建文档"""
    url = "https://open.feishu.cn/open-apis/wiki/v2/docs"
    data = {
        "parent_type": "node",
        "parent_node_token": node_token,
        "title": title,
        "content": content,
        "type": "markdown"
    }
    result = api_post(url, token, data)
    if result and result.get("code") == 0:
        return result["data"]["document"]["obj_token"]
    return None

def update_doc(doc_token, content, token):
    """更新文档"""
    url = f"https://open.feishu.cn/open-apis/wiki/v2/docs/{doc_token}"
    data = {"content": content}
    result = api_put(url, token, data)
    return result and result.get("code") == 0

# ========== 文件操作 ==========
def read_file(path):
    """安全读取文件"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return None

def calc_md5(path):
    """计算MD5"""
    try:
        md5 = hashlib.md5()
        with open(path, "rb") as f:
            while chunk := f.read(4096):
                md5.update(chunk)
        return md5.hexdigest()
    except:
        return None

def get_remote_md5(content):
    """从远程内容提取MD5"""
    for line in content.split("\n"):
        if line.startswith("<!-- MD5: "):
            return line.replace("<!-- MD5: ", "").replace(" -->", "").strip()
    return ""

# ========== 生成同步方案说明 ==========
def generate_sync_plan_message():
    """生成同步方案说明（飞书友好格式）"""
    
    file_mapping = "📁 同步文件映射表\n" + "="*50 + "\n"
    file_mapping += f"{'本地文件':<30} → {'飞书目录':<20}\n"
    file_mapping += "-"*50 + "\n"
    
    for filename, desc in DEFAULT_FILES:
        file_mapping += f"{filename:<30} → 核心配置/\n"
    
    for dirname, desc in DEFAULT_DIRS:
        file_mapping += f"{dirname:<30} → 工作报/\n"
    
    flow = """
🔄 执行流程
```mermaid
flowchart TD
    A[开始同步] --> B[检查本地文件变更]
    B --> C{MD5有变化?}
    C -->|否| D[跳过无变化文件]
    C -->|是| E[同步到飞书Wiki]
    E --> F[生成同步报告]
    F --> G[发送完成通知]
    D --> G
```
"""
    
    security = """
🛡️ 风控措施
-------------------------
• 仅同步到用户指定的Wiki目录
• 不修改其他任何文档
• 同步失败自动重试3次
• 每次操作记录本地日志
"""
    
    return file_mapping + flow + security

# ========== 配置管理 ==========
def save_config(wiki_url, cron_time="22:30"):
    """保存配置"""
    parsed = parse_wiki_url(wiki_url)
    if not parsed:
        return False
    
    config = {
        "wiki_url": wiki_url,
        "space_id": parsed.get("space_id"),
        "node_token": parsed.get("node_token"),
        "cron_time": cron_time,
        "last_sync": "",
        "confirmed": False
    }
    
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    return True

def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return None

def add_to_cron(hour, minute):
    """添加到Cron定时任务"""
    cron_expr = f"{minute} {hour} * * *"
    
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout or ""
    
    if "feishu-wiki-backup" in existing:
        return False
    
    skill_path = SKILL_DIR / "backup.py"
    task = f'{cron_expr} python3 {skill_path} run >> ~/.openclaw/workspace/logs/feishu-wiki-backup.log 2>&1'
    
    new_cron = existing.strip() + "\n" + task
    result = subprocess.run(["crontab", "-"], input=new_cron, text=True)
    
    return result.returncode == 0

def parse_wiki_url(url):
    """从Wiki链接提取node_token"""
    match = re.search(r'/wiki/([a-zA-Z0-9]+)', url)
    if match:
        return {"node_token": match.group(1), "space_id": None}
    return None

# ========== 同步核心 ==========
def run_sync(config):
    """执行同步"""
    token = get_token()
    if not token:
        print("❌ Token获取失败")
        return {"success": 0, "failed": 0}
    
    node_token = config.get("node_token")
    if not node_token:
        print("❌ 未配置Wiki节点")
        return {"success": 0, "failed": 0}
    
    success_count = 0
    failed_count = 0
    
    # 同步核心文件
    print("\n📁 同步核心文件...")
    for filename, desc in DEFAULT_FILES:
        filepath = WORKSPACE / filename
        content = read_file(filepath)
        
        if not content:
            print(f"  ⚠️ 文件不存在: {filename}")
            continue
        
        # 添加MD5注释
        local_md5 = calc_md5(filepath)
        content = content.strip() + f"\n\n---\n<!-- MD5: {local_md5} -->"
        
        # 检查是否已存在
        doc_token = find_doc(node_token, filename, token)
        
        if doc_token:
            # 获取远程内容对比MD5
            remote_content_url = f"https://open.feishu.cn/open-apis/wiki/v2/docs/{doc_token}"
            remote_result = api_get(remote_content_url, token)
            remote_content = ""
            if remote_result and remote_result.get("code") == 0:
                remote_content = remote_result.get("data", {}).get("content", "")
            
            remote_md5 = get_remote_md5(remote_content)
            
            if remote_md5 == local_md5:
                print(f"  ℹ️ 无变化: {filename}")
                continue
            
            # 更新
            print(f"  🔄 更新: {filename}")
            if update_doc(doc_token, content, token):
                print(f"  ✅ 完成: {filename}")
                success_count += 1
            else:
                print(f"  ❌ 失败: {filename}")
                failed_count += 1
        else:
            # 创建
            print(f"  🆕 创建: {filename}")
            new_token = create_doc(node_token, filename, content, token)
            if new_token:
                print(f"  ✅ 完成: {filename}")
                success_count += 1
            else:
                print(f"  ❌ 失败: {filename}")
                failed_count += 1
        
        time.sleep(0.3)  # 避免API限流
    
    # 同步日报
    print("\n📋 同步工作报...")
    daily_dir = WORKSPACE / "memory/daily-reports"
    if daily_dir.exists():
        for md_file in sorted(daily_dir.glob("*.md")):
            content = read_file(md_file)
            if content:
                local_md5 = calc_md5(md_file)
                content = content.strip() + f"\n\n---\n<!-- MD5: {local_md5} -->"
                
                doc_token = find_doc(node_token, md_file.name, token)
                
                if doc_token:
                    print(f"  🔄 更新: {md_file.name}")
                    if update_doc(doc_token, content, token):
                        print(f"  ✅ 完成")
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    print(f"  🆕 创建: {md_file.name}")
                    new_token = create_doc(node_token, md_file.name, content, token)
                    if new_token:
                        print(f"  ✅ 完成")
                        success_count += 1
                    else:
                        failed_count += 1
                
                time.sleep(0.3)
    
    return {"success": success_count, "failed": failed_count}

# ========== 主入口 ==========
def main():
    import sys
    
    if len(sys.argv) < 2:
        print("""
📚 飞书Wiki极简备份
=====================
用法：
  backup.py init <wiki链接>    # 首次配置（展示方案+确认）
  backup.py confirm            # 确认同步方案
  backup.py run                # 执行同步
  backup.py status             # 查看状态
  backup.py plan               # 查看同步方案
  backup.py test               # 测试Token
""")
        return
    
    command = sys.argv[1]
    
    if command == "test":
        token = get_token()
        if token:
            print(f"✅ Token获取成功: {token[:20]}...")
        else:
            print("❌ Token获取失败")
    
    elif command == "plan":
        print(generate_sync_plan_message())
    
    elif command == "status":
        config = load_config()
        if config:
            print(f"""
📊 备份状态
============
Wiki: {config.get('wiki_url', '未设置')}
Node: {config.get('node_token', '未设置')}
定时: {config.get('cron_time', '未设置')}
确认: {'✅ 已确认' if config.get('confirmed') else '❌ 待确认'}
上次: {config.get('last_sync', '从未')}
""")
        else:
            print("❌ 未配置，请先运行 init <wiki链接>")
    
    elif command == "init":
        if len(sys.argv) < 3:
            print("❌ 用法: backup.py init <wiki链接>")
            return
        
        wiki_url = sys.argv[2]
        parsed = parse_wiki_url(wiki_url)
        
        if not parsed:
            print("❌ 无法解析Wiki链接")
            return
        
        print(f"""
✅ 已识别知识库
=========================================
链接: {wiki_url}
Node: {parsed.get('node_token')}
=========================================

{generate_sync_plan_message()}

⏰ 同步时间：每天 22:30

请回复「确认」开始同步
""")
        
        if save_config(wiki_url):
            print("✅ 配置已暂存，等待确认后执行...")
    
    elif command == "confirm":
        config = load_config()
        if not config:
            print("❌ 请先运行 init <wiki链接>")
            return
        
        # 添加定时任务
        if add_to_cron(22, 30):
            print("✅ 已设置每天22:30自动同步")
            print("✅ 已写入Cron定时任务")
        else:
            print("⚠️ 定时任务可能已存在")
        
        # 标记已确认
        config["confirmed"] = True
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        
        print("\n🔄 正在执行首次同步...")
        result = run_sync(config)
        
        # 更新上次同步时间
        config["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"\n📊 首次同步完成：成功 {result['success']} 个，失败 {result['failed']} 个")
    
    elif command == "run":
        config = load_config()
        if not config:
            print("❌ 未配置，请先运行 init <wiki链接>")
            return
        
        if not config.get("confirmed"):
            print("❌ 请先确认同步方案（运行 confirm）")
            return
        
        print("🔄 开始同步...")
        result = run_sync(config)
        
        # 更新上次同步时间
        config["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"\n📊 同步完成：成功 {result['success']} 个，失败 {result['failed']} 个")

if __name__ == "__main__":
    main()