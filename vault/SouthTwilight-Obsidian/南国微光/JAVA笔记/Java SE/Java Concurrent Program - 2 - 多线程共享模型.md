### 临界区

共享资源：多个线程都需要进行访问使用的共有的资源变量

**临界区：**在多个线程内对同一个共享资源进行在时空上的交错操作指令，可能导致共享资源出现异常访问，对此处共享资源进行操作的代码即为**临界区**

竞态条件：多个线程在同一个临界区内共同执行，由于代码执行序列不同各自抢占资源导致最终结果无法预测，则这个过程称为发生竞态条件

### Java 之 synchronized 关键字

- 语法使用
    
    ```java
    1. 方法内使用
    synchronized(sharedObject) //各线程共享资源对象
    {
    		// 临界区
    		......
    }
    
    2. 方法间使用
    public synchronized modifier MethodName() {......}
    
    ```
    

理解：synchronized 是 Java 中的一种**同步/互斥锁**，由于是通过共享资源变量进行加锁，通称为对象锁。通过使某个线程暂时拥有这个对象的锁，使当前共享资源只能被已获取该锁的线程使用，以达到安全执行临界区代码的作用。

**作用：**通过对象锁的方式，保证临界区内代码具备原子性，所有临界区内对共享资源的操作不被其他线程打扰。

- 通用线程安全类
    - String
    - Integer
    - StringBuffer
    - Random
    - Vector
    - Hashtable
    - java.util.concurrent 下所有类

#📌 **注意！！！ *所有线程安全类都是针对其单个方法的使用上线程安全，多个方法的组合不安全。***

### Monitor( 管程 ) 及其 Java 对象锁实现原理

Java 对象构成三要素：**对象头**、实例数据、对齐填充字节

- **对象头**构成：
    - **Mark Word** (32 / 64 bits)：对象哈希地址 / 锁 等信息
    - **Klass Word** (32 bits)：描述java类，指向类的指针
    - Array Length (32bits)：**只有数组对象才有**，标定数组长度

- 32 位 JVM 中的 **Mark Word** 结构：

- 64 位 JVM 的 **Mark Word** 结构对比 32 位 JVM 区别不大
    
- _**Java 锁原理**_
    
    1. 未成锁时，共享资源对象就是一个普通对象。Mark Word 前 25 位记录对象的HashCode，**正常状态锁标志位为 01**，是否偏向为否( 0 ).
        
    2. 共享资源对象初次具备同步锁时，对象将被置为偏向锁( 偏向状态 )。偏向线程无需通过竞争即可轻松获取当前共享资源
        #📌 _偏向锁假定将来只有第一个申请锁的线程会使用锁，不会产生其他线程的竞争，只需要在Mark Word中 CAS( compare and swap: 比较与交换 ) 记录 owner (共享资源持有者），并将偏向状态置为真 ( 1 )，并在 Mark Word 中记录当前对象的偏向线程 ID。_
    3. 当发生一个新线程加入到一个已被偏向的共享资源的竞争时，将会抢占当前共享资源，通过 CAS 操作使资源偏向状态指向该新线程( _Mark Word_记录新偏向线程 ID )。当线程对共享资源竞争逐渐激烈，JVM 将根据**锁升级**机制，将该共享资源的同步锁升级为轻量级锁。
        #📌 _轻量级锁是相对于重量级锁的情况而言，线程竞争获取时只需要将 Mark Word 中的除锁标志位外其余字节作为指针指向获取到共享资源的线程中的 Lock Record ( 锁记录 )，锁状态标志位更新为 00 。当锁竞争不激烈时，其余竞争线程通过自旋方式继续竞争轻量级锁；当竞争过于激烈时，锁膨胀策略将使轻量级锁膨胀为重量级锁。_
    4. 轻量级锁存在时，其余线程竞争共享资源失败后会使用自旋的方式进行争取共享资源。但是俗称为**自旋锁的过程并不是一种同步锁**，只是在轻量级锁的基础上进行不断的获取共享资源的重试，实际上此时共享资源的同步锁状态一直是轻量级锁，直至锁膨胀为重量级锁。
    5. 当多个线程竞争轻量级锁时，某个线程的自旋尝试超过由 JVM 规定的阈值时，轻量级锁膨胀为重量级锁。重量级锁是通过 Monitor 实现的，也成为监视器锁 / 管程。此种锁状态下，未获取到锁的线程会进入阻塞态，并且伴随线程上下文切换。重量级锁同步方式实现的使用成本非常高昂。
        

