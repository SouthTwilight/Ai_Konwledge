我们在对接接口时，不时会遇到以 Json 格式返回数据的接口。后端解析此类接口返回数据时，不免需要进行反序列化以获取到需要的数据对象。
常用的反序列化工具有 Fastjson、Jackson、Gson。这三种都是不错的 Json 处理工具，我这里较常用的是 Jackson。
##### **使用 Jackson 反序列化：**
1. 添加 maven 依赖
```xml
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>xx.xx.xx</version>
</dependency>
```
2. 创建 ObjectMapper 对象，并进行解析方式的配置
```java
ObjectMapper objectMapper = new ObjectMapper().configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
```
其中，configure 方法配置该 ObjectMapper 对象解析 Json 字符串的方式。DeserializationFeature 以枚举方式给出了 ObjectMapper 的配置方式。该方法可由对应的 enable 或 disable 取代，注意对应的状态字即可。
3. 使用 ObjectMapper 的 readValue 方法进行 反序列化，将 Json 字符串转化成指定类的对象
```java
DataResult dataResult = objectMapper.readValue(JsonStr, DataResult.class);
```
通常情况下，属性名与 Json 字符串的 Key 值相对应即可成功解析出需要类的对象。

##### **注意点：**
1. 在解析复杂 Sql 的时候需要使用 @JsonProperty 注解标注属性对应的 Json 字符串 Key 值，否则即使你指定的 Java 类型接口与属性与 Json 字符串一一对应，也依旧可能存在无法解析或部分解析失败的情况。
2. Jackson 无法直接将 Json 字符串中的时间值转化为 LocalDateTime 等 Java 时间类型，需要为 ObjectMapper 对象注册时间解析模块。
```java
JavaTimeModule module = new JavaTimeModule();
LocalDateTimeDeserializer localDateTimeDeserializer = new LocalDateTimeDeserializer(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
module.addDeserializer(LocalDateTime.class, localDateTimeDeserializer);
ObjectMapper objectMapper = new ObjectMapper().configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
                .registerModule(module);
```
其中 JavaTimeModule、LocalDateTimeDeserializer 等对象依赖 jackson-datatype-jsr310，使用时需要添加依赖
```xml
<dependency>
    <groupId>com.fasterxml.jackson.datatype</groupId>
    <artifactId>jackson-datatype-jsr310</artifactId>
    <version>xx.xx.xx</version>
</dependency>
```