1、初始化推送一个项目：
```git
cd existing_folder # 文件夹路径
git init 
git remote add origin https://gitcode.net/han12020121/groovy_demo.git # 远程仓库的项目地址
git add . 
git commit -m "Initial commit" 
git push -u origin master
```
2、git commit 
	提交版本记录到本地暂存区
	git commit -m "info" 提交到暂存区时加上信息
3、git branch
	创建一个分支，一般使用：git branch 分支名字
	将分支强制指向某次提交：git branch -f 分支名字 HEAD~3 (将分支强制指向 HEAD 的第 3 级父提交)
4、git merge
	在当前分支，合并其他分支内容到当前分支，一般使用：git merge 其他分支名字
5、git rebase
	第二种合并分支的方法是 `git rebase`。Rebase 实际上就是取出一系列的提交记录，“复制”它们，然后在另外一个地方逐个的放下去。Rebase 的优势就是可以创造更线性的提交历史，这听上去有些难以理解。如果只允许使用 Rebase 的话，代码库的提交历史将会变得异常清晰。
	一般使用：git rebase 其他分支名字 （<font color="#f79646">会将当前分支换到其他分支的最顶端</font>）
6、git checkout 
	git checkout可以跟分支名，切换到目标分支，比如：git checkout 其他分支名
	git checkout可以跟HEAD哈希值，可以分离head指针到该次提交，比如：git checkout 6d884ca7
7、相对引用
	通过提交哈希值去checkout很不方便，可以使用相对引用基于一个易于记忆的地方开始计算。
	- 使用 `^` 向上移动 1 个提交记录
	- 使用 `~<num>` 向上移动多个提交记录，如 `~3`
	比如：git checkout main^ 就是切换到main的父节点
	git checkout HEAD^ 以HEAD作为参照，在提交树上向上移动几次
8、git reset和git revert 【撤销变更】
	c0 -> c1 -> c2 <-HEAD（当前HEAD指向c2提交）
	`git reset` 通过把分支记录回退几个提交记录来实现撤销改动。你可以将这想象成“改写历史”。`git reset` 向上移动分支，原来指向的提交记录就跟从来没有提交过一样。在git reset HEAD~1后， `C2` 所做的变更还在，但是处于未加入暂存区状态。（这是本地暂存区的修改）
	git revert HEAD后，在我们要撤销的提交记录后面居然多了一个新提交！这是因为新提交记录 `C2'` 引入了**更改** —— 这些更改刚好是用来撤销 `C2` 这个提交的。也就是说 `C2'` 的状态与 `C1` 是相同的。revert 之后就可以把你的更改推送到远程仓库与别人分享啦。（这是可以push的修改）
9、git cherry-pick【整理提交记录】
	命令形式为:- `git cherry-pick <提交号>...`
	如果你想将一些提交复制到当前所在的位置（`HEAD`）下面的话， Cherry-pick 是最直接的方式了。
	![[Pasted image 20240228162421.png]]
	![[Pasted image 20240228162509.png]]
	简单就是，在当前HEAD节点，使用git cherry-pick把其他的提交复制过来
10、git rebase -i 【整理提交记录，可视化】
	Git 会打开一个 UI 界面并列出将要被复制到目标分支的备选提交记录，当 rebase UI界面打开时, 你能做3件事:
	- 调整提交记录的顺序（通过鼠标拖放来完成）
	- 删除你不想要的提交（通过切换 `pick` 的状态来完成，关闭就意味着你不想要这个提交记录）
	- 合并提交。
	使用示例：git rebase -i HEAD~4 （对当前指针前4个提交进行操作】
11、git tag
	用法：git tag 标签内容 提交哈希值，也可以使用git tag 标签内容，这是该tag指向HEAD所在位置
12、git fetch
	拉取远程分支数据和状态，不会更改你的本地。
	语法是：`git fetch <remote> <place>`
	语法和git push类似，但是fetch是下载方向，而push是上传方向
	`git fetch origin foo`
	Git 会到远程仓库的 `foo` 分支上，然后获取所有本地不存在的提交，放到本地的 `o/foo` 上。
	
13、git pull
	是 git fetch 和 git merge 的结合
14、git push
	语法是：`git push <remote> <place>`
	`git push origin main`
	把这个命令翻译过来就是：_切到本地仓库中的“main”分支，获取所有的提交，再到远程仓库“origin”中找到“main”分支，将远程仓库中没有的提交记录都添加上去，搞定之后告诉我。
	我们通过“place”参数来告诉 Git 提交记录来自于 main, 要推送到远程仓库中的 main。它实际就是要同步的两个仓库的位置。
	要同时为源和目的地指定 `<place>` 的话，只需要用冒号 `:` 将二者连起来就可以了：`git push origin <source>:<destination>`
15、通过远程分支检出一个新的分支，跟踪远程分支
	git checkout -b totallyNotMain o/main
	就可以创建一个名为 `totallyNotMain` 的分支，它跟踪远程分支 `o/main`。
16、设置远程追踪分支2
	git branch -u o/main foo
	这样 `foo` 就会跟踪 `o/main` 了。如果当前就在 foo 分支上, 还可以省略 foo：
	`git branch -u o/main`
17、古怪的`<source>`
	Git 有两种关于 `<source>` 的用法是比较诡异的，即你可以在 git push 或 git fetch 时不指定任何 `source`，方法就是仅保留冒号和 destination 部分，source 部分留空。
	-`git push origin :side` 
	-`git fetch origin :bugFix`  
	如果 push 空 到远程仓库会如何呢？它会删除远程仓库中的分支！
	如果 fetch 空 到本地，会在本地创建一个新分支。
	source和destination可以以流向为理解，push时是从本地流向远程，所以是 本地：远程 ，fetch时是远程流向本地，所以是 远程：本地
