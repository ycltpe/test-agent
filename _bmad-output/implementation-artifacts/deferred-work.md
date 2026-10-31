# Deferred Work

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-project-skeleton-envelope.md`
  summary: 信封 `timestamp` 是否要求带时区（拒绝 naive datetime）未在 Story 1.1 spec 中规定
  evidence: 评审发现 `Envelope` 接受无时区 timestamp（若属实则 medium：跨跳时间比较崩溃/事件乱序）；spec 各层均未涉及时区策略。 settle：由消费 timestamp 的后续 Story spec（如 1.3 会话管理 / 1.5 Langfuse 追踪）明确时区契约后补校验器。

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-project-skeleton-envelope.md`
  summary: 信封字符串标识符（session_id/house_id/trace_id）是否要求非空未在 Story 1.1 spec 中规定
  evidence: 评审发现空字符串可通过校验（若属实则 medium：会话/路由查找失效）；spec 未规定非空约束。settle：由后续 Story spec 明确标识符规则后补 `min_length` 校验。
