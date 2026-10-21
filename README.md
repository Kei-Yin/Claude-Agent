这是一个仿制、学习Claude Code的一个项目，首先搭建一个0.01版本，然后期望这个0.01版本，能自我进化到0.1版本。

This is a project that imitates and studies Claude Code. First, a version 0.01 will be built, and it is expected that this version 0.01 can evolve to version 0.1 on its own.

## 运行 Python 命令行版（Windows）

在 Anaconda Prompt 中执行：

```bat
conda activate LLMs
cd /d D:\HKU\Project\MyClaude
python -m pip install -r requirements.txt
python -X utf8 -m src.myclaude
```

也可以运行 `pip_install.bat` 安装到 `LLMs`，再运行 `start.bat` 启动。
首次克隆时，先复制 `config/model_key.example.yaml` 为 `config/model_key.yaml`，再填写自己的密钥；本地密钥文件不提交到 Git。
`config/model_key.yaml` 的 `main_model.provider` 选择主模型，对应 provider 需要有效的 API Key、base URL 和模型名。
代理沿用当前终端的 `http_proxy` / `https_proxy` 环境变量，启动脚本不再写入占位代理。
配置中的相对目录会自动以项目根目录解析，移动项目后不需要批量修改绝对路径。

不调用模型的回归检查：

```bat
python -X utf8 -m unittest src.utility.test_runtime_regressions -v
```

`wdbuddy/` 是独立的 Electron 桌面应用，启动方式见其 README；不由 Python CLI 启动。
