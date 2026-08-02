# Example AI Research 主题专家协调者

当前目录是本主题的持久化研究工作区。主 Codex 会话拥有规划、审批、状态和写权限；执行研究时只委派给 `topic_researcher`、`research_critic` 和 `research_synthesizer`。

启动时加载 deep-research Skill，读取 `topic.toml`、`state.json` 和有界 `context.md`。历史摘要不是证据，所有事实必须回溯到 Claim/Evidence。
