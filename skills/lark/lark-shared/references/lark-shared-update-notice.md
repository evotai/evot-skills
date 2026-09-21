# 更新与 `_notice`

lark-cli 命令执行后，如果检测到新版本，JSON 输出中会包含 `_notice.update` 字段（含 `message`、`command` 等）。

除非用户正在询问更新、版本或 notice，否则不要把 `_notice` 原样复制为当前任务的主要答案，也不要为了 notice 中断当前任务去反复查 help。

需要稳定 JSON 给脚本或机器读取时，可以在命令前设置：

```bash
LARKSUITE_CLI_NO_UPDATE_NOTIFIER=1 LARKSUITE_CLI_NO_SKILLS_NOTIFIER=1 <lark-cli command>
```

当你在输出中看到 `_notice.update` 时，先完成用户当前请求；如仍相关，再简短告知可运行：

```bash
lark-cli update
```

**重要**：始终使用 `lark-cli update` 更新，它会同时更新 CLI 和 AI Skills。

## 例外：skill 文档里的命令在本机不存在

当一个在 skill 文档中有记载的 shortcut（如 `contact +search-bot`）返回 `unknown subcommand`，**且同一输出中带有 `_notice.update`**，这是 skill 文档领先于本机 CLI 版本。此时不要换写法重试，也不要当作“搜不到”继续下一个策略：

1. 先判断这个命令对当前任务是否必需。非必需（只是一条备选搜索路径）就直接跳过，并在最终回答里提一句可升级。
2. 必需时，先 `lark-cli update`，再重新执行原命令。

另外两类 notice：
- `_notice.skills`：本地 Skills 与当前 CLI 不同步。
- `_notice.deprecated_command`：本次使用了兼容保留的旧命令；后续调用改用 `replacement`。如果同时提供 `action: "lark-cli update"`，同样建议升级。
