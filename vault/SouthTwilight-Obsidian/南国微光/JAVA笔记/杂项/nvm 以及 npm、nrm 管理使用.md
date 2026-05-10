#### 一、卸载node
如果已经安装了node，那么在安装nvm之前，需要先卸载node，如果没有安装可以直接跳过这一步到下一步了。
删除前可查当前使用的node版本，方便后续决定使用哪个版本的node。

- 控制面板 -> 卸载程序 -> 卸载nodejs
- 为了确保彻底删除node，看下node安装目录中还有没有node文件夹，有的话一起删除。
- 删除以下文件夹（如果存在的话）
- C:\Program Files (x86)\Nodejs
- C:\Program Files\Nodejs
- C:\Users{User}\AppData\Roaming\npm
- C:\Users{User}\AppData\Roaming\npm-cache
- 删除C:\Users\用户名 下的 .npmrc文件以及 .yarnrc 文件
- 环境变量中npm、node的所有相关统统删掉
#### 三、nvm安装
1. [官网](https://github.com/coreybutler/nvm-windows/releases)下载 nvm 包
2. 安装 nvm-setup.exe (Windows)
3. 配置路径和下载镜像
4. 检查nvm版本以及是否安装完成，命令提示符执行命令 ‘nvm -v’

#### 四、使用nvm安装node版本
1. ==nvm list available== 查询可插入版本号，LST表示可插入稳定版本
2. 安装指定node.js版本，==nvm install 版本号==
3. 切换node版本，==nvm use 版本号==
4. 安装完成后可以分别输入命令行 ==node -v== 和 ==npm -v==，检验node.js以及对应npm是否安装成功
5. ==nvm list== 查看当前已安装的node.js版本，带 * 号的是正在使用的
6. 删除某 node.js 版本：==nvm uninstall 版本号==

#### 五、修改npm默认镜像源为淘宝镜像
1. 修改npm镜像源为淘宝镜像，加快npm包的下载速度，减少发生连接错误和超时的概率
>npm config set registry https://registry.npmmirror.com

2. 检查是否设置淘宝镜像成功
> npm config get registry


#### 六、使用 nrm 来管理 npm 源
我们可以使用 nrm 来管理 npm 源，特别是当需要在不同的网络环境之间切换时，它可以提供更好的包管理体验。
>nrm（npm registry manager）是一个用于管理和切换 npm 源的命令行工具。它允许您在不同的 npm 源之间进行切换，以加快包的下载速度，或者解决特定源无法访问的问题。nrm 提供了一组命令，可以列出可用的 npm 源、添加新源、测试源的响应速度，并切换当前使用的源。
##### 常见的 nrm 命令
1. 列出可用的源：当前配置的所有可用 npm 源以及它们的名称和 URL
>	nrm ls
1. 切换源：将当前的 npm 源切换为指定的源。可以使用源的名称或 URL 作为 参数
>	nrm use <registry>
3. 添加源：添加一个新的 npm 源并指定其名称和 URL
>	nrm add <registry> <url>
4. 删除源：删除指定的 npm 源，需要提供源的名称或 URL 作为 参数
> 	nrm del <registry>
5. 测试源的速度：测试指定源的响应速度，并显示测试结果
> 	nrm test <registry>
6. 显示当前使用的源：当前正在使用的 npm 源的名称和 URL
> 	nrm current


