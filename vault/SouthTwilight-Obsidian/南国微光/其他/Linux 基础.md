#### 基础命令
##### 目录切换命令
1. **cd absolutelyPath/relativePath**：进入指定绝对路径/相对路径下的目录
2. **cd . ./**：返回上级目录
3. **cd /**：切换到系统根目录
4. **cd ~**：切换到用户主目录
##### 目录的操作命令
1. **mkdir directoryName**：在当前目录下创建指定名称的目录
2. **ll**：（即 ls -l）查看目录信息
3. find:
	1. **find .**：列出当前目录及子目录下所有文件和文件夹
	2. **find /absolutelyPath -name “*.type”**：在指定目录下查找指定文件类型文件列表
	3. **find /absolutelyPath -iname "*.type"**：同上，忽略大小写
	4. **find . -name "*.Atype" -o -name "*.Btype"**：当前目录及子目录下查找两种类型
4. **mv oldDirectory newDirectory**：修改目录的名称或移动目录的位置
5. **cp -r oldDirectory newDirectory**：拷贝目录，-r 代表递归拷贝
6. **rm [-rf] directory**：删除目录
##### 文件的操作命令
1. **touch fileName**：创建文件
2. 查看
	1. **cat fileName**：显示最后一屏内容
	2. **more fileName**：显示百分比删除目录，回车下一行， 空格向下一页，q 退出查看
	3. **less fileName**：使用键盘上的 PgUp 和 PgDn 向上/向下翻页，q 结束查看
	4. **head rowNumber fileName**：查看文件的前 rowNumber 行，Ctrl+C 结束
	5. **tail -f -n rowNumber fileName**：查看文件的后 rowNumber 行，Ctrl+C 结束。-f 动态监控
3. 压缩解压
	1. **tar -zcvf zipName filesName/directory**：打包指定文件或指定目录下文件为指定压缩文件名
	2. **tar -zxvf zipName.tar.gz**：解压指定名压缩文件到当前目录
##### 权限操作
1. **修改文件/目录的权限的命令**：**chmod**

#📌 开机自启动脚本
>1. 新建执行脚本
>2. 为脚本添加可执行权限：**chmod +x scriptName**
>3. 将脚本添加到开机启动项里：**chkconfig --add scriptName**
>4. 确定添加成功：**chkconfig --list** ( | grep scriptName)

#### Shell 脚本
##### 变量
1. 命名
	1. 首字母必须字母a-z或A-Z
	2. 不能空格，可用_
	3. 不同于其他编程语言，**等号之间不要有空格**
2. 使用
	1. 变量使用位置使用 **$** 修饰
	2. 可以加{}来标识变量名的范围
	3. 已定义的变量可重新定义（赋值）
```bash
1.1  your_variable='yourname'
1.2  echo $your_variable
1.3  echo $(your_variable)
2.1  for skill in Ada Coffe Action Java; do
		 echo "I am good at ${skill}Script"
	 done
3.1  your_name="tom"
	 echo $your_name
3.2  your_name="john"
	 echo $your_name
```
3. 只读：**使用 readonly 命令将变量只读**，则不可再改变（类似常量）
4. 删除：使用 **unset** 命令删除变量；删除变量后不能再用，而 **unset 不能删除只读变量**
5. 类型
	1. 局部变量：脚本中定义的变量，仅作用于本shell脚本内
	2. 环境变量：所有程序，包括shell启动程序都能访问的环境变量
	3. shell 变量：shell 程序的特殊变量
6. 字符串
	1. string：
	2. 获取字符串长度：使用 # 标识变量长度
	3. 获取子字符串：**_下标从左至右，0开始_**
	4. 查找子字符串：使用 ` 符号
	>**单引号：**单引号''之间的字符原样输出，里面的变量也会失效。其内部不能再有单引号，哪怕转义符号都失效
	>**双引号：**双引号里面可以有变量，可以有转义符号
	
```bash
1. 
	your_name='your name'
	str="Hello ,world ,\"_$your_name\_"! \n"
2. echo ${#str}
3. echo ${str:1:4}
4. echo `expr index "$str" is`  #查找字符i或s的位置
```
7. 数组
	1. 定义：使用 () 表示数组，元素用空格来分割
	2. 读取
	3. 获取数组长度
```bash
1. array=(1 2 3 4 5 6 7)   # 或如下单元素定义方式
   array[0]=1
   array[1]=2
   array[3]=7
2. variable=${array[index]}  
   echo ${variable[@]}   # @ 符号代替 index 表示获取所有元素
3. length=${#array_name[@]}  # 获取元素个数
   length=${#array_name[*]}  # 或者使用 * 通配符
   length=${#array_name[n]}  # 获取数组单个元素的长度
```
8. 注释：使用 # 至于行首，表示该行注释，shell 无多行注释


##### 参数

##### 运算符

##### 流程控制

##### 重定向