### **wait / notify**
- 具体使用
    1. wait 方法使已获取到共享资源对象同步锁的当前线程进入等待状态( WAIT / TIMED_WAITING )，同时使当前线程释放其所持有同步锁。直到**其他获取同步锁的线程**调用共享资源对象( 同步锁 )的 notify 方法或 notifyAll 方法使当前线程被唤醒进入 ”就绪状态”
        
    2. wait( 0 ) 是 wait( ) 方法的默认实现，指当前线程等待时间无限，直至被 notify 或 notifyAll 唤醒；sleep( 0 ) 指当前线程睡眠时间为零，即实际上不进入睡眠状态
        #📌 _**线程使用 sleep 方法陷入睡眠等待状态时不会释放其已获取到的同步锁！！！**_
    3. notify 和 notifyAll 的作用，则是唤醒当前对象上的处于 因 wait 方法进入 TIMED_WAITING 状态的等待线程；notify 唤醒单个线程，notifyAll 唤醒所有线程
    4. wait( long timeout ) 使当前线程处于等待状态，直至其他获取到同步锁对象的执行线程**调用此共享资源对象**的 notify 方法或 notifyAll 方法，或因**超过**指定的时间量”，当前线程被唤醒进入“就绪状态”
- **多线程设计模式——保护性暂停与 wait / notify**
    1. **定义：**当线程在访问某个对象时，发现条件不满足时，就暂时挂起等待条件满足时再次访问
    2. 实现案例：Thread.join()、Future 等采用了该模式进行设计
    3. 实现方式：某个结果/条件需要在多线程间传递，可使这些线程关联到一个共享对象；当结果/条件需要不断某些线程到另一些线程时，则可以使用消息队列，将此处实现扩展为 **生产者-消费者模式**
    4. 代码示例
        ```java
        public V protectiveSuspension(long millis) {
            long begin = System.currentTimeMillis(); // 等待开始时间
            long waitedTime = 0; // 等待了多长时间
            synchronized (lock) {
                while (!isFinished) {
                    if(waitedTime >= millis) {
        				// 等待超时处理
                        ......
                        break;
                    }
                    try {
                        lock.wait(millis - waitedTime); // 继续等待剩余时间
                        break;
                    } catch (InterruptedException e) {
        				// 计算已等待时间并保存
                        waitedTime = System.currentTimeMillis() - begin;
                        // 中断、异常处理
        				......
                    }
                }
        		// 当前线程对共享资源进行的处理，即多线程业务代码
        		......
            }
            return v;
        }
        ```
        
- **多线程设计模式——生产者-消费者与 wait / notify**
    1. **定义：**将一块缓冲区作为仓库，生产者将生产的产品存入仓库，消费者可以从仓库中取走产品进行后续操作。
    2. **实现方式：**
        1. 采用某种机制**保护生产者和消费者之间的同步**，是最常用的形式，即保护性暂停；防止生产与消费过于不平衡导致系统异常
        2. 生产者和消费者之间直接建立管道；但管道缓冲不易控制，被传输数据对象不易于封装，实用性不强
    3. 细节处理：
        1. 仓库是生产者和消费者间共享资源，使用同步锁对生产和消费同步
        2. 生产者仅在仓库未满时候生产，仓满则停止生产( 生产者 wait )
        3. 消费者仅在仓库有产品的时候才能消费，仓空则等待( 消费者 wait )
        4. 当消费者发现仓库没产品可消费时通知生产者生产( notify 生产者 )
        5. 生产者产出可消费产品时，通知消费者获取并消费( notify 消费者 )
### park **/ unpark**

> **来源：park / unpark** 是 LockSurpport 类提供的方法，主要用于当前对线**_暂停和恢复_。**在 LockSurpport 类中借助 Unsafe 类提供的本地( native ) 同名方法实现。
> **优点：**相对于 wait/notify 不能精确唤醒某个线程，park/unpark 更具有灵活性。以线程为操作对象，不借助共享资源对象锁，操作更直观。
> **表现：1. park/unpark** 操作核心为通过 unpark 函数对指定线程提供 “许可”，”许可” 可在指定线程调用 park 之前或之后。若无许可，则线程阻塞，若存在许可则继续执行。同一时间，只存在一个 ”许可” ，每次 park 操作消耗一个 “许可”
> **原理：**每个线程具备一个 paker 对象，paker 对象含有三个属性 _counter(计数器)，_cond（条件变量），_mutex(互斥量)。 
> 	**- park :** 
> 		1. 每次 park 操作检查 _counter 值是否为 1 并将其置为零，若为 1 则跳出后续流程。 
> 		2. _mutex 上加锁 
> 		3. 在 _cond 上阻塞，同时释放锁并等待被其他线程唤醒，当被唤醒后，将重新获取锁 
> 		4. 当线程恢复至运行状态后，将 _counter 的值再次置为 0 并释放锁 
> 	**- unpark：**
> 		1. 获取目标线程关联的 parker 对象（**注意：**是目标线程不是当前线程） 
> 		2. 在 _mutex 上加锁 
> 		3. 将 _counter 置为 1 
> 		4. 唤醒在 _cond 上等待着的目标线程并释放锁

