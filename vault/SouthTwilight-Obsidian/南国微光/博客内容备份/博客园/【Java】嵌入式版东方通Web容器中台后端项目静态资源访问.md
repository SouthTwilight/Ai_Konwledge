嵌入式东方通Web 版本：7.0.E.6_P3 ~ 7.0.E.6_P6
首先直接说结论，内置化东方通Web容器的基准版本较低。对静态资源访问配置必须使用以下语法：
```yaml
# 静态资源访问配置
spring:
    resources:
        static-locations: classpath:/resources/,classpath:/static/,file:/opt/app/FileRoot/
```
事件回顾：
1. 内置Tomcat容器与使用东方通Web容器部署War包，中台项目一切正常，中台管理页面访问无异常
2. 项目管理需要，切换至使用嵌入式东方通Web，发现异常：**无法访问中台页面静态资源**
3. 多次排查确认后，定位为使用嵌入式东方通Web容器时，程序无法读取 Nacos 配置文件中的静态资源路径

原配置文件（该配置文件 org.springframework.boot-web-2.4.2 版本自带的嵌入式 tomcat 容器中正常使用）：
```yaml
# 数据源配置
spring:
    web:
        resources:
            static-locations: classpath:/resources/,classpath:/static/,file:/opt/admin-manager-web/WebRoot/
```
4. 此时查找资料后尝试使用解决方法中的静态资源配置写法，成功解决问题