# 下载 / Releases

当前正式版本：[v0.5.2](https://github.com/kadevin/ilab-gpt-conjure/releases/tag/v0.5.2)

## 版本说明

当前版本：`v0.5.2`。这个版本提供 Windows x64、macOS Apple Silicon、macOS Intel 三种免安装一键包；下载对应平台的 zip 后解压即可启动本地 WebUI，并可手动运行包内更新脚本升级到后续版本。

本版重点：这一版主要发布多语言界面和输入图像画布编辑能力。WebUI 增加语言设置下拉菜单和多语言字典，输入图片编辑器升级为可插入多张输入图、调整画布范围、缩放旋转和局部擦除的多图层编辑器；同时修复任务状态同步和公用图库窄卡片操作区溢出问题。

本版详情：

- 多语言界面：语言设置改为下拉菜单，第一次启动会按浏览器语言自动选择，手动选择后即时生效并记住偏好；已加入简体中文、正體中文、繁体中文、日本語、한국어、English、Español、Português、Français、Deutsch、Русский、Italiano 和 हिन्दी。
- 语言入口可找回：语言设置放在独立 Tab，Tab 标题保留当前语言文案和 English 提示，避免用户切错语言后找不到入口；右上角中英文切换按钮已移除。
- 输入图像画布编辑：编辑输入图片时可插入输入框里的其他一张或多张图片，进行多图组合、选择移动、缩放旋转、局部擦除和图层排序，编辑后保存为一张输入图。
- 画布范围控制：新增“首图范围 / 适应图层”画布范围选择；既可以保持第一张输入图的尺寸，也可以按全部图层自动扩展画布，适合把多张参考图拼成一张更大的编辑输入图。
- 图层和变换体验：图层列表显示真实缩略图；图片变换默认锁定长宽比例，按住 Shift 才自由变换；箭头和擦除等工具改进实时反馈，减少绘制延迟感和错位感。
- 公用图库溢出修复：合入 PR #3 的窄宽度卡片修复，图库卡片、标题、说明和操作按钮都允许收缩并使用省略显示，极窄容器下操作按钮自动变为单列，避免抽屉变窄时按钮挤出卡片。
- 任务状态同步：修复已生成结果但左侧任务列表仍显示“生成中”的状态不同步问题，任务状态、输出槽位和历史详情以真实可显示结果为准更新。
- 前端依赖与测试：图层编辑器使用 Konva，`package-lock.json` 锁定对应 npm 依赖；前端资源版本提升到 `runtime-368`，静态测试覆盖多语言字典、语言下拉菜单、输入图像画布范围、图层缩略图、图库卡片窄宽度按钮溢出和任务状态同步，降低后续回归风险。

## 免安装一键包

| 平台 | 适用设备 | 下载 | SHA256 |
| --- | --- | --- | --- |
| Windows x64 | Windows 10/11 x64 | [ilab-gpt-conjure_windows_portable_x64_0.5.2.zip](https://github.com/kadevin/ilab-gpt-conjure/releases/download/v0.5.2/ilab-gpt-conjure_windows_portable_x64_0.5.2.zip) | [sha256](https://github.com/kadevin/ilab-gpt-conjure/releases/download/v0.5.2/ilab-gpt-conjure_windows_portable_x64_0.5.2.zip.sha256.txt) |
| macOS Apple Silicon | M1/M2/M3/M4 | [ilab-gpt-conjure_macos_portable_arm64_0.5.2.zip](https://github.com/kadevin/ilab-gpt-conjure/releases/download/v0.5.2/ilab-gpt-conjure_macos_portable_arm64_0.5.2.zip) | [sha256](https://github.com/kadevin/ilab-gpt-conjure/releases/download/v0.5.2/ilab-gpt-conjure_macos_portable_arm64_0.5.2.zip.sha256.txt) |
| macOS Intel | Intel x64 | [ilab-gpt-conjure_macos_portable_x64_0.5.2.zip](https://github.com/kadevin/ilab-gpt-conjure/releases/download/v0.5.2/ilab-gpt-conjure_macos_portable_x64_0.5.2.zip) | [sha256](https://github.com/kadevin/ilab-gpt-conjure/releases/download/v0.5.2/ilab-gpt-conjure_macos_portable_x64_0.5.2.zip.sha256.txt) |

使用方式：

1. 下载对应平台的 zip。
2. 解压到普通用户目录，不要放在系统保护目录。
3. Windows 双击 `Start WebUI Portable.bat`；macOS 双击
   `Start WebUI Portable.command`。
4. 如果浏览器没有自动打开，访问 `http://127.0.0.1:8787/`。

更新已经解压的一键包时，先关闭 WebUI 服务窗口，然后运行 Windows 的
`Update WebUI Portable.bat` 或 macOS 的 `Update WebUI Portable.command`。
启动脚本不会访问 GitHub，也不会自动更新文件。更新脚本会下载当前平台对应的最新
GitHub Release 资产，执行前显示所选资产和 SHA256 文件，校验 SHA256，只替换一键包目录内由程序管理的文件，保留本地 `data/`，并把被替换文件备份到 `.backup/`。

macOS 包是未签名的 portable zip，不是已签名 `.app` 或 notarized DMG。
启动脚本会尝试在启动前移除当前解压目录内的 quarantine 标记。如果 macOS
仍然拦截启动脚本，可以右键或 Control-click `Start WebUI Portable.command`，
选择 Open，并在系统安全提示中再次确认。也可以对解压目录执行：

```bash
xattr -dr com.apple.quarantine /path/to/ilab-gpt-conjure_macos_portable_arm64
# 或：
xattr -dr com.apple.quarantine /path/to/ilab-gpt-conjure_macos_portable_x64
```

一键包内的 `data/` 目录会保存本地设置、公用图库、输入图、输出图、任务数据库和日志。
不要把这些本地数据、API key 或 OAuth 文件提交到 Git。
