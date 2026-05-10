```shell
1、 以登录数据库服务器
2、 进入Sqlplus控制台，命令：sqlplus /nolog
3、 以系统管理员登录，命令：connect / as sysdba
　　可以合并为：sqlplus sys/密码 as sysdba
4、 启动数据库，命令：startup
5、 如果是关闭数据库，命令：shutdown immediate（shutdown abort）
6、 退出sqlplus控制台，命令：exit
7、 进入监听器控制台，命令：lsnrctl
8、 停掉监听器       命令：stop
9、 启动监听器       命令：start
10、退出监听器控制台，命令：exit
11、重启数据库结束
12、查看数据库监听的状态    lsnrctl status
```