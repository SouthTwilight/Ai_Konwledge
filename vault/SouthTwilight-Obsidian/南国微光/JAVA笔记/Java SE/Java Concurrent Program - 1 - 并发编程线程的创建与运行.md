### 一、创建线程

##### **使用 Thread 类进行新建**
```java
// 新建线程实例 t
Thread t = new Thread("threadName"){
	// 线程逻辑代码，类似于 main 函数
	public void run(){......}
}
// 启动运行线程实例
t.start();
```
##### **使用 Runnable 接口与 Thread 类联合新建**

 ###### **特点：**
> 1、将线程业务逻辑与线程实例本身分离开 
> 2、Runnable 接口更适合与线程池等高级API配合使用 
> 3、Runnable 使任务类脱离 Thread 类继承体系，使用更灵活

```java
// 通过匿名类创建一个 Runnable 接口类型对象
Runnable r = new Runnable(){
	// 实现接口中 run 方法，处理线程业务逻辑
	public void run(){......}
}

// 创建线程实例并运行
Thread t = new Thread(r,"threadName");
t.start();
```

 ###### Runnable 对象在 Thread 中被赋予一个类变量，在调用 Thread 类中 run() 方法时，该类变量不为空时优先调用变量( Runnable )的 run() 方法
 #📌 **使用 Thread 或 Runnable 都可以使用 Lambda 表达式进行代码简化 run 方法书写**

```java
Thread t = new Thread(()->{......}, "threadName");
```

 ###### 使用 FutureTask 类
>1. `FutureTask` 类实现 `RunnableFuture` 接口。`RunnableFuture` 继承于 `Runnable` 接口和 `Future` 接口。其中 `Future` 接口可使用 get 方法返回线程执行结果。
>2. . `FutureTask` 类需要配合 `Callable` 类型参数创建对象，`Callable` 用于处理返回结果情况
>3. 创建完成的 `FutureTask` 对象需要像 `Runnable` 对象一样与 `Thread` 类配合新建线程
```java
    FutureTask<Result> futureTask = new FutureTask<>(()->{
    	......
    	return (Result);
    });
    new Thread(futureTask ,"threadName").start();
    // 获取线程执行结果
    Result result = futureTask.get();
```

#📌 Callable 接口与 Runnable 接口： 1、Callable 接口的方法叫 call ；Runnable 接口方法叫 run (与 Thread 类方法同名) 2、call 方法具有返回值，run 方法不具备返回值 3、call 方法可以抛出异常，run 方法无法抛出异常

### 二、查看并干预进程

###### Windows 系统
1. **任务管理器**直接查看并进行操作
2. **命令提示符**中使用 tasklist 命令查看系统进程，使用 taskkill 杀死进程
```bash
1. tasklist                 //直接查看所有进程
2. tasklist | findstr str   //根据str字符串搜索所有进程名中含有该字符串的进程
3. taskkill /F /PID threadNumber // /F表意强制杀死，/PID指明根据唯一线程编号，threadNumber 为每个线程唯一的数字编号
```
###### Linux 系统
- ps -fe 查看所有进程
- ps -fT -p [PID] 查看某个进程（PID）的所有线程
- kill 杀死进程
- top -H -p [PID] 按大写 H 切换是否显示线程；查看某个进程（PID）的所有线程

###### Java 进程相关
- jps 命令查看所有 Java 进程
- jstack [PID] 查看某个 Java 进程（PID）的所有线程状态
- jconsole 来查看某个 Java 进程中线程的运行情况（图形界面）

###### JConsole监控 Java 进程/线程
1. 启动：使用 win+r 打开 Windows 系统命令运行器，输入 jconsole 命令
2. 监控本地 Java 程序进程/线程，找到本地正在运行（JConsole启动瞬间）的 Java 进程
3. 远程监控某主机暴露的 Java 进程与服务；使用命令设置 Java 程序启动及其参数；通过设置的 IP 地址与端口号进行连接；
    ```bash
    java 
    -Djava.rmi.server.hostname=`ip地址` 
    -Dcom.sun.management.jmxremote 
    -Dcom.sun.management.jmxremote.port=`连接端口` 
    -Dcom.sun.management.jmxremote.ssl=是否安全连接(true/false) 
    -Dcom.sun.management.jmxremote.authenticate=是否认证(true/false) 
    java类名(不含后缀)
    ```
      - 认证访问控制设置
        1. 复制 jmxremote.password 文件 (复制后改名才可修改，修改完成后用修改件覆盖原件)
        2. 修改 jmxremote.password 和 jmxremote.access 文件的权限为 600 即文件所有者可读写
        3. 连接时填入 controlRole（用户名），R&D（密码）
        4. 成功监控界面
