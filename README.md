# Telegram Group Exporter / Telegram 群组聊天记录导出工具

[English](#english) | [中文](#chinese)

---

<a id="english"></a>
## Telegram Group Exporter (English)

A powerful Python tool based on `Telethon` to batch export chat histories from Telegram groups and channels. It captures complete message details, downloads media files, and generates a beautiful HTML viewer mimicking the native Telegram interface, alongside Excel and JSON reports for further analysis.

### Features
- **Batch Export**: Export multiple groups/channels at once via configuration.
- **Media Download**: Downloads photos, videos, documents, voice notes, and stickers with customizable size limits.
- **Resumable**: Supports resuming exports. It periodically saves messages and skips already downloaded media to prevent data loss.
- **Beautiful HTML Viewer**:
  - Mimics the Telegram desktop UI.
  - Supports Dark/Light mode toggle.
  - Built-in navigation by date.
  - Highlights Top Active Users and Administrators.
- **Excel & JSON Exports**: Generates detailed Excel spreadsheets with statistics and raw JSON data.
- **Async Performance**: Utilizes Python's `asyncio` and `Telethon` for fast API communication.

### Prerequisites
- Python 3.9+
- A Telegram account with API credentials. Get your `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org/).

### Installation

1. Clone this repository or download the source code.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
Instead of modifying Python scripts, the project uses a `config.yaml` file for configuration. A sample is provided in `config.sample.yaml`. Copy it to `config.yaml` and edit the following:
- `api_id`: Your Telegram API ID.
- `api_hash`: Your Telegram API Hash.
- `phone`: Your login phone number (including country code, e.g., `85233334444`).
- `start_date`: Fetch messages starting from this date (e.g., `2025-01-01`).
- `max_media_size_mb`: Limit the maximum size of media to download.
- `video_cover_only`: If set to `true`, only downloads lightweight thumbnails/covers for videos instead of the full video files, significantly saving disk space.

### Usage

There are three ways to use this tool: via **Docker (Recommended)**, **Web UI**, or **Command Line (CLI)**.

#### 1. Docker Deployment (Recommended)
Using Docker is the easiest way to run the Web UI without worrying about Python environments. A `docker-compose.yml` is provided for quick startup.

1. Ensure Docker and Docker Compose are installed.
2. Run the container:
   ```bash
   docker-compose up -d
   ```
3. Open `http://localhost:8000` in your web browser. 
4. The downloaded data will be safely persisted in the `tg_export/` folder on your host machine.

#### 2. Web UI (Local Python)
The Web UI provides a graphical interface to configure parameters, input group links, login to Telegram, and view live export progress.

Start the Web UI server:
```bash
python web_app.py
```
Then open `http://localhost:8000` in your web browser. You can enter your credentials, group links, and start the export directly from there. It also supports downloading the exported files as ZIP archives.

#### 2. Command Line Interface (CLI)

**Step A: Login**
Run the interactive login script to create the session.
```bash
python interactive_login.py
```
*Follow the instructions in the terminal to receive and input your Telegram login code.*

**Step B: Start Exporting**
Create a text file (e.g., `groups.txt`) and paste the group links you want to export (one per line):
```text
https://t.me/example_group_1
https://t.me/example_group_2
```

Run the main script and provide the text file:
```bash
python main.py --links groups.txt
```

### Output Structure
Exports are saved in the configured `tg_export/` directory:
```text
tg_export/
├── group_id_group_name/
│   ├── index.html          # Beautiful HTML Viewer
│   ├── messages.xlsx       # Excel report
│   ├── messages.json       # Raw JSON data
│   ├── group_info.json     # Group metadata
│   └── media/              # Downloaded media files categorized by month
└── export_summary.json     # Summary report for all exported groups
```

---

<a id="chinese"></a>
## Telegram 群组聊天记录导出工具 (中文)

基于 `Telethon` 开发的 Python 工具，能够批量导出 Telegram 群组和频道的完整聊天记录。它不仅可以下载媒体文件，还会生成仿 Telegram 客户端风格的 HTML 阅读页面，以及便于数据分析的 Excel 和 JSON 文件。

### 核心功能
- **批量导出**：通过配置列表，支持一次性批量导出多个群组/频道。
- **媒体文件下载**：自动下载图片、视频、文件、语音和贴纸，支持自定义下载大小限制。
- **断点续传与防丢失**：进度会分批保存，且已下载的媒体文件将被跳过，不怕中途意外中断。
- **美观的 HTML 浏览器**：
  - 仿照 Telegram 桌面端的精美 UI。
  - 支持深色/浅色模式切换。
  - 右侧提供基于日期的快速跳转面板。
  - 智能统计并展示**管理员列表**和**活跃用户排行榜**。
- **多格式输出**：生成包含多个统计 Sheet 的 Excel 表格以及原始 JSON 数据。
- **异步高并发**：采用 `asyncio` 配合 `Telethon`，拉取速度快。

### 环境要求
- Python 3.9 及以上版本。
- 一个 Telegram 账号及其 API 凭据。请在 [my.telegram.org](https://my.telegram.org/) 获取 `api_id` 和 `api_hash`。

### 安装步骤

1. 下载或克隆本项目的源代码。
2. 安装依赖库：
   ```bash
   pip install -r requirements.txt
   ```

### 配置参数
本项目不再将配置写死在代码中，而是使用 `config.yaml`。你可以参考 `config.sample.yaml` 来创建你自己的配置文件：
- `api_id`：你的 Telegram API ID。
- `api_hash`：你的 Telegram API Hash。
- `phone`：用于登录的手机号码（需包含国家区号，如 `85233334444`）。
- `start_date`：拉取消息的起始日期（例如 `2025-01-01`）。
- `max_media_size_mb`：媒体文件下载的体积上限。
- `video_cover_only`：如果设置为 `true`，对于视频将只下载其封面/缩略图，不再下载完整的视频文件，极大节省磁盘空间。

### 使用方法

你可以通过 **Docker（推荐）**、**Web 界面** 或者 **命令行（CLI）** 来使用本工具。

#### 1. Docker 容器部署（推荐）
使用 Docker 是最简单的方式，无需配置 Python 环境，我们提供了 `docker-compose.yml` 方便你一键启动。

1. 确保你的系统已安装 Docker 和 Docker Compose。
2. 启动容器：
   ```bash
   docker-compose up -d
   ```
3. 在浏览器中打开 `http://localhost:8000` 即可开始使用。
4. 所有导出的数据将会安全地保存在你本地的 `tg_export/` 目录中。

#### 2. Web 界面（本地运行）
Web 界面提供了一个直观的操作方式，你可以直接在页面上填写参数、填入群组链接、进行 Telegram 登录认证，以及实时查看导出进度。

启动 Web 服务：
```bash
python web_app.py
```
然后在浏览器中打开 `http://localhost:8000`。你可以直接在此输入验证码完成登录。导出完成后，系统还支持将记录打包成 ZIP 下载。

#### 2. 命令行方式 (CLI)

**步骤 A：首次授权登录**
首次需要运行交互式脚本获取并输入验证码以生成 Session。
```bash
python interactive_login.py
```
*根据终端提示查看你的 Telegram 客户端，获取验证码并输入。*

**步骤 B：开始导出**
创建一个文本文件（例如 `groups.txt`），将你需要导出的群组或频道链接粘贴进去，每行一个：
```text
https://t.me/example_group_1
https://t.me/example_group_2
```

然后运行主程序并指定该文件，脚本将开始自动拉取数据：
```bash
python main.py --links groups.txt
```

### 输出目录结构
所有导出的数据将默认存储在 `tg_export/` 文件夹下：
```text
tg_export/
├── 群组ID_群组名称/
│   ├── index.html          # HTML 聊天记录浏览器
│   ├── messages.xlsx       # Excel 数据及统计报表
│   ├── messages.json       # JSON 原始数据
│   ├── group_info.json     # 群组元数据信息
│   └── media/              # 按月份归档的媒体文件
└── export_summary.json     # 所有群组的导出汇总报告
```

---
