# RabbitMQ - Spring Boot Message

Tags: Learn
Characters: 2 - Spring Boot Message
Classify: Middleware
Expiration date: April 2, 2024

### **Spring-AMQP**

**概述：** Spring 生态中，提供了 [Spring-AMQP](https://spring.io/projects/spring-amqp) 项目，让我们更简便的使用 AMQP 。它提供了一个“模板”作为发送消息的高级抽象，并通过“侦听器容器”为消息驱动的 POJO 提供支持。

- ***定义：***
    - [spring-amqp][https://mvnrepository.com/artifact/org.springframework.amqp/spring-amqp] 是 AMQP 的基础抽象。
    - [spring-rabbit][https://mvnrepository.com/artifact/org.springframework.amqp/spring-rabbit] 是基于 RabbitMQ 对 AMQP 的具体实现
- ***功能特性：***
    - 监听器容器：异步处理接收到的消息
    - RabbitTemplate：发送和接收消息
    - RabbitAdmin：自动创建队列，交换器，绑定器

### **Spring Boot 引入通用配置**

- ***依赖引入：***
    
    ```xml
    <dependencies>
    	<!-- 实现对 RabbitMQ 的自动化配置 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-amqp</artifactId>
        </dependency>
        
        ......
        
    </dependencies>
    ```
    
- ***应用配置：***
    
    ```yaml
    spring:
      # RabbitMQ 配置项，对应 RabbitProperties 配置类
      rabbitmq:
        host: 127.0.0.1 # RabbitMQ 服务的地址
        port: 5672 # RabbitMQ 服务的端口
        username: guest # RabbitMQ 服务的账号
        password: guest # RabbitMQ 服务的密码
    ```
#📌 `spring.rabbitmq` 配置项，设置 RabbitMQ 的配置，对应 [RabbitProperties][https://github.com/spring-projects/spring-boot/blob/master/spring-boot-project/spring-boot-autoconfigure/src/main/java/org/springframework/boot/autoconfigure/amqp/RabbitProperties.java] 配置类
#💡 Spring Boot 提供的 [RabbitAutoConfiguration](https://github.com/spring-projects/spring-boot/blob/master/spring-boot-project/spring-boot-autoconfigure/src/main/java/org/springframework/boot/autoconfigure/amqp/RabbitAutoConfiguration.java) 自动化配置类，实现 RabbitMQ 的自动配置，创建相应的 Producer 和 Consumer

## Spring Boot 消息路由

- **绑定键（binding key）与路由键（routing key）详解**
    
    > 在RabbitMQ中，routing key是一个消息属性，它是一个字符串，用于确定如何路由消息。在消息队列中，routing key用于解决消息的路由问题，它可以是任何字符串，但在实际应用中，我们通常使用有意义的标识符。
    > 
    > 
    > binding key是在交换机类型为 direct 或者 topic 的时候，消息队列如何绑定到交换机的一个规则。在绑定（exchange）交换机和（queue）队列的时候，需要指定一个binding key。
    > 
    > 在direct类型的交换机中，消息队列只有当routing key完全匹配binding key，消息才会被路由到绑定的队列。
    > 
    > 在topic类型的交换机中，binding key可以使用通配符，"*"匹配一个单词，"#"匹配0个或多个单词。当routing key与binding key中至少有一个通配符匹配时，消息会被路由到绑定的队列。
    > 
### **Direct Exchange**

规则：将消息路由到**绑定键（binding key）与路由键（routing key）完全匹配**的消息队列（Queue）

#📌 **绑定键（binding key）：消息交换机（Exchange）绑定消息队列的的消息路由键（routing key）**
#📌 **路由键（routing key）：交换机分发消息到消息队列的路由**

- ***组件：***
    - 消息类：
        #📌 **需要实现 Java Serializable 序列化接口！**RabbitTemplate 默认使用 Java 自带的序列化方式，进行序列化 POJO 类型的消息
        ```java
        public class DirectMessage implements Serializable {
        		// 消息队列名称
            public static final String QUEUE = "DIRECT_QUEUE";
        		// 消息交换机名称
            public static final String EXCHANGE = "DIRECT_EXCHANGE";
        		// 消息绑定路由键（消息队列与消息交换机进行绑定）
            public static final String ROUTING_KEY = "DIRECT_ROUTING_KEY";
         
        		······ // 具体消息类实例功能方法和属性   
        }
        ```
        
    - ***交换机配置类：***
        #📌 添加相关的 Exchange、Queue、Binding 的配置。完成 Exchange、Queue、Binding 三个 Bean创建后 ，后续 [RabbitAdmin](https://github.com/spring-projects/spring-amqp/blob/master/spring-rabbit/src/main/java/org/springframework/amqp/rabbit/core/RabbitAdmin.java) 会自动创建交换器、队列、绑定器。

        ```java
        @Configuration
        public class RabbitConfig {
            public static class DirectExchangeConfiguration {
        
                // 创建 Queue
                @Bean
                public Queue directQueue() {
                    return new Queue(DirectMessage.QUEUE, // Queue 名字
                            true, // durable: 是否持久化
                            false, // exclusive: 是否排它
                            false); // autoDelete: 是否自动删除
                }
        
                // 创建 Direct Exchange
                @Bean
                public DirectExchange directExchange() {
                    return new DirectExchange(DirectMessage.EXCHANGE,
                            true,  // durable: 是否持久化
                            false);  // exclusive: 是否排它
                }
        
                // 创建绑定关系，绑定键（binding key）与路由键（routing key）完全匹配
                // Exchange：DirectMessage.EXCHANGE
                // ROUTING key：DirectMessage.ROUTING_KEY
                // Queue：DirectMessage.QUEUE
                @Bean
                public Binding directBinding() {
                    return BindingBuilder.bind(directQueue())
        				            .to(directExchange())
        				            .with(DirectMessage.ROUTING_KEY);
                }
        
            }
        }
        ```
        
    - 生产者类：
        #📌 使用 Spring-AMQP 封装提供的 RabbitTemplate ，实现发送消息的功能；无需传入路由键（routing key），Direct模式默认路由键为绑定键，所以调用方法 convertAndSend 传入的是消息实例类的默认路由键（DirectMessage.ROUTING_KEY）
        ```java
        @Component
        public class DirectProducer {
        
            @Autowired
            private RabbitTemplate rabbitTemplate;
        
        		// 同步消息发送方法
            public void syncSend(String info) {
                // 创建 DirectMessage 消息
                DirectMessage message = new DirectMessage();
                message.setMessage(info);
                // RabbitTemplate 的同步发送消息
                rabbitTemplate.convertAndSend(DirectMessage.EXCHANGE, 
        					        DirectMessage.ROUTING_KEY, message);
            }
            
            // 通过 Spring @Async 注解，异步消息发送方法
            @Async
            public ListenableFuture<Void> asyncSend(String info) {
                try {
                    // 发送消息
                    this.syncSend(info);
                    // 返回成功的 Future
                    return AsyncResult.forValue(null);
                } catch (Throwable ex) {
                    // 返回异常的 Future
                    return AsyncResult.forExecutionException(ex);
                }
            }
        }
        ```
        #📌 ==***存在 [AsyncRabbitTemplate](https://github.com/spring-projects/spring-amqp/blob/master/spring-rabbit/src/main/java/org/springframework/amqp/rabbit/AsyncRabbitTemplate.java) 类，提供异步的 RabbitMQ 操作***==
    - 消费者类：
        
        ```java
        @Component
        @RabbitListener(queues = DirectMessage.QUEUE)
        public class DirectConsumer {
        
            private Logger logger = LoggerFactory.getLogger(getClass());
        
            @RabbitHandler
            public void onMessage(DirectMessage message) {
                logger.info("[onMessage][线程编号:{} 消息内容：{}]", 
        		        Thread.currentThread().getId(), message);
        		    ...... // 消费消息
            }
        }
        ```
        #📌 类添加 [@RabbitListener](https://github.com/spring-projects/spring-amqp/blob/master/spring-rabbit/src/main/java/org/springframework/amqp/rabbit/annotation/RabbitListener.java) 注解，声明消费的队列是 `"DIRECT_QUEUE"`
        #📌 方法上，添加 [@RabbitHandler](https://github.com/spring-projects/spring-amqp/blob/master/spring-rabbit/src/main/java/org/springframework/amqp/rabbit/annotation/RabbitHandler.java)注解，申明为处理消息的方法。方法入参为消息类型（消息实例类）。
## **Topic Exchange**

- 规则：与 Direct 类型的 Exchange 相似，但不同的是有如下约定
    1. **路由键（routing key）**为一个句点号 `"."` 分隔的字符串。我们将被句点号`"."`分隔开的每一段独立的字符串称为一个单词
    2. **绑定键（binding key）**与**路由键（routing key）**一样也是句点号 `"."` 分隔的字符串
    3. **绑定键（binding key）**中可以存在两种特殊字符 `"*"` 与 `"#"`，用于做模糊匹配。其中 `"*"` 用于匹配一个单词，`"#"` 用于匹配多个单词（可以是零个）
- 示例：
	    ![[Topic Exchange.png]]    
    - `routingKey="quick.orange.rabbit"` 的消息会同时路由到 Q1 与 Q2 。
    - `routingKey="lazy.orange.fox"` 的消息会路由到 Q1 。
    - `routingKey="lazy.brown.fox"` 的消息会路由到 Q2 。
    - `routingKey="lazy.pink.rabbit"` 的消息会路由到Q2（只会投递给 Q2 一次，虽然这个 routingKey 与 Q2 的两个 bindingKey 都匹配）。
    - `routingKey="quick.brown.fox"`、`routingKey="orange"`、`routingKey="quick.orange.male.rabbit"` 的**消息将会被丢弃，因为它们没有匹配任何 bindingKey** 。
- ***组件：***
    - ***消息类：***
        
        ```java
        public class TopicMessage implements Serializable {
            public static final String QUEUE = "TOPIC_QUEUE";
            public static final String EXCHANGE = "TOPIC_EXCHANGE";
            public static final String ROUTING_KEY = "#.topic.demo";
        
        		······ // 具体消息类实例功能方法和属性  
        }
        ```
        
    - ***交换机配置类：***

        #📌 ==***注意本次创建的 Exchange 类型为 [TopicExchange](https://github.com/spring-projects/spring-amqp/blob/master/spring-amqp/src/main/java/org/springframework/amqp/core/TopicExchange.java)***==
        
        ```java
        @Configuration
        public class RabbitConfig {
            public static class TopicExchangeConfiguration {
        
                // 创建 Queue
                @Bean
                public Queue topicQueue() {
                    return new Queue(TopicMessage.QUEUE, // Queue 名字
                            true, // durable: 是否持久化
                            false, // exclusive: 是否排它
                            false); // autoDelete: 是否自动删除
                }
        
                // 创建 Topic Exchange
                @Bean
                public TopicExchange topicExchange() {
                    return new TopicExchange(TopicMessage.EXCHANGE,
                            true,  // durable: 是否持久化
                            false);  // exclusive: 是否排它
                }
        
                // 创建 Binding
                // Exchange：TopicMessage.EXCHANGE
                // ROUTING key：TopicMessage.ROUTING_KEY
                // Queue：TopicMessage.QUEUE
                @Bean
                public Binding topicBinding() {
                    return BindingBuilder.bind(topicQueue())
        				            .to(topicExchange())
        				            .with(TopicMessage.ROUTING_KEY);
                }
            }
        }
        ```
        
    - 生产者类：
        #📌 ==***注意新增传入参数路由键 Routing Key 便于指定分发 Exchange。路由键 Routing Key 将与创建的绑定键 Binding Key 进行匹配分发消息。***==
        ```java
        @Component
        public class TopicProducer {
        
            @Autowired
            private RabbitTemplate rabbitTemplate;
        
            public void syncSend(String info, String routingKey) {
                // 创建 TopicMessage 消息
                TopicMessage message = new TopicMessage();
                message.setMessage(info);
                // 同步发送消息
                rabbitTemplate.convertAndSend(TopicMessage.EXCHANGE, routingKey, message);
            }
        
        }
        ```
        
    - 消费者类
        
        ```java
        @Component
        @RabbitListener(queues = TopicMessage.QUEUE)
        public class TopicConsumer {
        
            private Logger logger = LoggerFactory.getLogger(getClass());
        
            @RabbitHandler
            public void onMessage(TopicMessage message) {
                logger.info("[onMessage][线程编号:{} 消息内容：{}]", 
        		        Thread.currentThread().getId(), message);
        		    ...... // 消费消息
            }
        }
        ```
        

### **Fanout Exchange**