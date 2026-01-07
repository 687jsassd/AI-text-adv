# 低成本AI文字冒险游戏引擎

一个基于AI的沉浸式文字冒险游戏引擎，使用Python开发，支持中文交互，具备完整的角色扮演游戏机制。

## 🎮 项目特色

### 细节更新见更新日志

### 核心功能
- **低廉价格AI驱动叙事**: 使用AI生成动态剧情和选项，平均每轮成本不到1分钱(使用deepseekv3.2模型在100轮时的测试)
- **多样化的选项系统**:普通、检定、门槛三种选项，增加游戏丰富度
- **中文优化**: 专门为中文用户设计的提示词和交互界面
- **角色属性系统**: 六维主角属性，且可变动成长
- **道具管理系统**: 完整的背包系统，支持道具获取、使用和丢弃
- **概率检定机制**: 基于属性的成功概率计算和可视化动画
- **自动存档系统**: 每回合自动保存，支持手动存档/读档
- **无选项-自定义模式**: 完全由玩家主导的行动，配合独特的选项类型修饰带来跌宕体验
- **精心设计提示词下的近自由探索世界**：剧情一般不会明示暗示将主角卷入某场风波，玩家可随心所欲在世界探索生活。
- **Think 主角思考**： 提供主角的思考功能，玩家与主角可通过思考进行交流，思考还可提供一些解释说明甚至攻略指引，提升丰富度
- **简约文字终端界面**: 简介终端界面+颜色标识，辨识度高
- **API支持**: 兼容OpenAI API

### ▲成本低廉：

在v0.1.6的版本下，token消耗有所增加，这是新系统(变量表)的引入导致的，
但斜率下降的趋势没有变化，仍然可控。
1-110轮: 平均token消耗：4169.34 拟合直线: y = 17.4804x + 3199.1726


在v0.1.4的版本下，完善的提示词与良好剧情体验下，中等轮数的表现如下，该新版本相较于下面的旧版本来说，内容更多但效果反而更好：

1-80轮:  平均token消耗: 3589.64  拟合直线: y = 16.0600x + 2939.2057

1-90轮:  平均token消耗: 3602.37  拟合直线: y = 12.0558x + 3053.8292

1-100轮:  平均token消耗: 3632.80  拟合直线: y = 10.4407x + 3105.5442

1-110轮:  平均token消耗: 3690.23  拟合直线: y = 10.7655x + 3092.7401

1-120轮:  平均token消耗: 3709.95  拟合直线: y = 9.2124x + 3152.5987

1-130轮:  平均token消耗: 3766.92  拟合直线: y = 9.6970x + 3131.7689

1-132轮:  平均token消耗: 3786.95  拟合直线: y = 10.1633x + 3111.0978

在轮数148轮时，拟合直线斜率更低达8.93，压缩token消耗效果优秀(见下图)。

![token_consumption_trend](token_consumption_trend.png)


- (旧版) 测试统计(v0.1.1版本)，百轮消耗总token 37W左右，且集合曲线斜率逐渐下降，证明在中小轮数下有较好的压缩，成本控制优秀

1-10轮:  平均token消耗: 2766.90  拟合直线: y = 27.1818x + 2617.4000

1-20轮:  平均token消耗: 2880.55  拟合直线: y = 22.0609x + 2648.9105

1-30轮:  平均token消耗: 3028.40  拟合直线: y = 27.0131x + 2609.6966

1-40轮:  平均token消耗: 3113.68  拟合直线: y = 21.6800x + 2669.2346 

1-50轮:  平均token消耗: 3231.78  拟合直线: y = 22.6622x + 2653.8931

1-60轮:  平均token消耗: 3331.10  拟合直线: y = 21.5156x + 2674.8729 

1-70轮:  平均token消耗: 3404.89  拟合直线: y = 18.9589x + 2731.8447

1-80轮:  平均token消耗: 3489.74  拟合直线: y = 18.3545x + 2746.3797

1-90轮:  平均token消耗: 3594.18  拟合直线: y = 19.1112x + 2724.6160  

1-100轮:  平均token消耗: 3687.30  拟合直线: y = 18.9110x + 2732.2939 

(以上测试均基于单局，由于物品、变量、剧情不同，数据可能不准确。受限于成本，多局测试结果尚待确认)

### 技术亮点

