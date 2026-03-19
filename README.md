# 飞书Wiki极简备份

> 一句话说清楚要备份到哪里，剩下的自动搞定

## 一句话介绍

**小白也能用的飞书Wiki备份工具**：用户只需要说"帮我同步"，系统自动创建备份目录、同步核心文件、返回链接。每天自动备份，无需配置。

## 极简体验

### 首次使用
```
用户：帮我同步一下
↓
系统：✅ 收到！正在备份...
     📊 同步完成！成功 10 个文件
     📁 位置：https://xxx.feishu.cn/wiki/xxx
```

### 想换目录？
```
用户：帮我同步到 https://xxx.feishu.cn/wiki/新目录
↓
系统：✅ 已切换到新目录，立即同步...
```

---

## 功能特性

| 特性 | 说明 |
|------|------|
| 🗣️ 一句话启动 | 不需要链接，不需要配置 |
| 🔒 安全 | 仅同步到指定目录，不碰其他文件 |
| ⏰ 自动定时 | 每天自动备份，写入Cron |
| 🔄 增量同步 | 只同步有变化的文件 |
| 🔁 失败重试 | 自动重试3次 |
| 🔐 Token自动刷新 | 用OpenClaw飞书工具，Token自动刷新 |

## 默认同步内容

| 文件 | 说明 |
|------|------|
| AGENTS.md | Agent配置与安全红线 |
| SOUL.md | 人格定义与行为准则 |
| IDENTITY.md | 身份定义 |
| USER.md | 用户信息 |
| MEMORY.md | 长期记忆 |
| TOOLS.md | 工具配置 |
| HEARTBEAT.md | 心跳机制配置 |
| memory/daily-reports/* | 每日工作报 |

## 工作原理

```mermaid
flowchart TD
    A[用户说"帮我同步"] --> B{首次使用?}
    B -->|是| C[自动创建备份目录]
    B -->|否| D[使用已有目录]
    C --> E[调用OpenClaw飞书工具]
    D --> E
    E --> F[Token自动刷新]
    F --> G[同步7个核心文件]
    G --> H[同步日报]
    H --> I[返回链接给用户]
```

## 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/zhangyh9/feishu-wiki-backup.git
cd feishu-wiki-backup
```

### 2. 测试
```bash
python3 backup.py test
# 应该输出：✅ 飞书工具正常
```

### 3. 首次同步
```bash
python3 backup.py run
# 自动同步所有文件，返回备份位置链接
```

### 4. 设置定时（可选）
```bash
# 每天22:30自动同步
(crontab -l 2>/dev/null; echo "30 22 * * * cd /path/to/feishu-wiki-backup && python3 backup.py run") | crontab -
```

## 命令说明

| 命令 | 说明 |
|------|------|
| `python3 backup.py run` | 执行一次同步 |
| `python3 backup.py test` | 测试飞书工具是否正常 |
| `python3 backup.py status` | 查看上次同步状态 |

## 配置文件

首次运行后，会在 `~/.openclaw/workspace/` 下创建 `feishu-wiki-backup-config.json`：

```json
{
  "node_token": "ZpB0w0DPqiNKohkNlOUc66Ign9e",
  "last_sync": "2026-03-19 08:55",
  "file_count": 10
}
```

## 技术细节

- **Token来源**：OpenClaw飞书插件（自动刷新，不过期）
- **备份位置**：飞书Wiki知识库
- **同步方式**：通过飞书API创建/更新文档
- **依赖**：仅Python 3（需安装OpenClaw）

## 常见问题

**Q: 需要配置Token吗？**
A: 不需要！使用OpenClaw飞书工具，Token自动刷新。

**Q: 同步失败怎么办？**
A: 自动重试3次，失败记录日志。

**Q: 如何修改备份位置？**
A: 代码中修改 `WIKI_NODE` 常量，或者发新链接让系统切换。

**Q: 支持定时吗？**
A: 支持，可用cron设置定时任务。

## 目录结构

```
feishu-wiki-backup/
├── README.md          # 本文件
├── SKILL.md          # 技能定义
├── backup.py         # 主脚本（复杂版）
└── simple-backup.py # 极简版
```

## 许可证

MIT License

---

**一句话总结**：用户说"帮我同步" → 系统自动备份 → 返回链接。搞定！