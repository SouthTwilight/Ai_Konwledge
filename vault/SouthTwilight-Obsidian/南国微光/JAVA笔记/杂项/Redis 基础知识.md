##### 基本命令
- 安装
    1.使用 _**‘tar -zxvf [tar.gz压缩包全名]’**_ 解压 redis 压缩包
    2.确定当前系统存在基本 gcc 环境，以便于 redis 程序可以正常安装
    3.在解压后的 redis 目录下使用 _**‘make’**_ 命令重新编译 redis
    4.使用 _**‘make install’**_ 完成安装，默认安装目录为 /usr/local/bin
- 后台启动
    1.将 redis 解压目录下 redis.conf 文件备份到需要路径下(如：/myredis/redis.conf)
    2.将 redis.conf 备份文件内 daemonize 属性值 no 更改为 yes
    3.使用命令 _**‘redis-server /myredis/redis.conf’**_ 即可后台启动 redis 程序
- 多 Redis 启动
    - 主机配置文件编写
        > 新建配置文件，且在各配置文件内加入内容： 
        > 	_**include [/myredis/redis.conf]**_ 
        > 	_**pidfile [/var/run/redis_6379.pid]**_ 
        > 	_**port [6379]**_ 
        > 	_**dbfilename [dump6379.rdb]**_
           释义：1.引入指定位置conf文件作为公共部分；2.指定pid位置；3.指定启动端口号；4.指定启动dump文件( RDB 文件)    
	- 启动每个需要的 redis 服务
            redis-server redis6379.conf
    - 连接进入指定 redis 实例
        命令：redis-cli -p [6379]
	    释义：进入指定端口为 [6379] 的 redis 实例
    - **查看主机运行情况**
        _**info replication**_
    - **配置从库 (不配主库)**
        命令： slaveof   [ip]  [port]
        释义：将当前 redis 实例配置为指定 IP 指定端口的 redis 实例的从服务器
	#📌 主机重启无需额外操作，从机重启需重新设置隶属关系。
        
        
##### 全库命令
 _**select [numbers]**_
    切换当前 redis 系统数据库为指定序号数据库
    #📌 一个 Redis 系统具有 16 个数据库，默认为 0 号库；统一密码管理，所有库密码相同    
- _**dbsize**_
    查看当前数据库存在的数据量
- _**flushdb**_
    清空当前数据库
- _**flushall**_
    清空当前 Redis 系统所有数据库
        
##### 键( Key )命令
- keys *
	查看当前数据库所有 键值( key )
- _**exists [key]**_
    判断当前数据库是否存在指定键值
- _**type [key]**_
    查看指定键值( key )对应的数据( value )的数据类型
- _**del [key]**_
    删除指定键值的数据，强制删除
- _**unlink [key]**_
    根据指定键值对数据进行非阻塞删除，异步操作
- _**expire [key]  [seconds]**_
    对指定键值数据设定过期时间，seconds 秒数后数据过期
- _**ttl [key]**_
    查看指定键值数据还有多少秒数过期，-1 表示永不过期，-2 表示已过期
        
##### 字符串( string )命令
- _**set [key]  [value]**_
    往当前数据库添加键值对
- _**get [key]**_
    查询对应键值的数据值
- _**append [key]  [value]**_
    将给定 [value] 追加到原数据值末尾，命令返回值为追加后总数据值长度。
- _**strlen [key]**_
    获得指定键值的数据值长度
- _**setnx [key]  [value]**_
    只有在键值 [key] 不存在时，设置键值 [key] 的数据值 [value]
- ***incr/decr [key]***
    将 key 中储存的数据值增加/减少 1；只有当数据值类型为数字时可以使用
- **incrby/decrby [key]  [steps]**
    将 key 中储存的数据值增加/减少步长 [steps]；只有当数据值类型为数字时可以使用        
- _**mset [key1]  [value1]  [key2]  [value2]  ..…**_
    同时设置一个或多个 key-value 对
- _**mget [key1]  [key2]  [key3]  ..…**_
    同时获取一个或多个 value
- _**msetnx [key1]  [value1]  [key2]  [value2] ..…**_
    同时设置一个或多个 key-value 对，当且仅当**所有给定 key 都不存在**。
- _**getrange [key]  [begin]  [end]**_
    获得值的范围，类似 java 中的 substring，**前包，后包**
- _**setrange [key]  [begin]  [value]**_
    用  [value] 覆写 [key] 所储存的字符串值，从 [begin] 开始(**索引从0开始**)。begin 前不管，后面被全部覆盖
- _**setex  [key]  [seconds]  [value]**_
    设置键值的同时，设置过期时间，单位秒。
- _**getset [key]  [value]**_
    以新换旧，设置了新值同时获得旧值
        
##### 列表( List )命令
#📌 Redis 列表是简单的字符串列表，单键多值，按照插入顺序排序。底层实际是双向链表，对两端操作性能很高，通过索引下标操作中间节点性能较差。
- _**lpush/rpush  [key1]  [value1]  [value2]  [value3] .…**_
    从左边/右边依次插入一个或多个值。实际是链表插入方法的**头插法/尾插法**
- _**lpop/rpop [key]**_
    从左边/右边取出一个数据值，链表中会将节点断裂开。不存在值时，该键值对数据被销毁。
- _**rpoplpush [key1]  [key2]**_
    从[key1]列表**右边**吐出一个值，插到[key2]列表**左边**。取尾头插。
