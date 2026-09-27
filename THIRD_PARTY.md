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

- 封装脚本、网页 GUI、文档：**AGPL-3.0-only**（见 `LICENSE`，与上游 HOMR 对齐，避免衍生作品许可冲突）
- **不含** HOMR 源码与 ONNX 权重；权重由官方 release / `download_models.py` 下载
- **不修改、不重分发**上游仓库内容；`homr_gui/` 由使用者自行克隆

## 公开/分发前合规清单

- [x] 未包含 HOMR / HOMR GUI 源码  
- [x] 未包含 ONNX 权重  
- [x] 未包含受版权保护的总谱扫描  
- [x] 标明上游项目与作者（本文件）  
- [x] 本仓库许可与 HOMR 同为 AGPL-3.0  
- [ ] 若提供**网络服务**：需向使用者提供本仓库完整对应源码（AGPL §13）  
- [ ] README / Release 中保留第三方致谢  

## 原作者权益说明（摘要）

| 不可以 | 可以 |
|--------|------|
| 声称 HOMR 是你写的 | 说明「基于 HOMR，版权归其作者」 |
| 把 HOMR 源码混进本仓后改成 MIT | 独立封装 + 运行时调用上游 |
| 移除上游版权与许可声明 | 在 THIRD_PARTY / LICENSE 中保留归属 |
| 分发含版权的出版谱例图片 | 只用自绘/公版/自制谱例 |

## 版权提示

- 请勿将**受版权保护的总谱扫描件**（商业出版物、电影配乐原谱等）提交进公开仓库
- `examples/` 默认 gitignore
