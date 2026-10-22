# 小游戏 UI 切图 · game-ui-slicing

给 Codex 一张小游戏效果图，按流程拆成可复用的 PNG：**底板去字、文字与数字分离、透明图标、分类命名、逐图检查、预览与 ZIP 打包**。

默认只交付图片，不导入 Unity，不生成 Prefab，不修改游戏工程。该技能不依赖 Image-To-UI 或 UnityAgentBridge。

## 安装与使用

把本仓库放入 Codex 的个人技能目录，目录名为 `game-ui-slicing`。

Windows PowerShell：

```powershell
git clone https://github.com/shenliang34/game_ui_slice.git "$env:USERPROFILE/.codex/skills/game-ui-slicing"
```

macOS / Linux：

```sh
git clone https://github.com/shenliang34/game_ui_slice.git ~/.codex/skills/game-ui-slicing
```

已有同名技能时先保留已有目录，避免覆盖。若设置了自定义 CODEX_HOME，使用该目录下的 `skills/game-ui-slicing`。

附上效果图，对 Codex 说：

> 使用 $game-ui-slicing 按这个流程切图，文字数字与底图分离，输出 PNG、预览和 ZIP，不导入 Unity。

也可以说“按上次方式切图”。技能详细规则见 [SKILL.md](SKILL.md)。

## 工作流程

1. 检查原图分辨率，辨认背景、Logo、面板、方块、按钮、图标、数字和文案。
2. 缺少分层源文件时，调用可用的 imagegen 工具去字、补绘、分层和透明抠图。
3. 检查每张生成图的实际宽高与位置，人工测量裁框，编写 `slice_plan.json`。
4. 使用辅助脚本完成确定性裁切、透明留边、预览及 ZIP 打包。
5. 逐图检查漏字、边缘底色、裁断角标、数字字形和透明通道，修正后交付。

imagegen 负责语义编辑；Python 脚本不包含生成模型，不会独立理解效果图或自动完成去字。生成工具需要在使用该技能的 Codex 环境中可用。

## 资源组织

```text
Exports/<名称>UI/
  background/   干净背景
  panels/       空棋盘、状态栏、提示条
  tiles/        无数字底块
  buttons/      无文案/操作图标的按钮底板
  icons/        独立操作与状态图标
  numbers/      独立数字
  labels/       独立文案
  logo/         独立美术字
  slices.json
  CONTACT_SHEET.jpg
  validation.json
  README.md
Exports/<名称>UI.zip
```

分类按当前图像实际内容创建，不预设切图数量。同款资源去重；含图标的固定组合条会明确标注，不能按空底板任意拉伸。纯底板可附九宫格边框建议。

## 独立运行打包脚本

需要 Python 和 Pillow：

```sh
python -m pip install -r requirements.txt
python scripts/package_slices.py --plan /path/to/slice_plan.json --output /path/to/new-output
```

计划格式、坐标约定及可选蒙版/留边见 [references/slice-plan.md](references/slice-plan.md)。图层提示与常见问题见 [references/layer-prompts.md](references/layer-prompts.md)。

脚本检查源尺寸、裁框边界、透明通道、九宫格边框、输出路径与 ZIP 完整性；已有非空输出及同名 ZIP 会被保留。自动检查通过仍需要人工视觉审查。

## 验证

```sh
python -m unittest discover -s tests -v
```

测试使用合成图，不需要模型调用、密钥、Unity 或用户效果图。覆盖裁切与透明保留、蒙版、尺寸/越界检测、输出路径、重复文件、错误边框与已有文件保护。

## 范围与限制

平面图不能无损恢复被文字遮挡的像素。AI 补绘可能改变形状、高光和阴影；生成图的实际尺寸与位置也可能变化，必须复核。数字与文字只覆盖已提供字形，动态内容适合后续使用引擎文本。

仓库只包含技能说明和工具，没有上传任何用户效果图、商业素材、游戏工程、账号凭据或本机运行日志。
