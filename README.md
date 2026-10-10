# 收工交接

给明天的自己留一段能接着干的记录。只记做到哪、卡在哪、明天第一件事，不写周报，不写复盘。

这是一个 Cursor skill。说「交接」就收工，说「接着昨天」就开工。交接写在个人目录，不进项目仓库。

---

## 怎么用

在 Cursor 对话里说：

| 你说 | 它做什么 |
|------|----------|
| 交接、收工、交给明天 | 看当前对话和 git 状态，写下交接 |
| 接着昨天、昨天做到哪、继续上次 | 读上次交接，用四行复述。你同意之前不改代码 |

不能双击运行。`scripts/handoff.py` 要在终端里带命令执行，完整交接是在对话里说的。

---

## 安装

从本仓库克隆，放到 Cursor 能读到的 skill 目录。目录名用 `handoff`，里面要有 `SKILL.md`。个人 skill，所有项目都能用。

```bash
git clone https://github.com/nuvcloud88-star/handoff.git
mkdir -p ~/.cursor/skills
ln -s "$(cd handoff && pwd)" ~/.cursor/skills/handoff
```

装好后新开一个对话，再说「交接」。

---

## 交接长什么样

每条一两句。没有就写「无」。「明天第一件」只能有一件，写下一步动作，不写目标。

```markdown
# 交接

日期：YYYY-MM-DD
项目：<工作区绝对路径>

## 做到哪
- ...

## 卡在哪
- ...

## 明天第一件
一件事。具体到打开哪个文件，或跑哪条命令。

## 别动
明天不要重做、不要顺手改的东西。
```

文件在 `~/.cursor/handoffs/`，按项目路径分开。

---

## 脚本

叙述由对话来写，脚本看不到聊天内容。它只负责查 git、算路径、读写文件。在本仓库目录下执行：

```bash
python3 scripts/handoff.py collect   # 日期、项目路径、git 状态
python3 scripts/handoff.py show      # 读上次交接；没有则退出码 1
python3 scripts/handoff.py save      # 从标准输入覆盖写入
```

需要 Python 3。

---

## 目录

```
handoff/
├── README.md
├── SKILL.md              # 给 Cursor 看的说明
└── scripts/handoff.py    # 收集事实、读写交接
```
