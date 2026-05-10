Swagger 作为 Java 开发中常用的接口文档生成组件，绝大部分情况下都可以满足我们的业务需求。但有些时候依然有些不足，比如针对系统中某些特殊接口需要作出一些增强。

我自己在使用 Swagger 时候遇到需要将 base_path 消除并直接拼接到接口路径上的情形。一共寻找到两种方式：
1. 重写 Swagger2Controller ，并将转发到 tomcat 容器中的请求转发至重写后的 Swagger2Controller 中。
2. 使用切面，将即将序列化的 swagger 对象做定制化更改增强。
　
第一个方案卡在请求转发到重写后的控制器。应用的 Web 容器与 Swagger 的 Web容器并不相通，试了很久也没有实现。最终决定更换赛道，采用第二种方案。
　　
第二种方案可以指定切入点为 springfox.documentation.spring.web.json.JsonSerializer.toJson ，此方法在 “ /v2/api-docs ” 路径响应完毕并将 Swagger 对象转为 Json 对象时使用。

![[../../../attachments/Swagger接口_v2-api-docs.jpg]]
具体切面代码如下：
```java
@Aspect
@Component
@AllArgsConstructor
public class SwaggerAspect {
	@Around("execution(* springfox.documentation.spring.web.json.JsonSerializer.toJson(..))")
	public Object switchDataSource(ProceedingJoinPoint joinPoint) throws Throwable {
		Object[] args = joinPoint.getArgs();
		if (ArrayUtils.isEmpty(args)) {
			return joinPoint.proceed(args);
		}
		Object swaggerObject = args[0];
		if(swaggerObject instanceof Swagger){
			Swagger swagger = (Swagger) swaggerObject;
			String basePath = swagger.getBasePath();
			swagger.setBasePath("/");
			Map<String, Path> paths = swagger.getPaths();
			Map<String, Path> newPaths = new HashMap<>();
			for (Map.Entry<String, Path> entry : paths.entrySet()) {
				String newPath = basePath + entry.getKey();
				newPaths.put(newPath, entry.getValue());
			}
			swagger.setPaths(newPaths);
		}
		args[0] = swaggerObject;
		return joinPoint.proceed(args);
	}
}
```
