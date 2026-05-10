---
title: Linux 又爆 Dirty Frag 漏洞：Ubuntu、Debian、Arch、RHEL、WSL2 全中招
source: https://www.appinn.com/dirty-frag/
source_name: 品玩
author: 青小蛙
date_processed: '2026-05-08'
date_published: '2026-05-08'
tags:
- security
- linux
- vulnerability
relevance: 8
level: l2
hash: 9669f1d95a949018
---
# Linux 又爆 Dirty Frag 漏洞：Ubuntu、Debian、Arch、RHEL、WSL2 全中招

> Source: [品玩](https://www.appinn.com/dirty-frag/) | Author: 青小蛙

## Summary

**TL;DR:** Dirty Frag 漏洞允许本地用户在大多数 Linux 发行版上获取 root 权限，目前无补丁，需禁用特定内核模块缓解。

Dirty Frag 是一个影响自 2017 年以来大多数 Linux 系统的通用本地提权漏洞（LPE），允许普通用户无需特定环境即可获得 root 权限。该漏洞机制与之前的 Copy Fail 类似，利用 Linux 的“零拷贝”机制将只读的 page cache 变为可写目标。与 Copy Fail 不同的是，Dirty Frag 的根源在于 IPSec 相关模块（esp4, esp6）的代码缺陷。在 Ubuntu 等受 AppArmor 保护的系统上，研究人员通过串联 RxRPC 漏洞成功绕过限制实现了提权。由于保密协议被第三方打破，该漏洞在无补丁的情况下被提前公开，涉及 Ubuntu、Debian、RHEL、Arch 及 WSL2 等主流平台。目前唯一的临时缓解方案是禁用并卸载 esp4、esp6 和 rxrpc 这三个网络模块。官方建议管理员立即执行缓解命令，因为漏洞可能已被实际利用。

## Key Points

- 漏洞影响范围极广，涵盖 Ubuntu、Debian、Fedora、RHEL、Arch、OpenSUSE、CentOS Stream 及 WSL2，影响自 2017 年以来的内核版本。
- 利用链结合了两个独立漏洞：IPSec 相关模块（esp4/esp6）的零拷贝缺陷以及 RxRPC 漏洞，后者用于绕过 Ubuntu 的 AppArmor 防护。
- 攻击极其简单，本地用户只需编译并运行一段 C 语言代码即可直接获取 root 权限，不依赖任何特定配置。
- 由于披露流程被破坏，目前暂无 CVE 编号且所有发行版均无官方补丁可用。
- 临时缓解措施为禁用相关模块：通过 modprobe 配置阻止加载，并使用 rmmod 卸载已加载的 esp4、esp6 和 rxrpc 模块。
- 受影响的模块主要用于 IPSec 网络功能，普通服务器、NAS 和开发环境通常不需要，禁用它们对业务影响较小。

## Related

[[Linux Kernel Security]] [[Privilege Escalation]] [[IPSec]] [[Zero-Copy Mechanism]]

## Tags

#security #linux #vulnerability

## 原文内容

还记得前几天的漏洞么：Copy Fail：2017年至今的漏洞，一个脚本获得 Linux root 管理员权限｜CVE-2026-31431
没想到，又来了。
Dirty Frag
这次叫 Dirty Frag，暂时还未获得 CVE 编号。普通用户可以在大多数 Linux 机器上立即获得 root 访问权限，没有可用的补丁，也没有发出警告。
Dirty Frag 的机制与前几天的 Copy Fail 很像，影响了 2017 年以来的大多数 Linux 系统，包括：
- Ubuntu
- Debian 系
- Fedora
- RHEL / AlmaLinux
- Arch
- OpenSUSE
- CentOS Stream
- 甚至 WSL2
消息最早来自 Openwall（Linux 安全邮件列表）：
主题：脏片段（Dirty Frag）：通用 Linux 本地提权漏洞
您好，
这是一份关于“脏片段”（Dirty Frag）的报告，该漏洞为通用型本地权限提升（LPE）漏洞，允许在所有主流Linux发行版上获取root权限。
此漏洞的影响与之前的复制错误（Copy Fail）类似。
由于保密协议现已被打破，目前没有任何针对这些漏洞的补丁或CVE编号。在与linux-distros@…openwall.org维护者协商后，并根据维护者的要求，我现公开这份《脏片段》文档。
与先前的复制错误（Copy Fail）漏洞一样，“脏片段”同样能在所有主流发行版上实现即时root权限提升，它串联了两个独立的漏洞：
- https://git.kernel.org/pub/scm/linux/kernel/git/netdev/net.git/commit/?id=f4c50a4034e62ab75f1d5cdd191dd5f9c77fdff4
- https://lore.kernel.org/all/afKV2zGR6rrelPC7@v4bel/
由于负责任的披露时间表和保密状态已被破坏，目前所有发行版均无可用补丁。
测试漏洞
任何本地用户，只需要运行一段代码，就能直接获得机器的 root 权限。
它不依赖特定环境，什么都不需要，本质上就是一个内核逻辑错误，一行：
git clone https://github.com/V4bel/dirtyfrag.git && cd dirtyfrag && gcc -O0 -Wall -o exp exp.c -lutil && ./exp
临时解决方案
幸运的是，目前的历史解决方案：禁用 esp4、esp6 和 rxrpc 模块即可。
这些模块都和 IPSec 网络功能有关，普通服务器、NAS、开发机通常不会用到。
## 告诉 Linux 不再加载这些模块
printf 'install esp4 /bin/false
install esp6 /bin/false
install rxrpc /bin/false
' > /etc/modprobe.d/dirtyfrag.conf
## 卸载已经加载的模块
rmmod esp4 esp6 rxrpc
## 检查是否还在
lsmod | grep -E 'esp4|esp6|rxrpc'
技术原理
与 Copy Fail 类似，Dirty Frag 也利用了 Linux 的“零拷贝”机制，把原本只读的 page cache 变成了可写目标。
不同的是，Copy Fail 出问题的是加密优化代码，而 Dirty Frag 出问题的是 IPSec 相关模块。
Linux 在 2017 年加入的一段网络相关代码里埋下了这个漏洞，并一路影响到了今天的大多数发行版。
Ubuntu 因为有 AppArmor 防护，单靠第一个漏洞还不够，所以研究人员又串联了另一个 RxRPC 漏洞，最终实现 root 提权。
措手不及
Dirty Frag 之所以让很多管理员来不及反应，是因为漏洞虽然早在 4 月 30 日就已经报告给 Linux 内核团队，但有第三方提前打破了保密披露流程。
官方没有说明具体原因，不过外界猜测，这可能意味着漏洞已经开始被实际利用，因此不得不提前公开。
原文：https://www.appinn.com/dirtyfrag/
怎么说呢，麻了，记得更新系统。
……哦不对，现在还没补丁 😭


## Personal Notes
