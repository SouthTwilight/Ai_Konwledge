### 总括：
validation 让我们简化了开发过程，可以使用简单的一个注解就实现了很多常见的检验数据的功能，同时支持自定义注解。spring-boot-starter-validation 是由 Spring Boot 整合的一套用于处理 validation 的约定化自动配置启动器。Spring 系列框架通过简单的安装依赖即可直接使用 validation 提供的参数校验功能，通过为接口添加 @Valid / @Validated 对特定参数进行校验。

### 使用方法：
1. 安装依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
</dependency>
```
　　如果已使用 Spring Boot 框架可以不指定版本号，依赖于 Spring Boot 版本。

2. 接口参数添加 @Valid / @Validated 进行参数校验
```java
@RequestMapping("/doLogin")
@ResponseBody
public ResponseBean doLogin(@Valid LoginVo loginVo, HttpServletRequest request, HttpServletResponse response) {
    return userService.doLogin(loginVo, request, response);
}
```

3. 在需要进行校验的参数的属性上使用 validation 基础注解
```java
/* 空检查 */
	@Null 　　　　 　　　　　　// 验证对象是否为null
	@NotNull                // 验证对象是否不为null, 无法查检长度为0的字符串
	@NotBlank   　　　　　　  // 检查约束字符串是不是Null还有被Trim的长度是否大于0,只对字符串,且会去掉前后空格.
	@NotEmpty   　　　　　　  // 检查约束元素是否为NULL或者是EMPTY.

	/* Booelan检查 */
	@AssertTrue     　　　　　 // 验证 Boolean 对象是否为 true 
	@AssertFalse      　      // 验证 Boolean 对象是否为 false 

	/* 长度检查 */
	@Size(min=, max=)   　　 // 验证对象（Array,Collection,Map,String）长度是否在给定的范围之内 
	@Length(min=, max=)  　　// 验证注解的元素值长度在min和max区间内

	/* 日期检查 */
	@Past             　　  // 验证 Date 和 Calendar 对象是否在当前时间之前 
	@Future         　　    // 验证 Date 和 Calendar 对象是否在当前时间之后 
	@Pattern        　　    // 验证 String 对象是否符合正则表达式的规则

	/* 数值检查，建议使用在Stirng,Integer类型，不建议使用在int类型上，因为表单值为“”时无法转换为int，但可以转换为Stirng为"",Integer为null */
	@Min        　　　　　　  // 验证 Number 和 String 对象是否大等于指定的值 
	@Max        　　　　　　  // 验证 Number 和 String 对象是否小等于指定的值 
	@DecimalMax     　　　 　// 被标注的值必须不大于约束中指定的最大值. 这个约束的参数是一个通过BigDecimal定义的最大值的字符串表示.小数存在精度
	@DecimalMin      　　　　// 被标注的值必须不小于约束中指定的最小值. 这个约束的参数是一个通过BigDecimal定义的最小值的字符串表示.小数存在精度
	@Digits     　　        // 验证 Number 和 String 的构成是否合法 
	@Digits(integer=,fraction=) // 验证字符串是否是符合指定格式的数字，interger指定整数精度，fraction指定小数精度。
	@Range(min=, max=) // 验证注解的元素值在最小值和最大值之间 @Range(min=10000,max=50000,message="range.bean.wage")
	
	/* 其他检验 */
	@Valid               // 写在方法参数前，递归的对该对象进行校验, 如果关联对象是个集合或者数组,那么对其中的元素进行递归校验,如果是一个map,则对其中的值部分进行校验.(是否进行递归验证)
	@CreditCardNumber    // 信用卡验证
	@Email               // 验证是否是邮件地址，如果为null,不进行验证，算通过验证。
	@ScriptAssert(lang= ,script=, alias=) // 简单脚本校验
	@URL(protocol=,host=, port=,regexp=, flags=) // IP地址校验
```

4. 自定义参数校验注解
　　4.1 自定义注解
　　可以照抄 @NotNull 等基础校验注解的写法
```java
@Target({ElementType.METHOD, ElementType.FIELD, ElementType.ANNOTATION_TYPE, ElementType.CONSTRUCTOR, ElementType.PARAMETER, ElementType.TYPE_USE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Constraint(
        validatedBy = {IsMobileValidator.class}
)
public @interface IsMobile {
    boolean required() default true;

    String message() default "手机号码格式错误";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};
}
```
　　4.2 实现 ConstraintValidator 接口，用以实现自定义参数校验 
```java

public class IsMobileValidator implements ConstraintValidator<IsMobile,String> {
    private boolean required = false;

    /**
     * @Param: {@link  IsMobile } constraintAnnotation
     * @Return: void
     * @TODO: 初始化方法，可以用自定义注解中获取值进行初始化
     **/
    @Override
    public void initialize(IsMobile constraintAnnotation) {
        required = constraintAnnotation.required();
    }

    /**
     * @Param: {@link  String} value
     * @Param: {@link  ConstraintValidatorContext } constraintValidatorContext
     * @Return: {@link boolean}
     * @TODO: 实际校验自定义注解 value 值
     **/
    @Override
    public boolean isValid(String value, ConstraintValidatorContext constraintValidatorContext) {
        if(required){
            return ValidatorUtil.isMobile(value);
        }else {
            if(StringUtils.isEmpty(value)){
                return true;
            }else {
                return ValidatorUtil.isMobile(value);
            }
        }
    }
}
```

　　_其中 IsMobile 为自定义注解名(根据个人需求自己命名)，isValid 方法具体校验逻辑由个人需求及业务确定。使用时同基础校验注解一般放置在需要校验的参数属性上即可。_

　　_**注意：自定义注解上必须有**_ **_@Constraint 注解，其中 validatedBy 指定执行校验的类，该类必须实现 ConstraintValidator 接口_**