### 三、栈与栈帧
 ###### **栈（内存）**
1. JVM 由堆、栈、方法区组成其内存，其中栈内存是由 JVM 在一个线程启动时分配给此线程的内存区。
2. Java 程序开始执行时其字节码（class）被加载进入方法区内存
 ###### **栈帧**
1. 每个栈由多个栈帧（Frame）组成，线程的每个方法被调用时会将此方法放入栈内存最上面，执行完成后该方法从栈内存最上面被取出。该过程即是一个方法的入栈和弹栈。
2. 方法执行过程中的局部变量存储在栈帧内部的局部变量表中
 ###### 多线程调试
1. 在各线程内分别打上断点，右键点击断点选择断点模式为 Thread ，否则不可看到线程各自运行情况。
 ###### **上下文切换**
>**上下文切换原因：** 
>	1. 当前线程 CPU 时间片用完，需转入就绪状态并让出 CPU 
>	2. 垃圾回收器线程执行垃圾回收任务 
>	3. 更高优先级的线程抢占 CPU 
>	4. 线程调用 sleep/yield/wait/join/park 等迫使自己进入阻塞态的方法

上下文切换时，操作系统（JVM）先保存当前线程状态，并恢复/新建另一个线程状态。线程状态由各线程内部程序计数器保存，即记住当前线程下一条 JVM 指令执行地址。由于**上下文切换需要保存旧栈数据，并加载新栈数据，频繁切换会影响程序性能。**

### 四、线程状态
##### _**操作系统五状态**_
   ###### ***初始状态：*** 
   - 在语言中创建了该线程，但还未与操作系统关联，并未实际创建该线程栈空间
   ###### ***可运行状态（就绪状态）：*** 
   - 线程已被实际状态，随时可由 CPU 调取运行
   ###### ***运行状态：*** 
   线程被 CPU 分配到时间片，线程代码被执行。时间片消耗完会再次转换为就绪状态，每次相互转换都会有线程上下文切换
   ###### _**阻塞状态**_
   - 调用阻塞 API （IO流等）时，该线程使用 CPU，触发上下文切换并使自己进入阻塞状态
   - 阻塞 API 执行完毕后，操作系统唤醒该阻塞线程，并转换至**就绪状态**
   - 阻塞状态的线程不被唤醒则会一直处于不被调度器调用的状态
   ###### ***终止状态：*** 
   - 线程执行完毕，生命周期已结束。线程状态不可变更，栈空间等待被操作系统回收
##### _**JAVA 程序六状态**_
   - **NEW**：线程刚被创建，但尚未通过 start 启动
   - **RUNNABLE( RUNNING )：**start 方法将使线程进入 **RUNNABLE** 状态，其中此状态囊括操作系统五状态中的**运行状态、就绪状态、I/O阻塞状态**
   - **TERMINATED：**线程代码运行结束，线程进入自然终止状态
   - BLOCKED 
   - WAITING
   - TIMED_WAITING
#📌 TIMED_WAITING / BLOCKED / WAITING 都是 Java 中对**阻塞**的细分

### 五、线程常用方法

