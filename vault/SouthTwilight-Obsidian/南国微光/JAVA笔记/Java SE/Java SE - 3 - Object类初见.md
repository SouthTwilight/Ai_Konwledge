**JDK类库的根类：**

- Object类是JAVA语言JDK类库的根类，任何一个类默认直接继承或间接继承继承Object类。 主要学习Object类中2个方法——toString与equals

**toString()方法：**

> 1.默认输出："对象完整类名 + @ + 内存16进制哈希码(地址)" 2.默认实现： getClass().getName() + '@' + Integer.toHexString(hashCode())
> 
> **所有类中toString()方法都应当重写为用户需要的形式** String类中的toString()方法已被SUN公司重写

**equals()方法：**
> 1.默认输出：比较对象是否一致，返回值为true/false 2.默认实现： public boolean equals(Object obj) { return (this==obj);}
> **默认实现时是比较调用方法的对象和传参对象是否一致，通常只比较两引用的内存地址，而不比较引用地址内对象的具体内容。**因此，我们所有手写类都应当重写该函数。

**finalize()方法：**

> 对象在被垃圾回收器回收时执行，类似于C++中解构式 
> 该方法在JDK1.8中还有使用，在JDK1.13中已过时