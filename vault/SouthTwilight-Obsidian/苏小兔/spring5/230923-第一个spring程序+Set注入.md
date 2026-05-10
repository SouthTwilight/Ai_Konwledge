+ 开发步骤
```
1. 创建类型 
2. 配置⽂件的配置 applicationContext.xml 
<bean id="person" class="com.baizhiedu.basic.Person"/> 
3. 通过⼯⼚类，获得对象 ApplicationContext 
									|- ClassPathXmlApplicationContext ApplicationContext ctx = new ClassPathXmlApplicationContext("/applicationContext.xml"); Person person = (Person)ctx.getBean("person");
```
> 代码示例

```java
public class User {  
    private String name;  
    private Integer age;  
  
    public String getName() {  
        return name;  
    }  
  
    public void setName(String name) {  
        this.name = name;  
    }  
  
    public Integer getAge() {  
        return age;  
    }  
  
    public void setAge(Integer age) {  
        this.age = age;  
    }  
}
```

```xml
<?xml version="1.0" encoding="UTF-8"?>  
<beans xmlns="http://www.springframework.org/schema/beans"  
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  
       xsi:schemaLocation="http://www.springframework.org/schema/beans http://www.springframework.org/schema/beans/spring-beans.xsd">  
  
    <!--    spring的配置文件使用工厂 ClassPathXmlApplicationContext 来创建对应的对象-->  
    <bean id="user" class="com.sunzhen.User"/>  
</beans>
```

```java
public class TestSpring1 {  
  
    @Test  
    public void test1(){  
        // 1 获取spring工厂  
        ApplicationContext context = new ClassPathXmlApplicationContext("applicationContext.xml");  
        // 2 通过工厂类获得对象  
        User user = (User)context.getBean("user");  
  
        System.out.println(user);  
    }  
}
```


> 工厂类的相关方法

```java
		//当前Spring的配置文件中 只能有一个<bean class是Person类型

        Person person = ctx.getBean(Person.class);

        System.out.println("person = " + person);


  

        //获取的是 Spring工厂配置文件中所有bean标签的id值  person person1

        String[] beanDefinitionNames = ctx.getBeanDefinitionNames();

        for (String beanDefinitionName : beanDefinitionNames) {

            System.out.println("beanDefinitionName = " + beanDefinitionName);

        }

  

        //根据类型获得Spring配置文件中对应的id值

        String[] beanNamesForType = ctx.getBeanNamesForType(Person.class);

        for (String id : beanNamesForType) {

            System.out.println("id = " + id);

        }

  

        //用于判断是否存在指定id值得bean,不能判断name值

        if (ctx.containsBeanDefinition("person")) {

            System.out.println("true = " + true);

        }else{

            System.out.println("false = " + false);

        }

  
  

        //用于判断是否存在指定id值得bean,也可以判断name值

        if (ctx.containsBean("p")) {

            System.out.println("true = " + true);

        }else{

            System.out.println("false = " + false);

        }
```


+ 配置文件中需要注意的细节
```xml
1. 只配置class属性 <bean class="com.baizhiedu.basic.Person"/> 
a) 上述这种配置 有没有id值 spring会按照特定规则自己生存一个 -> com.baizhiedu.basic.Person#0 
b) 应⽤场景： 如果这个bean只需要使⽤⼀次，那么就可以省略id值 
	如果这个bean会使⽤多次，或者被其他bean引⽤则需要设置id值
```
```xml
2. name属性 
作⽤：⽤于在Spring的配置⽂件中，为bean对象定义别名(⼩名) 
相同： 
	1. ctx.getBean("id|name")-->object 
	2. <bean id="" class="" 
	等效
	<bean name="" class="" 
区别： 
	1. 别名可以定义多个,但是id属性只能有⼀个值 
	2. XML的id属性的值，命名要求：必须以字⺟开头，字⺟ 数字 下划线 连字符 不能以特殊字符开头 /person 
	3. name属性的值，命名没有要求 /person 
	4. name属性会应⽤在特殊命名的场景下：/person 比如在使用(spring+struts1)开发时
	5. XML发展到了今天：ID属性的限制，不存在 /person 已经可以使用斜杠开始了
```
```java
// 3. 代码  containsBeanDefinition 和 containsBean 的区别，主要是id和name的判别
//⽤于判断是否存在指定id值的bean,不能判断name值 
	if (ctx.containsBeanDefinition("person")) { 
		System.out.println("true = " + true); 
	}
	else{ 
		System.out.println("false = " + false); 
	} 
//⽤于判断是否存在指定id值的bean,也可以判断name值 
	if (ctx.containsBean("p")) { 
		System.out.println("true = " + true); 
	}else{ 
		System.out.println("false = " + false); 
	}
```


