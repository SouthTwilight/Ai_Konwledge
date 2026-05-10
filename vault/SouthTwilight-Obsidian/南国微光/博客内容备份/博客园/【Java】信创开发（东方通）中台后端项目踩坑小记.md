在万事国产化以备世界风云突变之日，我们做软件开发的也不可避免的需要完成一部分信创项目，通常 Web 项目国产化部署的首要选择都是东方通 Web 容器。此次中台项目信创适配过程中踩坑无数，唯独这个坑让我印象深刻念念不忘，接下来就请诸君与我共同复盘一下。

背景：中台项目源于 ruoyi 开源框架，根据公司需要做了一些定制化改造增强。
###### 1. 首先，按照惯例进行 war 包打包。
　　a. 去除项目内置 tomcat依赖
```xml
	<dependency>
	    <groupId>org.springframework.boot</groupId>
	    <artifactId>spring-boot-starter-web</artifactId>
	    <exclusions>
	        <exclusion>
	            <groupId>org.springframework.boot</groupId>
	            <artifactId>spring-boot-starter-tomcat</artifactId>
	        </exclusion>
	    </exclusions>
	</dependency>
```
　　b. 重写启动类，继承 `SpringBootServletInitializer` 类，重写 `configure` 方法，Web 容器否则无法检测到启动类
```java
public class MainServletInitializer   extends SpringBootServletInitializer
{
    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder application)
    {
        return application.sources(MainApplication.  class );
    }
}
```
###### 2. 部署项目至东方通容器，具体部署步骤可参见此[博客](https://www.cnblogs.com/niway/p/16714894.html) 

a.登录东方通中台管理页面
b.创建虚拟主机与 Http 通道，并相互绑定
c.部署应用，并绑定虚拟主机
到此为止，基本的部署已经完成。按理说现在可以访问登录页面资源了。但访问页面却出现了一个意料之外的错误。
![[../../../attachments/中台页面访问错误.png]]
栈溢出！！！！！！此刻，我有了一种十分不妙的预感。经测试，是获取不到 MVC 视图静态资源等，而接口服务却可以正常提供（登录接口可以使用 Postman 等方式登录，却不能打开登录页面）
查询日志如下：
```java
org.springframework.web.util.NestedServletException: Handler dispatch failed; nested exception is java.lang.StackOverflowError
```
![[../../../attachments/东方通堆栈信息错误1.png]]
![[../../../attachments/东方通堆栈信息错误2.png]]
可见项目是使用 hutool 工具类出现错误，此时我在 tomcat 上部署相同 war 包确认是否打包问题，测试后发现 tomcat 未复现该问题。那么可以确定该问题为东方通 Web 容器与 tomcat 不兼容部分导致的问题。
![[../../../attachments/tomcat堆栈错误信息1.png]]
经过艰难的排查，最终确认访问并没有进入相应的 Controller 控制器。但是 servlet 容器执行 doDispatch 时获取的请求对象（ShiroHttpServletRequest，SysLoginController）都与 tomcat 容器与本地启动时一致。在此处我陷入深深的怀疑与深思，我确定肯定与项目使用 hutool 工具类有关，于是我怀着不必要的希望去查询 hutool 开源社群 isuee 。找到如下问题：
[JSONBeanParser在遇到List时没有被正确递归](https://gitee.com/dromara/hutool/issues/I7M2GZ)
此时我已经基本确认，我遇到的问题就是这项，回归项目，在切面中定位到此处代码：
```java
String requestParameter= JSONUtil.toJsonStr(proceedingJoinPoint.getArgs());
```
该处代码是打印接口调用日志的切面代码，需要将切点参数（接口请求参数）转换为可以打印的 String 字符串，使用了 hutool JSON 工具类中 toJsonStr 方法。但该方法在东方通 Web 容器 7.0.4.9 版本会发生错误，而 tomcat 9.0版本以上则不会出现此类错误，其余版本因未进行测试故不确定：不能转换 HttpServletRequest 对象。
因为不能随意变更已上线系统的引用软件版本，故修改代码为：
```java
   String requestParameter;
   Object[] args = proceedingJoinPoint.getArgs();
   if (args.length>=2 && args[0] instanceof HttpServletRequest && args[1] instanceof HttpServletResponse){
       requestParameter = ((HttpServletRequest) args[0]).getRequestURI();
   }  else {
       requestParameter= JSONUtil.toJsonStr(args);
   }
```
至此，中台项目成功启动，登录页面访问成功且能正常登录：
![[../../../attachments/中台成功访问信息.png]]