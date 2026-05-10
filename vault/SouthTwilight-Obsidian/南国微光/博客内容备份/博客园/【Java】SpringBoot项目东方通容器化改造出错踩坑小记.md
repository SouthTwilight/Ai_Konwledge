由于信创业务需要，需要将直接部署微服务程序进行容器化改造并部署至东方通Web容器（东方通Web容器基于Tomcat 9，两者基本可以兼容，但也存在不兼容的部分。我曾遇到过一个不兼容问题，详情可见我这篇东方通踩坑博客： [【Java】信创开发（东方通）中台后端项目踩坑小记](obsidian://open?vault=Team&file=%E5%8D%97%E5%9B%BD%E5%BE%AE%E5%85%89%2F%E5%8D%9A%E5%AE%A2%E5%86%85%E5%AE%B9%E5%A4%87%E4%BB%BD%2F%E5%8D%9A%E5%AE%A2%E5%9B%AD%2F%E3%80%90Java%E3%80%91%E4%BF%A1%E5%88%9B%E5%BC%80%E5%8F%91%EF%BC%88%E4%B8%9C%E6%96%B9%E9%80%9A%EF%BC%89%E4%B8%AD%E5%8F%B0%E5%90%8E%E7%AB%AF%E9%A1%B9%E7%9B%AE%E8%B8%A9%E5%9D%91%E5%B0%8F%E8%AE%B0) ）。

言归正传，按照惯例我先说一下背景：有部分微服务需要做信创改造，为统一管理需要将本地通过脚本启动的微服务打为 **war** 包并部署至东方通容器。大部分微服务都非常顺利的完成了这个步骤，但使用了最新版本自用框架的微服务却在部署东方通时报错。

1.去除项目内置 tomcat依赖
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
2. 重写启动类，继承 `SpringBootServletInitializer` 类，重写 `configure` 方法，Web 容器否则无法检测到启动类
```java
public class MainServletInitializer   extends SpringBootServletInitializer
{
    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder application)
    {
        return application.sources(MainApplication.  class );
    }
}
```
3.（可选）添加 Nacos 服务注册配置，需要注册到 Nacos 则加入此配置
```java
@Configuration
@Slf4j
public class NacosConfig implements ApplicationRunner {

    @Resource
    private NacosAutoServiceRegistration registration;

    @Value("${server.port}")
    Integer port;

    @Override
    public void run(ApplicationArguments args) {
        if (registration != null && port != null) {
            int tomcatPort = port;
            registration.setPort(tomcatPort);
            log.info("当前已注册到 nacos, port为："+tomcatPort);
            registration.start();
        }
    }
}
```
4.加入打 war 包的插件，并将打包方式修改为 war
至此，一个可以在容器中运行，并且可以注册到 Nacos 的微服务 war 包已经打好。此时可以部署了，但让我心梗的是，这此信创改造后的程序并不想往常一样，居然直接部署都不成功！！！果然事情不会一帆风顺的完成。
东方通回发的错误日志如下：
```java
java.lang.IllegalStateException: ContainerBase.addChild: start: org.springframework.beans.factory.BeanDefinitionStoreException:   
Failed to process import candidates for configuration class [io.xxxx.xxxxx.xxxxx.MainApplication]; nested exception is java.lang.ClassCastException:   
org.springframework.web.context.support.ServletContextResource cannot be cast to org.springframework.core.io.ClassPathResource
    at com.tongweb.deploy.TongWebDeployer.deploy(TongWebDeployer.java:348)
    at com.tongweb.deploy.commands.DeployCommand.deploy(DeployCommand.java:278)
    at com.tongweb.console.deployer.service.DeployerService.deploy(DeployerService.java:886)
    at com.tongweb.console.deployer.controller.DeployerController.deploy(DeployerController.java:468)
    at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
    at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
    at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
    at java.lang.reflect.Method.invoke(Method.java:498)
```
由于开发日期比较紧迫，东方通给出的错误日志实在难以定位，并且网上所能查找到的解决方案并不能符合我的情况。我采取了两种尝试性措施期望解决此项问题：A方案，降低自用框架版本，保持和其他正常可用系统一样的版本；B方案，定位自用框架问题并修改。
由于降低框架需要修改代码，可能出现不可控的问题，最终还是决定坚决执行B方案。这是一锅夹生饭，但就算硌牙也得吃下去！
最终，我尝试在 tomcat 9 版本上部署应用，并从tomcat 抛出的比东方通更深入的报错信息定位问题于此处（是的，tomcat 会将报错定位至你的代码，而东方通会包装自己的错误并抛出，相当无语。）：
```java
    @Override
    public PropertySource<?> createPropertySource(String name, EncodedResource encodedResource)
            throws IOException {
        ClassPathResource classPathResource = (ClassPathResource) encodedResource.getResource();
        String locationPattern = classPathResource.getPath();
        String sourceName = classPathResource.getPath();
        PathMatchingResourcePatternResolver resolver = new PathMatchingResourcePatternResolver(new PathMatchingResourcePatternResolver());
        Resource[] resources = resolver.getResources(locationPattern);
        Properties propertiesFromYaml = new Properties();
        for (Resource resource : resources) {
            String active = getActive();
            String endWith = active + ".yml";
            if (resource.getFilename().endsWith(endWith)) {
                Properties properties = loadYaml(resource);
                propertiesFromYaml.putAll(properties);
            }
        }
        return new PropertiesPropertySource(sourceName, propertiesFromYaml);
    }
```
那么现在问题与结论就很清晰明了了，_**直接使用脚本启动应用时，上下文环境为 ApplicationContext，而部署容器时由于东方通和 tomcat 都是基于 servlet 3.0 协议为部署的应用创建了一个 ServletContext 上下文环境。所以框架内用于读取应用配置文件的方法需要将 Resouce 进行强制转换为子类 ClassPathResource 并使用子类特有的 path 属性时，实际传入的 Resource 类型是 ServletContextResource，从而产生如上错误。**_
最终，我采用了反射的方式来修改这段代码
```java
	@SneakyThrows
    @Override
    public PropertySource<?> createPropertySource(String name, EncodedResource encodedResource) {
        Resource contextResource = encodedResource.getResource();
        Method getPath = contextResource.getClass().getMethod("getPath");
        Object invokePath = getPath.invoke(contextResource);
        String locationPattern = (String) invokePath;
        String sourceName=(String) invokePath;
        
        PathMatchingResourcePatternResolver resolver = new PathMatchingResourcePatternResolver(new PathMatchingResourcePatternResolver());
        Resource[] resources = resolver.getResources(locationPattern);
        Properties propertiesFromYaml = new Properties();
        for (Resource resource : resources) {
            String active = getActive();
            String endWith = active + ".yml";
            if (resource.getFilename().endsWith(endWith)) {
                Properties properties = loadYaml(resource);
                propertiesFromYaml.putAll(properties);
            }
        }
        return new PropertiesPropertySource(sourceName, propertiesFromYaml);
    }
```
将框架代码部署至仓库后，重新拉取依赖后打包部署，运行成功。
至此，问题得到完美解决。