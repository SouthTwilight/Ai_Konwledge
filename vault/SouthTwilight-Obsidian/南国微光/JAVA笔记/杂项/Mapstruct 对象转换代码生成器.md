### Mapstruct 对象转换代码生成器：适用于单表简单查询的对象转换业务

### 初解 **@Mapper**

> 1. 于 mybatis3.4.0 被引入，用于简化 mapper 映射文件编写( 准确来说是不再写映射文件)
> 2. 主要存在 @Select 和 @Mapper 注解
> 3. @Select 注解于方法之上，用于指明 sql 语句，@Select("select * from user where name = #{name}")
> 4. @Mapper 具备 componentModel 属性，指定自动生成接口实现类的组件类型

- **mapstruct 依赖包**
	```xml
	<dependency>
		<groupId>org.mapstruct</groupId>
		<artifactId>mapstruct-jdk8</artifactId>
		<version>1.3.0.Final</version>
	</dependency>
	<dependency>
		<groupId>org.mapstruct</groupId>
		<artifactId>mapstruct-processor</artifactId>
		<version>1.2.0.Final</version>
	</dependency>
	```

- 使用 mapstruct 进行**简单对象转换**
	1. 定义数据对象转换接口类，并添加 @Mapper 注解
	    ```java
	    @Mapper
	    public interface UserCovertBasic {...}
	    ```
	2. 在接口中声明了一个成员变量 INSTANCE，用于访问 Mapper 接口的实现
	    ```java
	    UserCovertBasic INSTANCE = Mappers.getMapper(UserCovertBasic.class);
	    ```
	3. 定义对象转换的方法，方法名不重要：参数为待转换对象，返回值是转换目标对象
	    ```java
	    // 将 User 的 source 对象转换为一个 UserVO1 对象
	    UserVO1 toConvertVO1(User source);
	    // 将 UserVO1 的 userVO1对象转换为一个 User 对象
	    User fromConvertEntity1(UserVO1 userVO1);
	    ```
	4. 使用时直接通过对应的接口方法转换成目标对象即可
	    ```java
	    UserVO1 userVO1 = UserCovertBasic.INSTANCE.toConvertVO1(user);
	    ```


### **复杂情况对象转换**

#### **同名类型不一致：**
1. 定义接口时须使用 @Mappings 包含对多个不同属性的指定
```java
  @Mappings({
      	@Mapping(target = "createTime", expression = "java(com.java.mmzsblog.util.DateTransform.strToDate(source.getCreateTime()))"),
  })
  UserVO3 toConvertVO3(User source);
```
   其中expression 为指定的类型转换处理函数，即指定类 DateTransform 中 strToDate(String str)方法处理 createTime 属性
    
2. 在指定方法中实现类型转换
```java
    public class DateTransform {
        public static LocalDateTime strToDate(String str){
            DateTimeFormatter df = DateTimeFormatter.ofPattern("yyy-MM-dd HH:mm:ss");
            return LocalDateTime.parse("2018-01-12 17:07:05",df);
        }
    }
```

3. 自动类型转化依理：
    > 1. 基本类型及其他们对应的包装类型会自动拆装箱
    > 2. 基本类的包装类型和string类型之间相互转换
    > 3. 大部分实现了 toString 方法的类型转化为 String 类型
    

#### **同类型字段名不一致：**
1. 定义接口时须使用 @Mappings 包含对多个不同字段名之间对应关系的指定
```java
    @Mappings({
    	@Mapping(source = "id", target = "userId"),
      @Mapping(source = "name", target = "userName")
    })
    UserVO4 toConvertVO(User source);
```