|方法名|是否静态|功能|备注|
|---|---|---|---|
|start||启动新线程，新线程运行 run 方法|start 使线程进入就绪态，run 方法代码在分配时间片后执行|
|run||新线程启动时调用该方法||
|join()||等待指定线程的运行结束||
|join( long time )||等待指定线程运行结束，最多等待 time 长毫秒||
|getId||获取线程长整型的 id 标识|每个线程 id 在当前系统中唯一|
|getName||获取当前线程名||
|setName( String )||修改当前线程名为 String||
|getPriority||获取线程优先级||
|setPriority( int )||修改线程优先级|线程优先级是1~10 整数，较大优先级有更高几率被 CPU 调取执行|
|getState||获取线程状态|6个线程状态：NEW, RUNNABLE, BLOCKED, WAITING,TIMED_WAITING, TERMINATED|
|isInterrupted||判断当前线程是否被打断|不会清除当前已有的打断标记|
|isAlive||线程是否存活||
|( 所有线程代码运行完成 )||||
|interrupt||打断线程|sleep，wait，join 的线程被打断会抛出InterruptedException，并清除打断标记 ；打断运行中或 park 线程，则设置打断标记|
|interrupted|是|判断当前线程是否被打断|会清除当前已有的打断标记|
|currentThread|是|获取当前正在执行的线程||
|sleep( long time )|是|让当前执行的线程休眠指定毫秒数，进入阻塞态让出 CPU||
|yield|是|提示/请求线程调度器让出当前线程对 CPU 的使用|测试和调试时常用|

 ###### start / run
   - 线程中的 **run** 方法可作为线程对象的属性方法被直接调用，但使用线程对象直接调用 run 方法时不会开辟新线程运行该方法，而会在当前线程中直接作为程序代码被运行。
   - 调用线程对象的 **start** 方法会为当前线程对象开辟新线程，在新线程中执行 run 方法代码
 ###### sleep / yield
  - 在一个线程中调用 **sleep** 方法，会使当前线程从 Runnable 运行状态进入 Time_waiting 阻塞态
  - 其他线程使用 interrupt 方法打断一个正在 **sleep** 的线程时，会抛出 InterruptedException
  - 推荐使用 TimeUnit 提供的 **sleep** 方法，而不是 Thread 提供的 sleep
  - 调用 **yield** 使当前线程从 Runnable 运行状态转入 Runnable 就绪状态，其它线程被调度进入 Runnable 运行状态。即使当前线程在时间片未耗完前让出 CPU
  - **yield** 具体实现依赖操作系统的任务调度器
 ###### join
  - join 方法解决线程同步问题，A 线程通过 B 线程对象调用 join 方法，将使 A 线程进入阻塞状态，等待 B 线程执行完成后继续实行 A 线程剩余代码。这样使 A 与 B 两线程具备序列执行的同步化。
  - join( long ) 方法限制当前线程等待时间，A 线程通过 B 线程对象调用 join( long ) 方法，在规定时间内 B 线程未结束返回，则 A 线程不再等待继续执行
 ###### interrupt
  1. 打断调用 sleep / wait / join 方法后，自身线程进入阻塞状态的线程。打断其阻塞状态
        - 打断 sleep / wait 方法后，线程打断标记会被清空，线程进入 RUNNABLE 的就绪状态或运行状态
        - 执行线程 B，等待线程 A ，在 A 中调用 B.join 。打断 join 方法后会将 A 线程的打断标记置真，等待线程 A 进入 RUNNABLE 的就绪状态。执行线程 B 不受影响
  2. 打断正常运行线程，将使该线程打断标记置真，但不会影响该线程的正常运行
  3. **将线程置为 park 状态时，会使线程进入 WIATING 状态，当线程打断标记已置真时，park 不会生效。打断 park 线程时会将当前线程唤醒转为 RUNNABLE 状态，且使打断标记置为真**
#📌 LockSupport.park 将挂起当前线程，使线程进入 WAITING 类型的阻塞状态，等待唤醒。可以使用 LockSupport.park( threadName ) 唤醒指定线程
 ###### 已过时方法，不要在程序中使用
  - stop : 停止线程运行
  - suspend : 挂起（暂停）线程运行
  - resume : 恢复线程运行

#📌 守护线程设置：
```java
	new Thread( ()→{......} ).setDaemon( true )
```

##### _**基于 interrupt 的两阶段终止**_
1. stop 终止线程的缺点：无论线程处于什么状态，stop 会直接终止线程，可能导致线程占有资源得不到释放造成系统资源损失
```java
	myThread = new Thread(() -> {
        while (true) {
            Thread current = Thread.currentThread();
            // 是否被打断
            if (current.isInterrupted()) {
				// 关闭前处理
                ......
                break;
            }
            try {
				//业务逻辑
                ......
            } catch (InterruptedException e) {
                // 异常处理
				......
            }
        }
    }, "monitor");
```