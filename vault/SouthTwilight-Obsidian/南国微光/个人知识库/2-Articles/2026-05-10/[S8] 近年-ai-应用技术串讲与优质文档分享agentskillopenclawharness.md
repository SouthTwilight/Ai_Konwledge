---
title: 近年 AI 应用技术串讲与优质文档分享｜Agent、Skill、OpenClaw、Harness……
source: https://oigi8odzc5w.feishu.cn/wiki/WBMfwiNkfi6uNFkRtXdcavDzn0e
source_name: feishu
date_processed: '2026-05-10'
tags:
- llm
- agent
- rag
relevance: 8
level: l2
hash: ''
---
# 近年 AI 应用技术串讲与优质文档分享｜Agent、Skill、OpenClaw、Harness……

> Source: [feishu](https://oigi8odzc5w.feishu.cn/wiki/WBMfwiNkfi6uNFkRtXdcavDzn0e)

## Summary

**TL;DR:** 本文系统梳理了近年AI应用核心技术，涵盖LLM、RAG、Agent及工程化实践，重点解析了Agent技能封装与OpenClaw框架。

文章首先回顾了LLM基础架构，指出Decoder-only架构已成为主流，并介绍了Prompt工程与LoRA微调作为低成本优化手段。接着详细阐述了RAG检索增强生成、Function Calling工具调用以及MCP模型上下文协议在连接外部数据中的关键作用。核心部分深入解析了Agent的“思考-行动-观察”循环机制，以及Multi-Agent系统在处理复杂任务时的协作模式。文章特别强调了Context Engineering在筛选和组织上下文信息中的重要性，以最大化模型推理能力。此外，介绍了Agent Skills作为一种轻量级封装格式，用于沉淀SOP并实现能力的低门槛复用。最后，文章探讨了OpenClaw开源框架与Harness Engineering工程实践，展示了如何通过构建受控环境提升Agent在长周期任务中的可靠性。

## Key Points

- Decoder-only架构是当前LLM的主流选择，Prompt工程和LoRA微调是提升模型效果而不改变底层参数的高效手段。
- RAG通过检索外部知识库增强生成准确性，而MCP协议则标准化了模型与外部工具及数据源的连接方式。
- Agent本质是对人类“思考-行动-观察”循环的模拟，由提示词、LLM和工具构成，能自主完成复杂任务。
- Context Engineering关注如何高质量筛选、压缩和组织上下文信息，是提升Agent决策能力的关键工程环节。
- Agent Skills将整套能力封装为可复用模块，适合SOP沉淀，支持Agent按需激活和渐进式披露内容。
- Harness Engineering强调通过构建约束机制和反馈回路，为Agent提供受控环境以确保长周期任务的可靠执行。

## Related

[[LLM]] [[AI Agent]] [[RAG]] [[Prompt Engineering]]

## Tags

#llm #agent #rag

## 原文内容

近年 AI 应用技术串讲与优质文档分享｜Agent、Skill、OpenClaw、Harness……
LLM
[Attention Is All You Need](https://arxiv.org/abs/1706.03762)
tree.png
粉色：Encoder-Only；绿色：Encoder-Decoder（经典架构）；蓝色：Decoder-Only（当前更主流）

Prompt Engineering
https://www.aneasystone.com/archives/2024/01/prompt-engineering-notes.html
Fine-tuning 微调
[LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
RAG
[Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)

Function call
https://platform.openai.com/docs/guides/gpt/function-calling

MCP
https://modelcontextprotocol.info/docs/introduction/

Agent
https://arxiv.org/abs/2210.03629?utm_source=chatgpt.com
https://x.com/HiTw93/status/2034627967926825175
https://x.com/HiTw93/status/2034627967926825175（https://tw93.fun/2026-03-21/agent.html）
Agent Loop：思考 → 行动 → 观察
Agent 设计模式
https://medium.com/binome/ai-agent-workflow-design-patterns-an-overview-cf9e1f609696
https://mp.weixin.qq.com/s/7CZ6cHWQ-T9bmaWoJFwdwA
Multi-Agent
https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them
Context Engineering
[【Lanchain】Context Engineering](https://blog.langchain.com/context-engineering-for-agents/)（lanchain）
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)（Anthropic）
https://mp.weixin.qq.com/s/KbviOJ6q-K4ik_wzsUs2dw?open_in_browser=true
Agent Skill
https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
https://agentskills.io/home
OpenClaw
openclaw 代码太长了，可以看精简版 nanobot：https://github.com/HKUDS/nanobot
Harness Engineering
https://openai.com/zh-Hans-CN/index/harness-engineering/
分享下 Claude Code 源码
https://github.com/instructkr/claw-code
https://github.com/hesreallyhim/claude-code-fork
https://www.youtube.com/watch?v=DXTS82fJO9A


1. LLM
Transformer 架构的提出奠定了大模型时代基础，使基于注意力机制的生成模型成为主流。
Decoder-Only（仅解码器）的 Transformer 架构变体是当下最为主流的架构。

2. Prompt Engineering
提示词是用来引导模型按照特定意图生成输出的输入指令。主要包含「系统提示词」和「用户提示词」。
提示词工程是通过设计和优化提示词，使大模型更准确、可控地产生所需输出。是一种提升效果但不改变模型智力（参数）的低成本调优手段。

3. Fine-tuning（微调）
微调是在已有模型基础上，用特定数据再训练，让模型更适合某个具体任务或场景。
微调要训练的是模型的参数。LoRA 算法通过只训练少量低秩参数来进行微调，大幅降低了训练成本。

4. RAG（检索增强生成）
先从外部知识库检索相关信息，再结合这些信息一起生成回答，从而提升模型的准确性和知识时效性。

5. Function Calling
Function Calling 是让大模型按约定格式输出调用指令，从而由外部系统真正去执行具体操作的一种机制。
Function Calling 让模型从“只会说话”变为“会调用工具”。

6. MCP（Model Context Protocol）
是一种标准化协议，用来让大模型以统一的方式连接外部工具、数据源和服务，从而获取上下文信息并执行操作。
MCP 最重要的贡献之一是使工具可以跨 AI 应用复用，推动社区生态发展。

7. Agent
Agent 是一种能够基于目标进行“思考-行动-观察”循环、能够自主调用工具来完成复杂任务的智能系统。
Agent 本质上是对人类的模拟。
「提示词 + LLM + Tools」就可以构成一个最简单的 Agent。

8. Multi-Agent
由多个分工协作的 Agent 共同完成任务，通过拆分任务与隔离上下文解决单 Agent 系统难以处理的复杂问题。
需要谨慎使用以避免 Token 消耗量大、协作效率低、系统复杂度过高等问题。

9. Context Engineering
Agent 运行中需要提供给 LLM 的一切相关信息（如对话历史、用户输入、背景知识、工具结果等）都是上下文。
上下文工程关注如何高质量筛选、压缩和组织上下文，从而最大化模型决策与推理能力。

10. Agent Skill
Agent Skills 是一种轻量级的开放格式，用于将一整套 Agent 能力（prompt、工具脚本、知识文件等）
封装为可复用模块，从而实现低门槛分享与复用。
Agent Skill 本质上约等于一个子 Agent。
Agent Skill 特别适合 SOP 的沉淀和复用（离职的同事终将化作温暖的 Skill）。
Agent 会在运行过程中按需激活不同 Skills、按需读取和使用 Skills 文件包里的内容（渐进式披露）。

11. OpenClaw
OpenClaw 是一款开源、高可扩展的AI Agent框架，基于 TypeScript 开发，核心用途是构建可自定义的私人AI助手。创新之一是拓展了 Agent 的交互入口（飞书等）

12. Harness Engineering
Harness Engineering 强调通过构建受控环境，让 Agent 在约束下高效可靠地完成长周期复杂任务。
包含围绕 Agent 构建约束机制、反馈回路、可靠上下文等等一系列工程实践。


## Personal Notes
