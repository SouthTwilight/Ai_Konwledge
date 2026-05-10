#### 一、常用注解
1. Spring Bean相关注解：

| 注解 | 作用 |
| -------| ----------|
| @Autowired | 自动导入Spring 容器管理的对象到类中|
| @RestController | 是@Controller和@ResponseBody的合集 |
| @Component | 通用注解，标注任意类为 Spring 组件。|
| @Repository | 对应持久层即 Dao 层，主要用于数据库相关操作|
| @Service | 对应服务层，主要涉及一些复杂的逻辑，需要用到 Dao 层 |
|@Controller| 对应 Spring MVC 控制层，接受用户请求并返回 Service 层数据|

2. HTTP 请求相关注解：

| 注解 | 作用 |
| -------| ----------|
|@GetMapping|GET 请求|
|@PostMapping|POST 请求|
|@PutMapping|PUT 请求|
|@DeleteMapping|DELETE 请求|

3. HTTP 请求参数相关注解：

| 注解 | 作用 |
| -------| ----------|
|@RequestParam|获取查询参数|
|@PathVariable|获取路径参数|
|@RequestBody|用于读取 Request 请求的 body 部分类型为 application/json 格式的数据，并注入数据至对应 Java 对象|

#### 二、配置文件
##### 1. 读取配置文件
1. 注解@Value
作用：用于注入简单配置信息
使用方式：在需要注入的字段上添加注解，并指定配置名称
```java
@Value("${test.value.annotation}")
String wuhan2020;
```

2. 注解ConfigurationProperties
作用：读取配置并将配置信息 Bean 实例绑定
使用方式：在定义 Java 对象上添加注解，并指定配置前缀；此后便可直接使用 Bean 对象
```java
@Component
@ConfigurationProperties(prefix = "library")
@Setter
@Getter
@ToString
class LibraryProperties {

	private String location;
	private List<Book> books;
	
	@Setter
	@Getter
	@ToString
	static class Book {
		String name;
		String description;
	}
}
```
可以对应解析如下配置：
```yml
library:
	location: 湖北武汉加油中国加油
	books:
		- name: 天才基本法
		  description: 二十二岁的林朝夕在父亲确诊阿尔茨海默病这天
		- name: 时间的秩序
		  description: 为什么我们记得过去，而非未来？
		- name: 了不起的我
		  description: 如何养成一个新习惯？
```
3. 注解@PropertySource
作用：读取properties文件并进行配置
缺陷：不支持导入YMAL文件
使用方式：指定properties文件所在位置，并使用@Value注解注入指定属性
```java
@Component
@PropertySource("classpath:website.properties")
@Getter
@Setter
class WebSite {
	@Value("${url}")
	private String url;
}
```

##### 2. 配置文件优先级
1. 内部配置文件（application.properties 或 application.yml ）加载优先级：
	- 当前项目根目录下的 config 目录下
	- 当前项目的根目录下
	- 当前项目 resources/config 目录下
	- 当前项目 resources 目录下
2. 加载规则：
	- 低优先级存在高优先级没有的属性，会互补配置
	- 同一个配置属性在多个配置文件都存在配置，默认使用第1个读取的。即高优先级的配置会覆盖低优先级的配置。

#### 三、Bean 映射工具
1. 起因：同个数据结构可能被封装成DO、SDO、DTO、VO等不同层级不同用处对象。
2. 常用映射工具：Spring BeanUtils、Apache BeanUtils、MapStruct、ModelMapper、Dozer、Orika、JMapper
3. 使用建议：Apache BeanUtils 、Dozer 、ModelMapper __性能太差不推荐__；MapStruct __性能更好使用更灵活__

#### 四、请求参数校验
参看个人博客[【Java】使用 validation 完成自定义校验注解](https://www.cnblogs.com/southtwilight/p/java-note_03.html)]
