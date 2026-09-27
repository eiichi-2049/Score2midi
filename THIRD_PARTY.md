# 第三方组件与许可

本项目是 **本地封装 / 工具链**，OMR 识别能力来自上游开源项目。**分发或提供网络服务前请自行核对各许可条款。**

## HOMR（核心识别引擎）

- 项目：https://github.com/liebharc/homr
- 作者：Christian Liebhardt 等
- 许可：**AGPL-3.0**
- 用途：乐谱图片 → MusicXML

## HOMR GUI（图形封装，含 `homr` 包布局）

- 项目：https://github.com/Quackone/homr_gui
- 许可：**AGPL-3.0**
- 用途：本仓库 `homr_gui/` 目录的来源（运行时放置，不入库）

## oemer（备选 / 血缘）

- 项目：https://github.com/BreezeWhite/oemer
- 许可：MIT
- 说明：HOMR 部分思路与分割模型与之相关

## RapidOCR / ONNX Runtime / OpenCV / music21 等

- 由 `requirements.txt` 安装，遵守各自上游许可（Apache-2.0 / BSD / LGPL 等）

## 本仓库

- 封装脚本、网页 GUI、文档可按仓库根目录 `LICENSE`（若添加）授权
- **不含** HOMR 源码与 ONNX 权重；权重由官方 release 下载

## 版权提示

- 请勿将**受版权保护的总谱扫描件**（商业出版物、电影配乐原谱等）提交进公开仓库
- `examples/` 默认 gitignore
