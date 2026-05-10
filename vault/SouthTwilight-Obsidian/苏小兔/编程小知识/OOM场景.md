<font color="#f79646">常见OOM情况及解决方法 </font> 
情况一、java.lang.OutOfMemoryError: Java heap space —— > java 堆内存溢出  
出现OOM原因：此种情况最常见，一般由于内存泄露或者堆的大小设置不当引起。  
解决办法：对于内存泄露，需要通过内存监控软件查找程序中的泄露代码，而堆大小可以通过虚拟机参数-Xms、-Xmx等修改。  
举例：循环调用new A() 导致堆溢出  
虚拟机参数：-Xms1M -Xmx1M -XX:+HeapDumpOnOutOfMemoryError，  
解释：将-Xmx和-Xms设置为一样可以避免堆自动扩展。-XX:+HeapDumpOnOutOfMemoryError， 解释：可以让虚拟机在出现内存溢出异常时Dump出当前的堆内存转储快照，然后分析Dump文件  
  
情况二、java.lang.OutOfMemoryError: PermGen space —— > java 永久代溢出 ，即方法区溢出了  
出现OOM原因：一般出现于大量Class 或者 jsp页面，或者采用cglib等反射机制的情况，因为上述情况会产生大量的Class信息存储于方法区。另外，过多的常量，尤其是字符串，也会导致方法区溢出。  
解决办法：此种情况可以通过更改方法区的大小来解决，使用类似-XX:PermSize=64m -XX:MaxPermSize=256m 的形式修改。  
举例：循环调用String.intern()方法来写入常量池，常量池溢出。  
虚拟机参数：-XX:PermSize=10M -XX:MaxPermSize=10M，  
解释：表示JVM初始分配的永久代的容量和最大容量。（永久区内存不足，1.8后都在堆上。方法区=永久代，PermGen space”，即永久代）  
  
情况三、java.lang.StackOverflowError ------> 不会抛OOM error，但也是比较常见的Java内存溢出。  
出现OOM原因：JAVA虚拟机栈溢出，一般是由于程序中存在死循环或者深度递归调用造成的，栈大小设置太小也会出现此种溢出。  
解决办法 ：可以通过虚拟机参数 -Xss 来设置栈的大小。  
举例：循环调用对象引用的方式实现栈溢出。  
虚拟机参数：-Xss128k，  
解释：设置虚拟机栈的大小为128kn  
在单线程下，无论栈帧太大还是虚拟机栈容量太小，内存无法分配的时候都会抛出以上错误。