- **模块化架构**: 清晰的代码分离，易于扩展和维护
- **JSON配置驱动**: 所有设置通过配置文件管理，无需修改代码
- **动画效果**: 加载动画、打字机效果、概率检定动画
- **Token统计**: 实时监控API使用情况，优化成本控制
- **历史压缩**: 自动管理游戏历史，防止上下文过长

## 🚀 快速开始

### 环境要求
- Python 3.7+
- 依赖包：`openai`, `json_repair`

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd AI-text-adv
```

2. **安装依赖**
```bash
pip install openai json_repair
```

3. **配置API**
复制 `config/llm_api_config.example.json` 为 `config/llm_api_config.json`，然后填入您的API配置：
```json
{
  "api_providers": {
    "0": {
      "name": "硅基流动",
      "base_url": "https://api.siliconflow.cn/v1",
      "api_key": "your-api-key-here",
      "model": "deepseek-ai/DeepSeek-V3"
    }
  },
  "api_provider_choice": 0
}
```

4. **运行游戏**
```bash
python main.py
```

## ⚙️ 配置说明

### 配置文件

所有配置文件位于 `config/` 目录下：

- **config/config.json**: 游戏设置
  - **ai_settings**: AI参数（max_tokens, temperature等）
  - **preferences**: 玩家偏好设置（色情、暴力、血腥、恐怖程度）
  - **player_settings**: 玩家信息（姓名、背景故事）
  - **custom_prompts**: 自定义附加提示词

- **config/llm_api_config.json**: LLM API 提供商配置
  - **api_providers**: 提供商列表（便于进行密钥、端点、模型统一管理）
  - **api_provider_choice**: 当前使用的提供商ID，可以手动指定使用哪个 LLM

- **config/llm_api_config.example.json**: API配置示例（逐步新增 LLM 提供商）

### 游戏设置

游戏启动后，您可以通过以下方式配置：
1. 首次运行时会进入配置界面(此时若无上述json配置文件，将自动创建范例文件，需要配置后重启读取)
2. 游戏中输入 `config` 命令重新配置
3. 直接编辑JSON配置文件

## 🎯 游戏玩法

### 基本操作

1. **开始游戏**: 运行程序后，根据提示配置角色属性
2. **选择选项**: 输入数字选择剧情选项（1-4）
3. **查看状态**: 使用命令查看游戏状态
4. **保存进度**: 游戏自动保存，也可手动保存
5. **物品操作**：通过inv与opi指令进行完善物品操作
6. **自定义行动**：通过csmode指令进入完全自定义行动模式，或者使用custom指令单轮自定义行动

### 可用命令

| 命令 | 功能 | 说明 |
|------|------|------|
| `exit` | 退出游戏 |  |
| `inv` | 查看道具 | 显示当前拥有的所有道具 |
| `attr` | 显示属性 | 查看角色六维属性 |
| `summary` | 查看历史摘要 |  |
| `save` | 手动保存 | （每轮自动存档，自动存档只保留最近10轮）、手动永久保存 |
| `load` | 读取 | （游戏会在启动时自动读取自动存档） |
| `new` | 新游戏 | 重新开始新游戏 |
| `config` | 配置游戏 |  |
| `custom` | 自定义行动 | 当不采用AI生成的选项时，可输入自定义的行动描述 |
| `opi` | 道具操作 | 添加、删除、重命名、重描述、与仓库间转移等物品操作|
| `think` | 思考 | 玩家输入疑问，主角进行思考，可以作为剧情补充或者对玩家的解惑，在本轮剧情内完成 |
| `ana_token` | Token统计 | 查看API使用统计 |
| `help` | 显示帮助 |  |
| `csmode` | 切换完全自定义行动模式 |  |
| `show_init_resp` | 切换显示AI原始回复和token详细信息 | 可切换开关，调试用 |
| `vars` | 查看变量 |  |
| `setvar` | 添加/设定变量 |  |
| `delvar` | 删除变量 |  |

### 游戏机制

#### 属性系统
- 力、敏、智、感、魅、运共六维属性

#### 概率检定
- **普通选项**: 直接执行
- **检定选项**: 基于属性和随机值进行判定是否成功
- **门槛选项**: 需要达到属性门槛才能选择(成功)

#### 形势值
- 范围：-10（绝对劣势）到 10（绝对优势）
- 影响检定成功率和剧情发展
- 根据剧情事件动态变化

## 📁 项目结构

```
AI-game-test/
├── main.py              # 主程序入口，游戏循环和UI
├── game_engine.py       # 游戏引擎核心逻辑
├── config.py            # 配置管理系统
├── prompt_manager.py    # 提示词管理
├── animes.py            # 动画效果工具
├── config/              # 配置文件目录
│   ├── config.json              # 游戏设置
│   ├── llm_api_config.json      # API提供商配置
│   └── llm_api_config.example.json  # API配置示例
├── saves/               # 存档目录
├── logs/                # 游戏日志
└── __pycache__/         # Python缓存
```

## 🔧 开发指南

### 扩展新功能

1. **添加新命令**: 在 `main.py` 的 `get_user_input_and_go` 函数中添加命令处理
2. **修改游戏机制**: 编辑 `game_engine.py` 中的相关方法
3. **自定义提示词**: 修改 `prompt_manager.py` 中的提示词模板

### API响应格式

在普通模式下(含完整选项),AI响应必须遵循以下JSON格式(部分字段在某些情况下无)：
```json
{
  "description": "场景描述",
  "summary": "10-25字摘要",
  "options": [
    {
      "id": 1,
      "text": "选项文本",
      "type": "normal|check|must",
      "main_factor": "属性名",
      "difficulty": "数值",
      "base_probability": "概率",
      "next_preview": "预览文本"
    }
  ],
  "commands": [
    {
      "command": "add_item|remove_item|change_attribute|change_situation_value|gameover",
      "value": "指令值"
    }
  ]
}
```

## 🎨 视觉效果

- **颜色编码**: 不同游戏元素使用不同颜色标识
  - 红色: 危险/失败
  - 绿色: 成功/增益
  - 黄色: 警告/中性
  - 蓝色: 信息/属性

- **动画效果**:
  - 加载动画（旋转、点状、进度条）
  - 打字机效果的文字输出
  - 概率检定的可视化动画

## 📊 性能优化

### Token管理
- 实时显示Token使用统计
- 自动压缩历史记录防止上下文过长
- 支持Token消耗分析功能(使用ana_token指令进行分析)

### 存档优化
- 自动存档管理（保留每局的最近10个自动存档与所有手动存档）
- 游戏ID标识，支持多游戏并行
- 存档文件包含完整游戏状态

## 🐛 故障排除

### 常见问题

1. **API连接失败**
   - 检查 `config/llm_api_config.json` 中的密钥、端点、模型是否正确

2. **JSON解析错误**
   - AI响应格式不符合要求
   - 检查提示词模板是否完整

3. **游戏无法保存**
   - 检查 `saves/` 目录权限
   - 确认磁盘空间充足

### 调试命令

游戏内置调试命令：
- `show_init_resp`: 显示AI原始响应
- `fix_item_name`: 修复道具名错误
- `ana_token`: 分析Token使用模式
- `opi`下`*add`等指令：添加物品、修改物品、移除物品等
- `setvar`: 添加/设定变量
- `delvar`: 删除变量


## 打包为exe文件的说明

1. 安装pyinstaller：`pip install pyinstaller`
2. 建议打包命令: `pyinstaller --noconfirm --clean --onedir --icon ".\icon.ico" --add-data ".\config;config/" --add-data ".\logs;logs/" --add-data ".\saves;saves/" --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module tkinter --exclude-module numpy --exclude-module pandas --exclude-module scipy --exclude-module matplotlib ".\main.py"`
  * 查阅main.spec 以了解详细配置
3. 在`dist/`目录下找到生成的exe文件

## token分析工具的使用说明
1. 安装matplotlib与numpy:`pip install matplotlib numpy`
2. 正常进行游戏，找到saves目录下游戏ID文件夹中最新存档文件。
3. 找到该json文件中的token_consumes字段(通常在最下方),将其复制到tools/ana_tokens.py中的tokens变量中。
4. 运行ana_tokens.py,即可分析token消耗趋势。

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

### 开发规范
- 添加适当的注释
- 测试新功能确保兼容性

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 🙏 致谢

感谢所有AI模型提供商的支持，以及开源社区的贡献。
感谢returnToInnocence 对项目的贡献，尤其是对llm配置相关json的优化。


## TODO NEXT

√ 添加总结摘要时附带清理旧、无用变量或物品的机制，减缓token消耗增加。
重构项目代码
GUI开发
(Long run)加入并完善NPC记忆系统，并尝试获得较好效益

---

**开始您的AI文字冒险之旅吧！** 🎮✨