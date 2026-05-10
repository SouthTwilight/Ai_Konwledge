# RabbitMQ - Base Concept

Tags: Learn
Characters: 1 - base concept

Classify: Middleware
Expiration date: April 1, 2024

***概述：***
[RabbitMQ](https://www.rabbitmq.com/) 是由 LShift 提供的一个 Advanced Message Queuing Protocol (AMQP：高级消息队列协议) 的开源实现，由 Erlang 写成，具备高性能、健壮以及可伸缩性的特点。

- ***特点：***
    1. **可靠性（Reliability）：**通过持久化、传输确认、发布确认手段进行保证
    2. **灵活的路由（Flexible Routing）：**通过多个 Exchange 绑定路由可以实现复杂路由功能
    3. **消息集群（Clustering）：** 多个 RabbitMQ 服务器可以组成一个集群
    4. **高可用（Highly Available Queues） ：**队列在集群中的机器上进行镜像保证高可用
    5. 多种协议（Multi-protocol）：支持多种消息队列协议，比如 STOMP、MQTT 等
    6. 多语言客户端（Many Clients）: 支持多种所有常用语言，比如 ***Java、.NET、Ruby*** 等
    7. 管理界面（Management UI）：提供易用的用户界面，使用户可以监控和管理消息 Broker
    8. 跟踪机制（Tracing）： 提供消息跟踪机制查询消息异常信息
    9. 插件机制（Plugin System）：提供许多插件，多方面扩展功能，也可以编写自定义功能插件
- ***基本概念：***
    1. Message 消息：由消息头和消息体组成，可选属性routing-key（路由键）、priority（相对于其他消息的优先权）、delivery-mode（指出该消息可能需要持久性存储）等
    2. Publisher 生产者：向交换器**发布消息**的客户端应用程序
    - 3.  Exchange 交换器：接收生产者发送的消息并将这些消息路由给服务器中的队列
        1. **direct 类型:** 消息中的路由键（routing key）如果和 Binding 中的 binding key 一致， 交换器就将消息发到对应的队列中。如果一个队列绑定到交换机要求路由键为“dog”，则只转发 routing key 标记为“dog”的消息，不会转发“dog.puppy”，也不会转发“dog.guard”等等。它是完全匹配、单播的模式
        2. **fanout 类型：**每个发到 fanout 类型交换器的消息都会分到所有绑定的队列上去。fanout 交换器不处理路由键，只是简单的将队列绑定到交换器上，每个发送到交换器的消息都会被转发到与该交换器绑定的所有队列上。fanout 类型转发消息是最快的。
        3. **topic 类型：**topic 交换器通过模式匹配分配消息的路由键属性，将路由键和某个模式进行匹配，此时队列需要绑定到一个模式上。它将路由键和绑定键的字符串切分成单词，这些单词之间用点隔开。它同样也会识别两个通配符：符号“#”和符号“*”。#匹配0个或多个单词，*匹配不多不少一个单词
        4. headers 类型：headers 匹配 AMQP 消息的 header 而不是路由键，此外 headers 交换器和 direct 交换器完全一致，但性能差很多，目前几乎用不到了
    1. Binding 绑定：消息队列和交换器之间的关联关系
    2. Queue 消息队列：消息的容器，保存消息直到发送给消费者
    3. Connection 网络连接：TCP连接
    4. Channel 信道：多路复用连接中的一条独立的双向数据流通道，以复用一条 TCP 连接节省开销
    5. Consumer 消费者：从消息队列中**取得消息**的客户端应用程序
    6. Virtual Host 虚拟主机：一批交换器、消息队列和相关对象
    7. Broker 代理： 表示消息队列服务器实体