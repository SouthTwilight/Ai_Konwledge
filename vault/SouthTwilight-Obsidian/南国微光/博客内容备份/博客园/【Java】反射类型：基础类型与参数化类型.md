Java.lang.Class 是一个比较特殊的类，它用于封装被装入到 JVM 中的类（包括类和接口）的信息。
当一个类或接口被装入的 JVM 时便会产生一个与之关联的 java.lang.Class 对象，可以通过这个 Class 对象对被装入类的详细信息进行访问。
**枚举类型**是类的一种。**注释类型是接口的一种。**每个**数组**也属于一个类，该类反映为class对象，该对象由具有相同元素类型和维数的所有数组共享。**基本Java类型**（boolean、byte、char、short、int、long、float和double）和**关键字void**也表示为Class对象。
类没有公共构造函数。相反，当类加载器调用其中一个defineClass方法并传递类文件的字节时，Java虚拟机会自动通过类加载器构造Class对象。


Class 是 Type 接口 (所有类的公共超接口 ) 的直接实现子类，也就是说所有的原始类的超类型都是 Class 。这是相对于 Type 类型的 ParameterizedType，GenericArrayType，TypeVariable 和 WildcardType 四个直接子接口而言，这四个接口分别对应四种参数化类型（俗称泛型）

- Class: 代表着类型中的原始类型以及基本类型。包含我们平常所指的简单类、枚举、数组(String[]、byte[])、注解，还包括基本类型及其对应的包装类。其意义为：类的抽象，即对“类”做描述：比如类有修饰、字段、方法等属性，有获得该类的所有方法、所有公有方法等方法。
- ParameterizedType: 表示一种直接的参数化的类型，也是最简单的参数化类型：例如 List<String> , Map<String,Object> 的整体
- GenericArrayType: 表示带有范型数组类型，描述的是形如：A<T>[ ] 或 T[ ] 的类型。其实也就是描述 ParameterizedType 类型以及 TypeVariable 类型的数组，即形如：classA<T>[ ][ ]、T[ ]等
- TypeVariable: 类型变量,表示的是参数化类型中实际类型。也就是泛型 A<T> 中的 T 的实际类型
- WildcardType: 通配符类型表达式，比如 <? extends A>，<? super B> 的这整个通配符参数化类型。提供 getUpperBounds 获取上界 ( A )，和 getLowerBounds 获取下界 ( B ) 的方法

　　所以参数化类型 instanceof Class 等于 false。可以参看 org.apache.ibatis.type.TypeReference#getSuperclassTypeParameter 方法对参数化类型与 Class 的实际使用

　　最后，可以参看 [博客](https://blog.csdn.net/weixin_37549458/article/details/109653091)