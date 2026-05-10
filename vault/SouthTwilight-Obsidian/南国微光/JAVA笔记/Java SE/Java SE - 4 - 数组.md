##### 介绍：

```
      JAVA语言中的数组是一种引用类型
```

###### **数组创建：**

> 1.类型名[] 数组变量名 = new 类型名[数组长度] ； 2.类型名[] 数组变量名 = {数组元素} ；

***注：***_数组一经创建，长度不可变。所有数组都具有属性：length，表示数组长度。因此，JAVA中的数组类似于数据结构中的顺序表类型数据。_

**常用工具方法：**
	1. System.java

👉 _public static native void arraycopy(Object src, int srcPos,Object dest, int destPos,int length);_

> **出处：**java.lang包下System.java文件中提供。 
> **功能：**完成将src数组下标srcPos处(含)长度为length的数组元素拷贝至dest数组下标destPos处(含)

2. Arrays.java

👉 _public static int binarySearch(Object[] a,Object key)_

> **出处：**java.util包下Arrays.java文件中提供。 **功能：**对输入数组完成二分法查找key值

3. Arrays.java
👉 _public static sort binarySearch(Object[] a,Object key)_

> **功能：**将指定的数组进行升序排列。