### 线程状态转换

- **NEW ——> RUNNABLE：**
    
    线程 A 创建后，调用 _**start**_ 方法使线程 A 状态由 new 转变为 runnable
    
- **RUNNABLE <——> WAITING：**
    
    1. 线程 A 获取到共享资源对象锁后( synchronized(lockObj) )，调用共享资源_**对象锁**_ 的 _**wait**_ 方法将使线程 A 状态 RUNNABLE **—>>** WAITING
    2. 线程 A 调用某线程的 _**join**_ 方法时
        - 线程 A 状态 RUNNABLE **—>>** WAITING，线程 A 在该某线程监视器上等待
        - 该线程运行结束，或其他线程调用线程 A 的 _**interrupt**_ 方法时，线程 A 状态由 WAITING**—>>** RUNNABLE
    3. 线程 A 调用 _**LockSupport**_ 类中方法时
        - 调用 _**park**_ 方法时，线程 A 状态由 RUNNABLE **—>>** WAITING
        - 调用 _**unpark**_ 方法或 A 的 _**interrupt**_ 方法时，线程 A 状态由 WAITING **—>>** RUNNABLE
- **WAITING ——_>_ RUNNABLE / BLOCKED**
    
    1. 其他线程获取到同个对象锁后，调用_**对象锁**_ 的 _**notify**_ / _**notifyAll**_ 方法或线程 A 的 interrupt 方法时：
        - 线程 A 竞争锁成功，线程状态从 WAITING **—>>** RUNNABLE
        - 线程 A 竞争锁失败，线程状态从 WAITING _**—>> BLOCKED**_
### **活跃性**

1. 一个线程不能得到正确结束，有三种现象：**死锁、活锁、饥饿**
- 死锁：
    >条件：互斥、请求并保持、不可剥夺、循环等待
    >定位：使用 JConsole 线程工具查看。Windows系统下使用运行命令工具运行 JConsole。
    >避免：注意加锁顺序，破坏循环等待条件；
    
- 活锁
    
    >条件：多个线程互相改变其他线程的结束条件，导致所有线程都无法结束
    
- 饥饿
    
    >线程由于优先级太低，始终得不到 CPU 调度执行，并且不能结束
    

### _**ReenrtantLock 可重入锁**_

_**ReenrtantLock** 是 JUC 并发编程工具包内的一个工具类。 是一个互斥可重入锁_

 #### **特点：**
- ***可重入：***同 synchronized 一样，是可重入锁，一个线程放弃所获取的锁时，可重新加入等待队列与其他线程一起继续竞争该互斥锁。
- *超时时间：*可设置竞争锁超时时间，在指定时间内未竞争到锁即放弃继续竞争锁
- ***公平锁：*可设置**为公平锁，保证每个线程可以公平的获取到锁，避免可能的饥饿
- ***可打断：***可对竞争锁的线程进行打断，停止未持锁线程的长时间阻塞。竞争锁时需使用 ***reentrantLock.lockInterruptibly*** 方法
- 多条件变量：可设置多个条件变量，保证每次唤醒精准唤醒指定条件变量上等待的线程；synchronized 中有 ***wait*** 方法占用的 ***waitSet*** 等待队列可以认为是条件变量，但 一个synchronized 只支持一个 waitSet 。

```java
// 加锁，以一个 ReenrtantLock 类对象为基准进行枷锁
reenrtantLock.lock()

// 解锁，必须放在 finally 语句块中保证每次运行都可以正确释放锁
reenrtantLock.unlock()

// 可打断锁加锁
reentrantLock.lockInterruptibly()

// 限定时间加锁(时间数，时间单位),返回 boolean(true/false) 值表示是否获得锁
reentrantLock.tryLock(timeNum,TimeUnit.SECONDS)
// 只获取一次，获取不到即返回
reentrantLock.tryLock()

// 公平锁设置 创建 **ReenrtantLock** 对象时传入 boolean(true/false) 值表示是否创建为公平锁
ReenrtantLock reentrantLock = new ReenrtantLock(true)

// 创建新的条件变量;同一把锁可以有多个条件变量
Condition condition = reentrantLock.newConditon()
// 条件不满足时，当前线程在指定条件变量上等待
condition.await()
// 唤醒在指定条件变量上等待的某个线程或所有线程
condition.singal()
condition.singalAll()

```