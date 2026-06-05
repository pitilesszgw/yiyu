# iOS 一键启动以渔官网

这个方案分两步：Mac 负责启动官网服务，iPhone/iPad 负责把官网添加到主屏幕。设置好之后，手机桌面点「以渔官网」就能打开。

## 第一次设置

1. 在 Mac 上双击 `一键启动以渔官网-iOS.command`。
2. 等窗口显示 `iPhone/iPad 打开：` 后，复制下面那条 `http://你的Mac地址:5001` 链接。
3. 确保 iPhone/iPad 和这台 Mac 连接同一个 Wi-Fi。
4. 在 iPhone/iPad 的 Safari 里打开这条链接。
5. 点 Safari 底部分享按钮，选择「添加到主屏幕」。
6. 名称填写 `以渔官网`，点「添加」。

## 日常使用

1. 先在 Mac 上双击 `一键启动以渔官网-iOS.command`。
2. 再在 iPhone/iPad 桌面点击「以渔官网」图标。

## 注意

- iPhone/iPad 不能直接运行这个本地 Python 官网服务，所以 Mac 需要保持开机且服务正在运行。
- 如果手机打不开，优先检查 iPhone/iPad 和 Mac 是否在同一个 Wi-Fi。
- 如果 Mac 的 Wi-Fi 地址变化，重新运行启动文件，再用 Safari 打开新的链接并重新添加到主屏幕。