- _**lrange [key]  [start]  [stop]**_
    按照索引下标获得元素(从左到右)；当 [stop] 为 -1 时，表示从 [start] 开始直至结束。
    #📌 Redis 不存在 rrange 命令；正数表示从左开始，0为左边第一个，负数表示从右边开始数，-1为第一个。输出序列只能为从左到右，不存在start为-1，stop为0的情况
- _**lindex [key]  [index]**_
    按照索引下标获得元素(从左到右)
- _**llen [key]**_
    获得列表长度
- _**linsert [key] before/after [value]  [newValue]**_
    在 [value] 的前面/后面插入 [newvalue] 插入值 **(即在 [value] 值附近使用头插/尾插)**
- _**lrem [key]  [n]  [value]**_
    从左边删除 n 个 value (从左到右)，从**头部**取出 n 个指定值；**不足 n 个时，返回值为实际取出指定 value 个数。**
- _**lset [key]  [index]  [value]**_
    将列表 key 下标(从左往右)为 index 的值替换成 value；序列号从 0 开始。

##### 集合( set )命令
#📌 Set是 string 类型的无序集合。它底层其实是一个 value 为 null 的 hash 表，所以添加，删除，查找的**复杂度都是O(1)**。数据值占用哈希表的 key 值部分。_**Set 是可以自动排重**_
- _**sadd  [key1]  [value1]  [value2] ..…**_
    将一个或多个元素加入到集合 key 中，已经存在的元素将被忽略
- _**smembers [key]**_
    取出该集合的所有值
- _**sismember [key]  [value]**_
    判断集合 [key] 是否为含有该 [value] 值，有则返回值 1，没有则为 0
- _**scard [key]**_
    返回该集合的元素个数。
- _**srem   [key1]  [value1]  [value2] ……**_
    删除集合中的某个/几个元素
- _**spop [key]**_
    **随机**从该集合中取出一个值，**原数据从集合中删除**
- _**srandmember [key]  [n]**_
    **随机**从该集合中取出n个值，**不会从集合中删除原数据**
- _**smove [sourceKey1]  [destinationKey2]  [value]**_
    把集合中指定值从一个集合移动到另一个集合
- _**sinter [key1]  [key2]**_
    返回两个集合的交集元素
- _**sunion [key1]  [key2]**_
    返回两个集合的并集元素
- _**sdiff [key1]  [key2]**_
    返回两个集合的**差集，**元素(key1中的，不包含key2中的)
        
##### 哈希( hash )命令
#📌 hash 是一个 string 类型的 field 和 value 映射表，hash 特别适合用于存储对象。类似Java中的 Map<String,Object>。_hash 类型对应数据结构：ziplist (压缩列表)、hashtable (哈希表)。当 field-value 键值对长度较短且个数较少时使用 ziplist，否则使用 hashtable_
- _**hset [key]  [field]  [value]**_
    给给定 key 值集合中指定  [field] 键赋值 [value]
- _**hget [key]  [field]**_
    从 [key] 集合中取出键值为 [field] 的数据值 [value]
- _**hmset [key]  [field1]  [value1]  [field2]  [value2]…**_
    批量设置hash的值
- _**hexists [key]  [field] **_
    查看哈希表[key]中，给定域 [field] 是否存在
- _**hkeys [key]**_
    列出该 hash 集合所有 [field]
- _**hvals [key]**_
    列出该 hash 集合的所有 [value]
- _**hincrby [key]  [field]  [increment]**_
    为哈希表 [key] 中的域 [field] 的值加上增量(可正可负)；当 [value] 值不为数字时报错
- _**hsetnx [key]  [field]  [value]**_
    将哈希表 [key] 中的域 [field] 的值设置为 [value]，当且仅当域 [field] 不存在时
        
        
##### 有序集合( zset )
#📌 Zset 即为 **sorted set**。有序集合每个成员关联一个**评分(score)，** 评分(score)被用来按**最低分到最高分**方式**排序**集合中成员。集合成员唯一，**评分可以重复** 。可根据评分(score)或次序(position)获取某范围内元素。 
zset 底层使用了两个数据结构: 1) hash，关联元素 value 和权重 score ，保障元素 value的唯一性；2)跳跃表，根据 score 给元素 value 排序。跳跃表效率堪比红黑树，实现比红黑树简单。
- _**zadd [key]  [score1]  [value1]  [score2]  [value2]…**_
    将一个或多个 [value1] 元素及其 [score] 值加入到有序集 [key] 当中
- _**zrange [key]  [start]  [stop]  (withscores)**_
    返回有序集[key] 中，下标在 [start]  [stop] 之间元素；可选参数 withscores，可将 [score] 一并返回
- _**zrangebyscore/ zrevrangebyscore [key]  minmax (withscores) (limit offset count)**_
    返回有序集[key] 中，所有 [score] 值介于 [min] 和 [max] 之间(包括等于 min 或 max )的成员。有序集成员按 score 值**递增/递减** (从小到大/从大到小) 次序排列
- _**zincrby [key]  [increment]  [value]**_
    为 [value] 元素的 score 加上增量 ***[increment]***
- _**zrem [key]  [value]**_
    删除该集合下，指定值的元素
- _**zcount [key]  [min]  [max]**_
    统计该集合，分数区间内的元素个数
- _**zrank [key]  [value]**_
    返回该值在集合中的排名，从0开始