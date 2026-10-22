# 切片计划

路径相对于计划文件，输入允许绝对路径。输出为安全的相对 PNG 路径。矩形为原生像素 `[left,top,right,bottom]`，右/下边界不包含在内；不是 x/y/width/height。

```json
{
  "name": "ExampleUI",
  "referenceResolution": [941, 1672],
  "sources": {
    "blank": {"path": "Source/ui-blank.png", "size": [941,1672]},
    "parts": {"path": "Source/parts.png", "size": [981,1604]}
  },
  "sprites": [
    {"path":"buttons/button_blue.png", "source":"blank", "rect":[336,1255,605,1372], "border":{"left":40,"bottom":39,"right":40,"top":32}, "note":"无字底板，左右导航共用"},
    {"path":"icons/arrow_left.png", "source":"parts", "rect":[425,1335,540,1453], "trim":true, "note":"独立透明箭头"}
  ],
  "texts": {"previous":"上一关", "next":"下一关"},
  "limits": ["平面图补绘存在细节差异"]
}
```

可选字段：

- `role: "background"`：允许不透明，其他素材默认应有透明像素。
- `fixedSize: true`：固定组合图，不得同时指定非零 border。
- `trim: true`：按已有 Alpha 裁去透明边；结果记录 trimOffset。同尺寸方块一般禁用。
- `roundRadius: 22`：已经人工测量的圆角蒙版，乘上已有 Alpha，不重绘内容。
- `mask`：蒙版路径；尺寸应等于源层整图，使用相同 rect。L 图取亮度，RGBA 图取 Alpha。用于经核验的透明分离，不创造隐藏图像。
- `padding: [left,top,right,bottom]`：加透明边；border 以加边后的最终图为准。
- `allowOpaque: true`：确实需要不透明贴图时使用，并在 note 解释；不能默认绕过透明检查。

脚本拒绝越界框、源尺寸不匹配、重复文件名、输出路径穿越、全透明素材、非背景全不透明素材及无效边框。已有非空输出目录会被保留并拒绝写入。打包成功不等于视觉审查通过。
