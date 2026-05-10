##### **微服务运行流程**

> 1. 服务提供方正常启动后，通过**服务发现客户端**上报自身服务接口给服务发现中心
> 2. 服务发现中心将相应服务注册到该中心内**服务注册表**上
> 3. **服务发现客户端**定期从服务发现客户端同步服务注册表
> 4. 服务消费方从服务发现中心获取服务注册表并定位对应服务以获取服务

##### 各服务发现中心异同

|对比项目|Nacos|Eureka|Consul|Zookeeper|
|---|---|---|---|---|
|一致性协议|支持AP和CP模型|AP模型|CP模型|CP模型|
|访问协议|HTTP/DNS|HTTP|HTTP/DNS|TCP|
|多数据中心|支持|支持|支持|不支持|
|跨注册中心同步|支持|不支持|支持|不支持|
|SpringCloud集成|支持|支持|支持|不支持|
|Dubbo集成|支持|不支持|不支持|支持|
|k8s集成|支持|不支持|支持|不支持|

##### **Nacos 数据源配置(** 单机 **)**

- 单机模式下运行 Nacos 需配置数据源，默认数据库名 nacos_config 。
- 使用 nacos 软件包中 conf 路径下 nacos-mysql 生成 mysql 的 nacos_config 配置数据库信息
- 编辑 conf路径下 application 属性文件，增加 nacos 服务注册服务中心对 mysql 数据源配置

```yaml
spring.datasource.platform=mysql

db.num=1
db.url.0=jdbc:mysql://11.162.196.16:3306/nacos_config?characterEncoding=utf8&connectTimeout=1000&socketTimeout=3000&autoReconnect=true
db.user=nacos_config_database_username
db.password=nacos_config_database_password
```

##### #📌 Restful 模式
###### （应用）**服务注册/发现配置**

```yaml
spring:
	application:
		name: nacos_provider_name/nacos_consumer_name
	cloud:
		nacos:
			discovery:
				server‐addr: ip_address:port
```

###### 调用过程
> 1. 通过服务注册提供的服务注册名 nacos_provider_name 在服务注册中心获取服务接口
> 2. 使用nacos集成的负载均衡工具类(Ribbon)选定真正执行服务的微服务实例
> 3. 通过从服务注册中心获取的服务实例信息获取对应的ip地址并执行调用
```java
ServiceInstance serviceInstance = loadBalancerClient.choose(nacos_provider_name);
URI uri = serviceInstance.getUri();
String providerResult = restTemplate.getForObject(uri+"/service",String.class);
```

##### #📌 Dubbo 模式

###### **Dubbo 粗解**
- Dubbo 是开源的轻量级 RPC( Remote Procedure Call/远程过程调用 ) 框架
- RPC调用过程
    1. 客户端通过函数ID查找到服务端函数
    2. 客户端将传入参数转换成字节流，通过序列化与反序列化与服务器进行参数/结果传递
- Rest(ful)与RPC
    - REST常以业务为导向，格式简单，可使用浏览器扩展/传输，支持请求/响应方式的通信；无需中间代理，简化系统架构。但只支持请求/响应单一通信方式，客户端需要知道服务实例位置，难以单个请求获取多个资源。
    - RPC框架一般使用长链接，减少网络开销；存在注册中心，监控管理发布/下线接口/动态扩展丰富，对调用透明，协议私密安全性较高；协议简单内容小效率高，服务化架构/治理。但完善的RPC框架开发难度大，调用成功率受限于网络，调用远程方法原理难度高。
    - Restful 模式常应用于应用层对前端接口服务；Dubbo 模式常应用于微服务层对应用层接口。

###### **Dubbo 使用**
> 1. 服务提供方创建服务接口/接口实现类( 接口单独成模块，需要时做jar包以maven引入 )
> 2. 服务实现类注解dubbo提供的@Service 注解，作为dubbo模式微服务处理类
> 3. 服务消费方使用@Reference 注解获取本地调用远程服务的代理对象(名同微服务处理类)，并通过maven引入对应jar包
> 4. 通过代理对象直接像使用本地方法一般使用微服务方法

###### **Dubbo配置**
- 服务端配置
    ```yaml
    dubbo:
    	scan: #基准扫描包
    		base‐packages: service_base_package_route
    	protocol: # dubbo协议
    		name: dubbo # 协议名称(可选配置:dubbo rmi hessian webservice)
    		port: service_prot # 协议端口，通常为自定义端口
    	registry:
    		address: nacos://nacos_ip_address:nacos_prot # dubbo注册到nacos启动地址
    	application:
    		qos‐enable: false
    	consumer:
    		check: false
    ```


##### **Nacos 服务发现数据模型**
- 命名空间
    - 用于不同环境的隔离，如开发/测试/生产环境的资源/配置/服务的隔离。
    - nacos 使用 public 命名空间作为默认命名空间
    - nacos 使用 DEFAULT 作为命名空间下默认默认分组/集群( cluster-name)

##### **Nacos配置管理**
- _理解程序的配置_
    1. 配置是独立于程序的只读变量：程序不应该改变配置，只需要通过配置改变自己
    2. 配置伴随应用全生命周期：应用启动时读取配置初始化，运行时由配置调整行为
    3. 配置有多种加载方式：诸如配置文件、环境变量、启动参数、基于数据库等
    4. 配置需要治理：不同环境/集群需要不同配置
**配置中心：** 将配置从各应用中剥离，对配置进行统一管理，应用不需要自己管理配置
- **获取配置配置内容**
    1. 添加获取配置依赖
	    ```xml
	    <dependency>
	    	<groupId>com.alibaba.cloud</groupId>
	    	<artifactId>spring‐cloud‐starter‐alibaba‐nacos‐config</artifactId>
	    </dependency>
	    ```
    2. 在 bootstrap.yml 添加配置( 此处引入 config-file-name.yaml 文件)
	    ```yaml
	    spring:
	    	application:
	    		name: config-file-name # 应用/配置文件名，主配置文件优先级最高，不会被覆盖
	    	cloud:
	    		nacos:
	    			config:
	    				server‐addr: nacos_ip:nacos_prot # 配置中心地址
	    				file‐extension: yaml # 配置文件格式
	    				namespace: a1f8e863‐3117‐48c4‐9dd3‐e9ddc2af90a8 # 命名空间ID
	    				group: GROUP_NAME
	    				ext‐config[0]: # 基于Data Id的扩展配置会相互覆盖同名配置信息
	    					data‐id: ext‐config‐common01.yaml # 此处必须携带文件扩展名
	    					group: COMMON_GROUP # 文件分组，未明确时为 DEFAULT_GROUP
	    					refresh: true # 开启动态配置刷新
	    				ext‐config[1]: # 组值越大，优先级越高
	    					data‐id: ext‐config‐common02.yaml
	    					group: COMMON_GROUP
	    					refresh: true
	    ```
    #📌 **注意：** 使用时需在bootstrap.yml中配置，bootstrap.yml加载优先级最高
    3. 实现配置的动态更新( 默认开启 )
        配置 spring.cloud.nacos.config.refresh.enabled=true/false 开启/关闭动态刷新
	    ```java
	    @Autowired // 注入配置文件上下文
	    private ConfigurableApplicationContext applicationContext;
    
	    public String getCommonNameConfig(){
	    	// 获取 common.name 配置的值
	    	return applicationContext.getEnvironment().getProperty("[common.name](<http://common.name/>)");
	    }
	    ```