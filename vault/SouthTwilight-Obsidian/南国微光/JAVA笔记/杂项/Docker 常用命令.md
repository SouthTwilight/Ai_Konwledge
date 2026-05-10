### Linux 安装命令
1. * 卸载旧版本
	```shell
	sudo yum remove docker \ 
				docker-client \ 
				docker-client-latest \ 
				docker-common \ 
				docker-latest \ 
				docker-latest-logrotate \ 
				docker-logrotate \ 
				docker-engine
	```
2. 安装 gcc 编译环境
	```shell
	1.yum -y install gcc 
	2.yum -y install gcc-c++
	```
3. 安装 yum 工具包
	```shell
	yum install -y yum-utils
	```
4. 设置镜像仓库（使用阿里云镜像代替官方镜像）
	```shell
	yum-config-manager --add-repo <http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo>
	```
5. 更新 yum 软件包索引
	```bash
	yum makecache fast
	```
6. 安装DOCKER CE
	```shell
	yum -y install docker-ce docker-ce-cli [containerd.io](http://containerd.io/)
	```
7. 启动命令
	```shell
	systemctl start docker
	```
8. 运行测试 Hello World
	```shell
	docker run hello-world
	```
9. 设置阿里云镜像加速
	- 1. 获取镜像加速器地址
	  ```shell 
		个人镜像加速器：
			  https://jghit5yz.mirror.aliyuncs.com
	  ```
	- 2. 执行脚本语句(配置 daemon 文件，重启 docker 服务)
		```
		1. sudo mkdir -p /etc/docker 
		2. sudo tee /etc/docker/daemon.json <<-'EOF' 
		   { 
			   "registry-mirrors": ["https://jghit5yz.mirror.aliyuncs.com"] 
		   } 
		   EOF 
		3. sudo systemctl daemon-reload 
		4. sudo systemctl restart docker
	    ```
10. 卸载命令
	```shell
	1. systemctl stop docker 
	2. yum remove docker-ce docker-ce-cli containerd.io 
	3. rm -rf /var/lib/docker 
	4. rm -rf /var/lib/containerd
	```

### Linux 运行时 Docker 命令
1. 启动 Docker
	```shell
	systemctl start docker
    ```
2. 停止 Docker
    ```shell
    systemctl stop docker
    ```
3. 重启 Docker
	```shell
	systemctl restart docker
	```
4. 查看 Docker 状态
    ```shell
    systemctl status docker
	```
5. 开机启动
    ```shell
    systemctl enable docker
	```
6. 查看 Docker 概要信息
	```shell
	docker info
    ```
7. 帮助文档
	1. 总体文档查看
		```shell
			docker --help
		```
    2. 具体命令(Particular Command)查看
	    ```shell
	     docker [Particular Command] --help
		```


### Docker 安装 Mysql
1. 指定版本【version】拉取 mysql 镜像
	```shell
	docker pull mysql:version
	```
2. 配置并运行 mysql
	```shell
	docker run -d -p 3306:3306 --privileged=true -v /usr/local/mysql/log:/var/log/mysql -v /usr/local/mysql/data:/var/lib/mysql -v /usr/local/mysql/conf:/etc/mysql/conf.d -e MYSQL_ROOT_PASSWORD=【password】 --name 【docker title】 mysql:version
	```
3. 启动完成后自定义 Mysql 配置
	```shell
	1. cd /usr/local/mysql/conf 
	2. vim my.cnf 
	3. [client] 
	   default_character_set=utf8 
	   [mysqld] 
	   collation_server=utf8_general_ci 
	   character_set_server=utf8 
	4. docker restart mysql
	```



### Docker 安装 Redis
1. 指定版本【version】拉取 redis 镜像
	```shell
	docker pull redis:【version】
	```
2. 配置并运行 redis
	```shell
	docker run --restart=always --log-opt max-size=100m --log-opt max-file=2 -p 6379:6379 --name 【docker title】-v /usr/local/redis/redis.conf:/etc/redis/redis.conf -v /usr/local/redis/data:/var/redis/data -d redis:【version】 redis-server /etc/redis/redis.conf  --appendonly yes  --requirepass 【password】
	```
3. docker 启动 redis 常用 redis.conf 文件
	```shell
	# bind 192.168.1.100 10.0.0.1 
	# bind 127.0.0.1 ::1 
	# bind 127.0.0.1 
	protected-mode no 
	port 6379 
	tcp-backlog 511 
	requirepass 015203nie 
	timeout 0 
	tcp-keepalive 300 
	daemonize no 
	supervised no 
	pidfile /var/run/redis_6379.pid 
	loglevel notice 
	logfile "" 
	databases 30 
	always-show-logo yes 
	
	save 900 1 
	save 300 10 
	save 60 10000 
	
	stop-writes-on-bgsave-error yes 
	rdbcompression yes 
	rdbchecksum yes 
	dbfilename dump.rdb 
	dir ./ 
	
	replica-serve-stale-data yes 
	replica-read-only yes 
	repl-diskless-sync no 
	repl-disable-tcp-nodelay no 
	replica-priority 100 
	
	lazyfree-lazy-eviction no 
	lazyfree-lazy-expire no 
	lazyfree-lazy-server-del no 
	replica-lazy-flush no 
	
	appendonly yes 
	appendfilename "appendonly.aof" 
	no-appendfsync-on-rewrite no 
	
	auto-aof-rewrite-percentage 100 
	auto-aof-rewrite-min-size 64mb 
	
	aof-load-truncated yes 
	aof-use-rdb-preamble yes 
	lua-time-limit 5000 
	slowlog-max-len 128 
	notify-keyspace-events ""
	
	hash-max-ziplist-entries 512 
	hash-max-ziplist-value 64 
	list-max-ziplist-size -2 
	list-compress-depth 0 
	set-max-intset-entries 512 
	
	zset-max-ziplist-entries 128 
	zset-max-ziplist-value 64 
	
	hll-sparse-max-bytes 3000 
	stream-node-max-bytes 4096 
	stream-node-max-entries 100 
	
	activerehashing yes 
	hz 10 
	
	dynamic-hz yes 
	
	aof-rewrite-incremental-fsync yes 
	rdb-save-incremental-fsync yes
	```


