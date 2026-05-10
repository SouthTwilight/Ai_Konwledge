1. 软件版本
```java
1. JDK1.8+ 
2. Maven3.5+ 
3. IDEA2018+ 
4. SpringFramework 5.1.4
```
2. 环境搭建
+ Spring的jar包
```xml
#设置pom依赖 
<!-- https://mvnrepository.com/artifact/org.springframework/spring- context --> <dependency> 
	<groupId>org.springframework</groupId> 
	<artifactId>spring-context</artifactId> 
	<version>5.1.4.RELEASE</version> 
</dependency>
```
+ Spring的配置⽂件
```
1. 配置⽂件的放置位置：任意位置 没有硬性要求 
2. 配置⽂件的命名 ：没有硬性要求 建议：applicationContext.xml 
3. 思考：⽇后应⽤Spring框架时，需要进⾏配置⽂件路径的设置。
```
![[Pasted image 20230922143106.png]]





### spring的核心API
+ ApplicationContext
```
作⽤：Spring提供的ApplicationContext这个⼯⼚，⽤于对象的创建 
好处：解耦合
```
 + ApplicationContext接⼝类型
```
接⼝：屏蔽实现的差异 
⾮web环境 ： ClassPathXmlApplicationContext (main junit) 
web环境 ： XmlWebApplicationContext
```
![[Pasted image 20230922144418.png]]
+ 重量级资源
```
ApplicationContext⼯⼚的对象占⽤⼤量内存。 
不会频繁的创建对象 ： ⼀个应⽤只会创建⼀个⼯⼚对象。 
ApplicationContext⼯⼚：⼀定是线程安全的(多线程并发访问)
```