![[Pasted image 20230923203300.png]]
> 底层通过读取spring的xml配置文件，使用反射创建对象，会调用对象自己的构造方法（无参构造）


+ 思考
```
问题：未来在开发过程中，是不是所有的对象，都会交给Spring⼯⼚来创建呢？ 
回答：理论上 是的，但是有特例 ：实体对象(entity)是不会交给Spring创建，它是由持久层 框架进⾏创建。
```


 ### spring和日志框架整合
> Spring与⽇志框架进⾏整合，⽇志框架就可以在控制台中，输出Spring框架运⾏过程中的⼀些 重要的信息。 好处：便于了解Spring框架的运⾏过程，利于程序的调试

如何整合？
```
默认 
	Spring1.2.3早期都是于commons-logging.jar 
	Spring5.x默认整合的⽇志框架 logback log4j2 
Spring5.x整合log4j 
1. 引⼊log4j jar包 
2. 引⼊log4.properties配置⽂件
```
```xml
	<dependency> 
		<groupId>org.slf4j</groupId> 
		<artifactId>slf4j-log4j12</artifactId> 
		<version>1.7.25</version> 
	</dependency> 
	<dependency> 
		<groupId>log4j</groupId> 
		<artifactId>log4j</artifactId> 
		<version>1.2.17</version> 
	</dependency>
```
```properties
# resources⽂件夹根⽬录下⽂件夹根⽬录下  log4j.properties
### 配置根配置根 
log4j.rootLogger = debug,console 
### ⽇志输出到控制台显示⽇志输出到控制台显示 
log4j.appender.console=org.apache.log4j.ConsoleAppender 
log4j.appender.console.Target=System.out 
log4j.appender.console.layout=org.apache.log4j.PatternLayout 
log4j.appender.console.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
```


### 注入
+ 什么是注⼊
```
通过Spring⼯⼚及配置⽂件，为所创建对象的成员变量赋值
```
+ 为什么需要注⼊?
通过编码的⽅式，为成员变量进⾏赋值，存在耦合
![[Pasted image 20230923210031.png]]
+ 如何进⾏注⼊[开发步骤]
1、类的成员变量提供set get⽅法
2、配置spring的配置⽂件
![[Pasted image 20230923210130.png]]
+ 注⼊好处
```
	解耦合
```

![[Pasted image 20230923210936.png]]


### Set注入详解
```
针对于不同类型的成员变量，在<property>标签，需要嵌套其他标签 
<property> 
xxxxx 
</property>
```

![[Pasted image 20230923211854.png]]
![[Pasted image 20230923214710.png]]
+ 1、String+8种基本类型
```xml
<value>suns</value>
```
+  2、数组
```xml
<list>  
    <value>1@qq.com</value>  
    <value>2@qq.com</value>  
    <value>3@qq.com</value>  
</list>
```
+ 3、 set集合
> set内部的标签需要根据泛型选择，比如
```xml
<ref bean=""/>
```
```xml
<set>  
    <value>13412341234</value>  
    <value>13512341234</value>  
    <value>13612341234</value>  
</set>
```
+ 4、list集合
> 内部的标签需要根据泛型选择
```xml
<property name="address">  
    <list>  
        <value>chengdu</value>  
        <value>xian</value>  
        <value>hebei</value>  
    </list>  
</property>
```
+ 5、map集合
> 注意： map -- entry -- key有特定的标签
> 									 值根据对应类型选择对应类型的标签
```xml
<property name="qqs">  
    <map>  
        <entry>  
            <key><value>key1</value></key>  
            <value>value1</value>  
        </entry>  
        <entry>  
            <key><value>key2</value></key>  
            <value>value2</value>  
        </entry>  
    </map>  
</property>
```
+ 6、Properties
> Properties类型 特殊的Map key=String value=String

```xml
<property name="properties">  
    <props>  
        <prop key="key1">value1</prop>  
        <prop key="key2">value2</prop>  
    </props>  
</property>
```
+ 7、复杂的JDK类型 (Date)
> 需要程序员⾃定义类型转换器，处理。


+ 8、用户自定义类型
![[Pasted image 20230923215554.png]]
![[Pasted image 20230923215622.png]]
+ 第二种方式
![[Pasted image 20230923215708.png]]
> 把公用的对象，在配置文件中单独创建，以后每个需要的地方使用ref进行引用即可

+ set注入的简化写法
![[Pasted image 20230923220805.png]]
![[Pasted image 20230923221100.png]]
