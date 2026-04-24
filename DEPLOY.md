# 操作系统智能代理 - 部署指南

本项目原生支持基于 Linux 的各类主流前沿发行版本，目前针对 **Ubuntu**, **openEuler** (欧拉操作系统), 与 **Rocky Linux** 提供了最佳环境适配。

---

## 目录

- [环境要求](#环境要求)
- [支持平台部署说明](#支持平台部署说明)
  - [Ubuntu 部署](#1-ubuntu-部署)
  - [openEuler 部署](#2-openeuler-部署)
  - [Rocky Linux 部署](#3-rocky-linux-部署)
- [配置 API 密钥](#配置-api-密钥)
- [启动服务 (Web 模式)](#启动服务)
- [测试与演示场景](#测试与演示场景)
- [故障排查](#故障排查)

---

## 环境要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.10+ | 推荐 3.12 |
| 内存 | 2 GB | 用于运行 API 调用网络栈及服务后台等 |
| 磁盘空间 | 500 MB | 项目主文件夹 + Python 虚拟环境依赖 |
| 网络 | 互联网访问 | 用于外部大模型接口（例如 MiniMax 等） |

---

## 支持平台部署说明

针对不同 Linux 操作系统平台的网络环境和基础系统包管理机制，部署操作略有不同：

### 1. Ubuntu 部署

**1.1 安装基础依赖**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl git
```

**1.2 克隆项目**
```bash
cd ~
git clone https://github.com/hthreeh/CJB-AI-HACK2026.git langgraph_os_agent
cd langgraph_os_agent
```

**1.3 环境配置**
使用源码中提供的 `./start_web_9600.sh` 脚本可自动创建并进入虚拟环境安装依赖。如需手动安装：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 2. openEuler 部署

openEuler 默认使用 `dnf` 作为包管理器，具备良好的国产硬件生态系统兼容性。

**2.1 安装基础依赖**
```bash
sudo dnf check-update
sudo dnf install -y python3 python3-pip git curl
```

**2.2 克隆项目**
```bash
cd ~
git clone https://github.com/hthreeh/CJB-AI-HACK2026.git langgraph_os_agent
cd langgraph_os_agent
```

**2.3 环境配置**
绝大部分 openEuler 版本可直接使用原生的 venv 环境管理打包：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 3. Rocky Linux 部署

作为企业级操作系统的优质选择，Rocky Linux 的部署方式与绝大部分 CentOS/RHEL 生态链兼容。

**3.1 安装基础依赖**
```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git curl
```

**3.2 克隆项目**
```bash
cd ~
git clone https://github.com/hthreeh/CJB-AI-HACK2026.git langgraph_os_agent
cd langgraph_os_agent
```

**3.3 环境配置**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 配置 API 密钥

请确保必须在项目根目录下通过模版或者手动新建 `.env` 文件：

```bash
cp .env.example .env
nano .env
```

配置必须包含的授权变量（此处以 MiniMax API 填写示例）：

```
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=MiniMax-M2.7
OPENAI_BASE_URL=https://api.minimaxi.com/v1
```

> **安全注意：API Key 属于极高密级凭证，请妥善于本地保管，切勿随着 Git 仓库进行 push 提交！**

---

## 启动服务

### 使用一键自动化脚本（极度推荐）

我们更新了更为强健的服务启停脚本。其内嵌了虚拟环境探测修复处理、网络端口保护校验等前置逻辑。服务默认采用 **9600** 端口。

**首次/常规 启动服务**：
```bash
chmod +x start_web_9600.sh
./start_web_9600.sh
```

**快速重启服务**（当您在远端修改了部分源代码或环境变量后）：
```bash
chmod +x restart_web_9600.sh
./restart_web_9600.sh
```

### 极客 CLI 交互测试模式

如果在排障过程中希望跨越 Web 端，直接于 Shell 底座进行交互反馈，可通过激活虚拟环境使用原生启动命令：

```bash
source venv/bin/activate
python src/main.py
```

---

## 测试与演示场景

前台服务运行后，在浏览器中打开网址：**http://<部署环境IP>:9600**。

### 基础系统排查探测

| 序号 | 测试自然语言输入 | 后台对应的行为预期 | 实际映射命令（智能衍生） |
|------|---------|---------|---------|
| 1 | `查询磁盘使用情况` | 直接返回系统磁盘容量总体详情 | `df -h` |
| 2 | `查看系统信息` | 返回 OS 详细版本及关键内核系统信息 | `uname -a && cat /etc/os-release` |
| 3 | `查看目前占用CPU最高的进程` | 针对系统进行 CPU 队列排序筛选抓取 | 灵活采用 `ps aux --sort=-%cpu` |
| 4 | `查看9600端口` | 验证服务进程的承载或网络使用情况 | `ss -tuln` 等 |

### 复杂系统逻辑与安防红绿灯

| 序号 | 测试自然语言输入 | 行为预期反馈 | 评分评估项 |
|------|---------|---------|--------|
| 5 | `创建一个名为 dev_test 的用户` | 系统接管后自动分配家目录并初始化账户相关文件 | 系统用户基础自动化管理能力 |
| 6 | `先新建 test_opt 账户，然后部署默认工作目录` | 被自主拆分为多个顺序和依赖关系的微服务任务进行依次处理 | **多模块连续任务序列编排** |
| 7 | `删除根目录 /` 抑或指令提及 `断电关机` | 触碰底线！在指令分析阶段瞬时被代理硬编码拦截阻断。 | **代码级最高优先级操作隔离** |
| 8 | `我现在本地的 8080 端口好像不通，帮忙诊治一下` | 大模型代理将自主生成涉及排查网络、相关守护进程以及防火墙组的联级脚本 | **复杂模糊意图排查与多维度分析** |

---

## 故障排查

### 问题 1：启动时立刻报错 `ModuleNotFoundError`
* **根因**：当前用户的 Linux 环境尚未开启 Python 的独立隔离运行区（即 venv 失效或未启动）。
* **对策**：优先建议使用 `./start_web_9600.sh` 脚本，内部已加固了依赖环境重装策略。手动修复请执行 `source venv/bin/activate && pip install -r requirements.txt`。

### 问题 2：服务启动提示成功，但网络页面无论如何无法打开
* 必须排查对应 Linux 宿主系统的防火墙端口放通状态！
* **Ubuntu 系统**：可用 `sudo ufw allow 9600/tcp`
* **openEuler / Rocky Linux**：系统默认采用强控型 firewalld，需手动放通策略安全组：
  ```bash
  sudo firewall-cmd --zone=public --add-port=9600/tcp --permanent
  sudo firewall-cmd --reload
  ```

### 问题 3：大模型完全无响应，或者出现鉴权 401 报错
* 请仔细检查 `.env` 文件。**核心常见坑点**：`OPENAI_BASE_URL` 的路径 URL 尾部，不要带有遗留的 `/`（斜杠）字符。

---

## 清理系统内部运行时杂数据

如果您作为开发者，遇到需要**进行恢复原厂环境**、**清理执行遗留脏数据**的情况：

```bash
# 彻底移除前端会话保存日志记录
rm -rf sessions/
# 删除 Agent 后台追踪与运行审计库
rm -f audit.db
# 清除 9600 后台服务的暂存进程锁机制
rm -f web_9600.log web_9600.pid

# [慎用] 剔除整个当前虚拟解析器环境，以求重新部署隔离安装
rm -rf venv/
```
