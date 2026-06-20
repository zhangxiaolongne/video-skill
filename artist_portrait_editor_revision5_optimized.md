# Artist Portrait Editor Skill
## Revision 5：优化后的 V0 工程冻结母版

> **文档状态**：V0 Engineering Freeze  
> **工作名称**：`artist-portrait-editor`  
> **中文名称**：人物向剪辑导演 / 艺人肖像剪辑 Skill  
> **适用范围**：产品愿景、V0 产品规格、V0 工程规格  
> **当前开发闸门**：仅允许启动阶段 A；阶段 A 通过前不得实现媒体扫描、转写、视觉分析、创作提案或时间线生成。

---

# 0. 执行摘要

`artist-portrait-editor` 面向广义人物向影像创作，不局限于偶像团体、舞台直拍或歌曲卡点。它需要理解一个人物在歌唱、影视、音乐剧、话剧、采访、排练、幕后等不同媒介中的素材，并帮助创作者发现素材之间新的叙事、情绪和视听关系。

长期目标是：

> 以人物为中心，完成素材研究、创意构思、叙事设计、声音设计、视听剪辑和专业工程输出。

V0 不做“一键精品成片”，而是先成为：

> **可靠的素材研究员 + 可解释的剪辑策划师。**

V0 分为两个模式：

- `core_mode`：不依赖文本生成模型或视觉模型，负责确定性媒体处理、canonical 数据、风险规则和素材结构报告。
- `creative_mode`：在 `core_mode` 证据基础上，生成三套可回溯创作提案，并在用户选择后生成时间线草案。

当前只允许实现阶段 A：

```text
project.yaml
→ 配置验证
→ 工作区初始化
→ 能力检测
→ 状态账本
→ 运行报告
→ 固定退出码
```

阶段 A 禁止实现：

```text
scan
ffprobe 扫描流程
媒体哈希
PySceneDetect
Whisper
OpenCV
Embedding
视觉模型
创作提案
时间线生成
预览渲染
```

---

# 1. 产品定位与创作原则

## 1.1 项目定位

这里的“人物”是广义概念，可能同时涉及：

- 歌手
- 影视演员
- 音乐剧演员
- 话剧演员
- 电影与电视剧
- 综艺与采访
- 排练与幕后
- 现场演出
- 公开活动
- 跨媒介艺术实践

系统不得默认所有视频都以音乐、BPM、舞蹈动作或舞台卡点为中心。

## 1.2 核心创作原则

1. **人物是中心，音乐不是中心。**
2. **真人、角色、歌词、采访和二创字幕必须区分。**
3. **剪辑规则是工具，不是限制。**
4. **创意优先来自镜头关系，而不是特效堆叠。**
5. **反常规必须服务于人物、主题或情绪，不能随机。**
6. **允许断裂、留白、反差、错位、延迟完成和故意不切。**
7. **重要表演片段可以保留完整呼吸，不必追求高切换密度。**
8. **模型只能组织证据，不能创造证据。**
9. **每个关键剪辑决定必须可解释、可回溯。**
10. **用户确认优先，但机器原始判断必须保留。**
11. **不确定信息必须明确标识，不能用确定语气掩盖。**
12. **用户拥有最终的事实、审美和创作决定权。**

## 1.3 创意的最低解释要求

任何常规或反常规方案都应说明：

```text
形式：镜头或声音如何连接
感受：预期产生什么观感
意义：为什么适合当前人物与主题
风险：可能造成什么误解、失效或过度表达
```

无法说明以上四项的效果，不视为有效创意。

## 1.4 Skill 与底层应用的边界

### Skill 负责

- 工作流编排
- 配置与前置条件检查
- 工具调用
- 证据组织
- 素材地图、提案和时间线草案生成
- 人工确认点
- 风险与降级规则
- 结果解释与迭代指导

### 底层应用负责

- 媒体解码与探测
- 内容哈希
- 镜头切分
- 音频提取与转写
- 关键帧与算法分析
- canonical 数据持久化
- 渲染与专业工程导出
- UI 和版本管理

Skill 可以编排底层能力，但 V0 不等于完整剪辑应用。

---

# 2. V0 范围

## 2.1 V0 目标

给定 10–30 个视频或音频素材、人物档案和创作主题，系统应能够：

- 建立可回溯的素材索引
- 区分确定性数据、算法推断与用户确认
- 标记来源、身份、文本类型和权利风险
- 告诉用户哪些片段值得使用及原因
- 生成三套结构真正不同的创作提案
- 在用户选择后生成可验证的时间线草案

## 2.2 运行模式

### `core_mode`

不依赖文本生成模型或视觉模型。

包含：

```text
配置与 Schema
CLI
状态账本
能力检测
媒体扫描
哈希与去重
基础切片
可选 ASR
确定性元数据
canonical 数据
基础关系
风险规则
素材结构报告
```

`faster-whisper` 属于可选 ASR 能力，不属于创意模型。缺失时 `core_mode` 仍可运行。

### `creative_mode`

依赖文本生成模型；视觉模型和 Embedding 为可选增强。

包含：

```text
素材语义总结
三套创作提案
反方案挑战
叙事与声音结构
时间线草案
剪辑理由
```

规则：

- `creative_mode` 必须建立在有效的 `core_mode` 数据上。
- 创意输出不能绕过置信度、禁用素材和证据校验。
- CI 默认只要求 `core_mode` 工程正确性。
- 创意质量使用独立测试，不得与基础工程测试混为一谈。

## 2.3 输入

必需输入：

```text
project.yaml
media/ 素材目录
创作主题
目标平台
目标时长
```

可选输入：

```text
sources.csv
annotations/
人物作品与角色清单
指定音乐或台词
禁用与优先素材
参考视频
创作风格说明
已确认事实
```

## 2.4 产物

### 系统工作区中的 canonical 数据

```text
.artist-portrait/data/
├── sources.jsonl
├── clips.jsonl
├── transcripts.jsonl
├── relations.jsonl
└── proposals.json
```

### 用户可见输出

```text
output/
├── material_map.md
├── proposals.md
├── timeline_draft.json
├── risk_report.md
└── run_report.md
```

可选：

```text
output/preview.mp4
```

### 用户交换格式

```text
sources.csv
```

`CSV` 用于导入、查看和编辑；`JSONL/JSON` 是系统内部真相源。

## 2.5 非目标

V0 明确不做：

```text
自动下载网络素材
保证识别所有人物、作品和角色
一键精品成片
电影级自动调色
复杂遮罩和人物抠像
换脸或伪造发言
把角色台词当作真人观点
完整专业混音
复杂自然语言时间线修改
高级隐喻关系自动识别
Premiere / Resolve / Final Cut 工程导出
多版本 A/B UI
自动发布
商业版权安全承诺
```

## 2.6 建议处理规模

```text
单项目素材数：10–30
总时长：不超过 6 小时
单文件：不超过 2 小时
候选片段：不超过 2000
```

超过限制时应提示分批处理或显式覆盖，不得静默截断。

---

# 3. 数据分层与真相源

## 3.1 三类目录

### 用户源数据

```text
project.yaml
sources.csv
media/
annotations/
```

用户源数据不得由系统静默覆盖。

### 系统工作区

```text
.artist-portrait/
├── state.json
├── data/
├── cache/
└── runs/
```

工作区包含状态、canonical 数据、缓存和运行历史。它不是普通输出目录，也不得被“清理输出”操作删除。

### 用户输出

```text
output/
```

输出是可重新生成的报告和草案，不存放唯一的用户确认历史或系统状态。

## 3.2 真相源规则

- `project.yaml`：项目配置真相源。
- `sources.csv`：用户交换格式，不是系统 canonical。
- `.artist-portrait/data/sources.jsonl`：来源 canonical。
- `.artist-portrait/state.json`：步骤状态与能力真相源。
- `annotations/`：用户人工确认和修订的持久化来源。
- `output/`：可重建产物，不得作为唯一状态依据。
- `runs/<run_id>/`：单次执行审计记录。

## 3.3 Schema 真相源

Pydantic Model 是唯一的结构定义真相源。

JSON Schema 必须从 Pydantic 自动生成，不允许手工维护两套独立定义，以避免漂移。

```text
Pydantic Models
→ generated JSON Schema
→ contract tests
```

## 3.4 文件创建语义

- `init` 不预创建任何业务数据或报告。
- 某步骤成功完成后，才创建其 canonical 产物。
- 某步骤因能力缺失被 `skipped` 时，不创建该步骤的 canonical 产物。
- 某步骤正常运行但结果为零条记录时，可以创建空文件；是否完成以状态账本为准，不以文件存在为准。
- 下游步骤必须同时检查状态账本和产物 Schema。

---

# 4. 全局数据规范

## 4.1 时间

- 所有媒体时间统一使用秒。
- 类型为 `number`，允许小数。
- 时间基于原始媒体时间轴。
- Schema 应约束 `0 <= start < end <= source_duration`。
- 展示层可转换为时间码；canonical 数据不混用帧数。

## 4.2 置信度

- 范围：`0.0–1.0`
- 类型：`number`
- 不使用“高 / 中 / 低”替代结构化数值。
- 置信度必须对应具体字段或判断，不得用一个总分代替所有语义。

## 4.3 空值与枚举

- 未知值统一使用 `null`。
- 不使用 `"unknown"`、`"n/a"`、`"?"` 混代空值。
- 枚举统一使用 `snake_case`。
- 若一个分类字段尚未确定，应使用 `value: null`，而不是在枚举中加入 `unknown`。

## 4.4 ID

使用两类 ID：

### 稳定实体 ID

- `source_id`：由 `project_id + content_hash` 生成 UUIDv5，表示一份唯一媒体内容。
- 相同内容出现在多个路径时，不创建多个 `source_id`，而是在同一记录的 `locations[]` 中增加位置。
- `clip_id`：由 `source_id + start_ms + end_ms + segmentation_version` 生成 UUIDv5。
- 相同输入和算法版本重跑时保持稳定。

### 运行 ID

- `run_id`：使用 UUIDv7。
- 每次命令执行生成新的 `run_id`。

文件内容变化后创建新的 `source_id`，并可通过 `supersedes_source_id` 关联旧版本。

## 4.5 通用断言结构

所有非确定性字段使用统一的 `Assertion[T]`：

```json
{
  "value": "close_up",
  "method": "vision_model",
  "level": 3,
  "confidence": 0.82,
  "evidence": [
    {
      "type": "keyframe",
      "ref": "clip_123/frame_001"
    }
  ],
  "user_confirmed": false
}
```

字段：

```text
value
method
level
confidence
evidence[]
user_confirmed
```

## 4.6 推断来源等级

```text
level_0：文件系统、哈希、ffprobe、确定性媒体属性和时间码
level_1：文件名、目录名、project.yaml、sources.csv 等项目上下文
level_2：Whisper、OCR、字幕、关键词和其它文本分析
level_3：OpenCV、Embedding、视觉模型及其它算法推断
level_4：用户确认
```

`level` 表示来源类别，不是统一的可信度排序。

冲突解决规则：

1. 用户明确确认的值优先。
2. 确定性字段只接受 `level_0` 数据。
3. 语义字段根据字段类型、证据和置信度处理，不按固定 `level` 顺序自动覆盖。
4. 相互冲突且无法可靠决断时，保留候选并请求确认。
5. 冲突不得静默丢弃。

---

# 5. 项目配置

## 5.1 `project.yaml`

示例：

```yaml
schema_version: "0.3"

project:
  id: chen_haoyu_portrait_001
  title: 不同舞台上的她
  artist_name: 陈昊宇
  language: zh-CN

creative_brief:
  theme: 不同媒介中的声音、身体与情绪
  audience: 熟悉人物的粉丝和普通观众
  platform: bilibili
  target_duration_seconds: 180
  aspect_ratio: "16:9"
  tone:
    - restrained
    - gentle
    - late_release

content_policy:
  allow_role_dialogue: true
  allow_real_person_role_mix: true
  allow_unconfirmed_visual_material: false
  allow_interview_audio: true
  allow_music: true
  allow_restricted_rights: false

features:
  transcription: auto
  scene_detection: auto
  visual_analysis: off
  experimental_relations: false

data_policy:
  allow_remote_text_model: false
  allow_remote_vision_model: false
  include_absolute_paths_in_remote_requests: false

paths:
  media_dir: ./media
  annotations_dir: ./annotations
  output_dir: ./output
```

## 5.2 配置枚举

功能开关统一使用：

```text
off
auto
required
```

行为：

- `off`：不执行。
- `auto`：能力存在则执行，缺失时降级并警告。
- `required`：能力缺失则当前命令失败。

## 5.3 不可配置的硬规则

以下规则不能被项目配置关闭：

- 不伪造人物发言。
- 不把角色台词默认视为真人观点。
- 不引用不存在的素材、ID 或时间码。
- 不绕过 `forbidden_by_user`。
- 不把低置信度事实写成确定陈述。
- 未经许可不得向远程模型发送素材内容。

---

# 6. Canonical 数据协议

本节定义字段骨架；完整约束由 Pydantic Model 和生成的 JSON Schema 实现。

## 6.1 `SourceRecord`

路径：

```text
.artist-portrait/data/sources.jsonl
```

关键字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | Schema 版本 |
| `source_id` | string | 稳定来源 ID |
| `locations` | string[] | 相对 `project.yaml` 的所有已知路径 |
| `primary_location` | string | 当前首选读取路径 |
| `content_hash` | string | 内容身份 |
| `supersedes_source_id` | string/null | 替代的旧版本 |
| `media_kind` | enum | `video` / `audio` |
| `media_probe` | object | ffprobe 确定性数据 |
| `source_type` | Assertion | 素材类型 |
| `work` | Assertion/null | 作品 |
| `role` | Assertion/null | 角色 |
| `recorded_date` | Assertion/null | 录制日期 |
| `published_date` | Assertion/null | 发布日期 |
| `rights_status` | Assertion | 权利状态 |
| `provenance_confidence` | number | 来源与出处可信度 |
| `provenance_method` | string | 计算方法 |
| `provenance_evidence` | EvidenceRef[] | 证据 |
| `candidate_values` | array | 未决候选 |
| `conflicts` | array | 冲突记录 |
| `user_confirmed` | boolean | 是否确认 |
| `confirmation_history` | array | 确认历史 |
| `forbidden_by_user` | boolean | 是否禁用 |
| `risk_flags` | array | 来源级风险 |
| `notes` | string/null | 备注 |

`provenance_confidence` 取代 Revision 4 中含义不够精确的 `source_confidence`。它只表示来源、出处和归属的可信度，不代表画质或内容价值。

位置规则：

- 复制相同文件只增加 `locations[]`，不创建新媒体实体。
- 文件移动后更新位置列表，保持 `source_id`。
- `primary_location` 必须指向一个当前可读取的位置。
- 所有位置失效时保留记录并标记风险，不静默删除历史实体。

### `media_probe`

视频字段：

```text
duration
width
height
frame_rate
video_codec
audio_present
audio_codec
```

音频素材允许：

```text
width = null
height = null
frame_rate = null
video_codec = null
```

### 共享内容类型枚举

`source_type.value` 与 `media_type.value` 使用同一套枚举：

```text
interview
stage_performance
live_performance
music_video
film_scene
tv_scene
theatre_scene
musical_scene
variety_show
rehearsal
behind_the_scenes
public_event
fan_edit
other
null
```

`rights_status.value`：

```text
owned
licensed
publicly_available
permission_unknown
restricted
null
```

## 6.2 `ClipRecord`

路径：

```text
.artist-portrait/data/clips.jsonl
```

关键字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `clip_id` | string | 稳定片段 ID |
| `source_id` | string | 来源引用 |
| `start` / `end` | number | 原始媒体秒数 |
| `duration` | number | 派生值 |
| `segmentation_method` | enum | 切分方法 |
| `media_type` | Assertion | 内容类型 |
| `identity_type` | Assertion | 真人 / 角色 / 混合 |
| `work` / `role` | Assertion/null | 作品与角色 |
| `shot_size` | Assertion/null | 景别 |
| `camera_motion` | Assertion/null | 镜头运动 |
| `emotions` | Assertion[] | 情绪候选 |
| `actions` | Assertion[] | 动作候选 |
| `speech_refs` | string[] | 转写引用 |
| `visual_quality` | Assertion/null | 画质 |
| `narrative_value` | Assertion/null | 叙事价值 |
| `risk_flags` | array | 片段级风险 |
| `tags` | array | 通用标签 |
| `user_confirmed` | boolean | 是否确认 |

`identity_type.value`：

```text
real_person
role_character
mixed
null
```

`segmentation_method`：

```text
pyscenedetect
fixed_window
transcript_window
manual
single_source
```

`shot_size.value`：

```text
extreme_wide
wide
full
medium_full
medium
medium_close_up
close_up
extreme_close_up
null
```

`camera_motion.value`：

```text
static
pan
tilt
push_in
pull_out
tracking
handheld
zoom_in
zoom_out
mixed
null
```

## 6.3 `TranscriptRecord`

路径：

```text
.artist-portrait/data/transcripts.jsonl
```

关键字段：

```text
transcript_id
source_id
start
end
text
language
speaker
text_type
word_timestamps
method
confidence
user_confirmed
risk_flags
```

`text_type.value`：

```text
interview
role_dialogue
lyrics
stage_dialogue
voice_over
program_caption
fan_caption
null
```

ASR 只能证明“听到了什么”，不能独立证明文本属于采访、歌词还是角色台词。

## 6.4 `RelationRecord`

路径：

```text
.artist-portrait/data/relations.jsonl
```

V0 必做：

```text
same_source
same_work
same_media_type
keyword_related
user_defined
```

V0 实验：

```text
similar_action
opposite_action
similar_emotion
opposite_emotion
similar_composition
```

关键规则：

- 实验关系不作为 V0 硬验收。
- 实验关系不得独立决定时间线。
- 关系的 `level` 和 `confidence` 必须继承上游证据，不得凭“字段匹配”自动升级为 `level_0 / 1.0`。
- 例如两个 `media_type` 均由目录名以 `0.84` 推断，则 `same_media_type` 至多为 `level_1`，置信度不得高于上游最弱证据。
- 用户可关闭所有实验关系。

## 6.5 `ProposalSet`

机器可读：

```text
.artist-portrait/data/proposals.json
```

人类可读：

```text
output/proposals.md
```

固定包含：

```text
proposal_safe
proposal_advanced
proposal_risky
```

每套方案必须有：

```text
proposal_id
title
theme
audience
required_clip_ids
fact_refs
story_structure
sound_structure
visual_motifs
risks
minimum_viable_timeline
missing_material
counter_proposal
```

规则：

- Markdown 只是渲染结果，时间线命令不得解析 Markdown。
- 所有事实必须引用 `project.yaml`、已确认的 `SourceRecord` 或明确证据。
- 所有动作、情绪和构图判断必须引用 `clip_id`。
- 不得虚构缺失素材。
- 不存在的 ID 使提案验证失败。

## 6.6 `TimelineDraft`

路径：

```text
output/timeline_draft.json
```

顶层字段：

```text
schema_version
timeline_id
proposal_id
target_duration
actual_duration
segments
warnings
```

Segment 字段：

```text
segment_id
timeline_start
timeline_end
clip_id
source_id
source_in
source_out
track_id
media_role
video_transition
audio_transition
reason
evidence
creative_intent
confidence
```

`media_role`：

```text
video
audio
both
```

`video_transition`：

```text
none
hard_cut
crossfade
fade_in
fade_out
match_cut
```

`audio_transition`：

```text
none
cut
crossfade
fade_in
fade_out
j_cut
l_cut
```

规则：

- 所有引用必须存在。
- 原始时间码不得越界。
- 交叠只允许由明确的转场或多轨设计解释。
- 禁用、受限或时间码不可靠的片段不得进入可执行段落。
- 时间线仅在用户选择提案后生成。

## 6.7 风险枚举按作用域拆分

### 来源级

```text
unknown_provenance
low_provenance_confidence
rights_unknown
rights_restricted
decode_failed
conflicting_metadata
forbidden_by_user
```

### 片段级

```text
unknown_work
unknown_role
low_identity_confidence
timecode_unreliable
segmentation_fallback
forbidden_by_user
```

### 转写级

```text
audio_missing
transcript_failed
low_text_type_confidence
possible_fan_caption
possible_program_caption
possible_role_dialogue
possible_lyrics
```

### 提案与时间线级

```text
missing_evidence
invalid_reference
unconfirmed_fact
forbidden_content_reference
model_output_unverified
duration_out_of_tolerance
illegal_overlap
```

新增风险枚举必须提升 Schema 版本。

---

# 7. 事实、模型与隐私边界

## 7.1 硬阈值

```text
provenance_confidence < 0.7
不得作为确定事实写入字幕、标题、文案或提案事实陈述。

identity_type.confidence < 0.8
不得用于证明人物本人身份、观点或真实经历。

text_type.confidence < 0.8
不得确定声明为采访、歌词或角色台词。

identity_type.value 为 null 或未确认
只能作为视觉候选，不能作为真人叙事证据。

无法回溯 source_id / clip_id / start / end
不得进入提案事实引用或时间线。

forbidden_by_user = true
不得出现在提案、时间线或预览中。

rights_status = restricted
默认不得使用，除非项目策略明确允许且用户确认。
```

## 7.2 低置信度表达

必须使用：

- 疑似
- 可能
- 尚未确认
- 需要用户确认
- 仅作为视觉候选
- 不建议作为事实依据

## 7.3 文本模型允许做

- 总结已存在证据
- 组织三套创作提案
- 生成反方案
- 生成时间线草案
- 解释剪辑决定
- 汇总风险

## 7.4 文本模型禁止做

- 创造人物事实、素材、台词或 ID
- 无来源确定作品和角色
- 把角色台词当真人观点
- 绕过禁用或权利限制
- 忽略置信度规则

## 7.5 视觉模型允许做

- 景别和构图候选
- 基础动作和情绪候选
- 视觉描述
- 画质辅助判断

视觉模型不能独立确定：

- 人物真实身份
- 角色身份
- 作品来源
- 真实事件
- 人物观点
- 版权状态

## 7.6 远程模型数据策略

默认：

```text
allow_remote_text_model = false
allow_remote_vision_model = false
```

向远程服务发送以下内容前必须得到显式许可：

- 转写文本
- 关键帧
- 视频片段
- 人物档案
- 来源 URL
- 本地绝对路径

远程请求不得包含未授权的本地绝对路径或隐私元数据。

## 7.7 模型输出验证

任何模型结果写入 canonical 或输出前必须通过：

1. Schema 验证
2. ID 存在性验证
3. 时间码范围验证
4. 置信度阈值验证
5. 禁用素材验证
6. 事实来源验证
7. 权利规则验证
8. 风险规则验证

验证失败的结果只能进入运行错误记录，不得直接成为正式产物。

---

# 8. 目录结构

## 8.1 用户项目目录

```text
project_root/
├── project.yaml
├── sources.csv
├── media/
├── annotations/
├── .artist-portrait/
│   ├── state.json
│   ├── data/
│   │   ├── sources.jsonl
│   │   ├── clips.jsonl
│   │   ├── transcripts.jsonl
│   │   ├── relations.jsonl
│   │   └── proposals.json
│   ├── cache/
│   │   ├── probes/
│   │   ├── audio/
│   │   ├── keyframes/
│   │   └── embeddings/
│   └── runs/
│       └── <run_id>/
│           ├── command.json
│           ├── environment.json
│           ├── step_result.json
│           ├── warnings.json
│           ├── errors.json
│           └── log.txt
└── output/
    ├── material_map.md
    ├── proposals.md
    ├── timeline_draft.json
    ├── risk_report.md
    └── run_report.md
```

要求：

- 原始素材只读。
- `.artist-portrait/data/` 不得被普通缓存清理删除。
- `.artist-portrait/cache/` 可删除重建。
- `annotations/` 不得被系统覆盖。
- `output/` 可重建。
- 所有文本使用 UTF-8。
- 项目内路径统一相对 `project.yaml` 所在目录解析。

## 8.2 仓库结构

```text
artist-portrait-editor/
├── SKILL.md
├── README.md
├── AGENTS.md
├── pyproject.toml
├── docs/
│   ├── VISION.md
│   ├── PRODUCT_SPEC_V0.md
│   ├── ENGINEERING_SPEC_V0.md
│   ├── CLI_SPEC.md
│   ├── STATE_AND_INVALIDATION.md
│   ├── DATA_CONTRACTS.md
│   ├── MODEL_BOUNDARIES.md
│   ├── ACCEPTANCE_TESTS_V0.md
│   └── NON_GOALS.md
├── src/artist_portrait_editor/
│   ├── cli.py
│   ├── models/
│   ├── config/
│   ├── state/
│   ├── ingest/
│   ├── media/
│   ├── transcription/
│   ├── segmentation/
│   ├── analysis/
│   ├── relations/
│   ├── proposals/
│   ├── timeline/
│   ├── review/
│   └── reporting/
├── prompts/
├── fixtures/
├── examples/
└── tests/
    ├── unit/
    ├── contract/
    ├── integration/
    └── creative/
```

---

# 9. CLI 协议

可执行命令：

```text
artist-portrait
```

## 9.1 命令

```bash
artist-portrait validate --project ./project.yaml
artist-portrait init --project ./project.yaml
artist-portrait scan --project ./project.yaml
artist-portrait segment --project ./project.yaml
artist-portrait transcribe --project ./project.yaml
artist-portrait analyze --project ./project.yaml
artist-portrait relate --project ./project.yaml
artist-portrait map --project ./project.yaml
artist-portrait propose --project ./project.yaml
artist-portrait timeline --project ./project.yaml --proposal proposal_advanced
artist-portrait review --project ./project.yaml --scope project
artist-portrait run --project ./project.yaml --mode core
artist-portrait status --project ./project.yaml
```

## 9.2 通用参数

```text
--project PATH
--mode core|creative
--force
--resume
--dry-run
--json
--verbose
--quiet
```

约束：

- `--project` 指向 `project.yaml`，所有相对路径以其父目录为基准。
- CLI 参数优先于 `project.yaml` 中同名的运行时选项，但不得覆盖不可配置硬规则。
- `--force` 只能重建机器生成产物，不能覆盖用户确认、禁用标记或 `annotations/`。
- `--resume` 从状态账本中最近的可恢复步骤继续。
- `--dry-run` 不写入项目文件。
- `--verbose` 与 `--quiet` 互斥。
- `--json` 只改变命令输出格式，不改变项目文件格式。

## 9.3 命令职责

| 命令 | 职责 | 主要产物 |
|---|---|---|
| `validate` | 验证配置、路径和策略；可在初始化前运行 | 无业务产物 |
| `init` | 调用验证、创建工作区、能力检测、状态与运行记录 | `state.json`、run 记录、`run_report.md` |
| `scan` | 扫描媒体、哈希、ffprobe、导入 CSV | `sources.jsonl` |
| `segment` | 视频场景切分；音频按转写或固定窗口切分 | `clips.jsonl` |
| `transcribe` | 可选 ASR | `transcripts.jsonl` |
| `analyze` | 基础标签、算法推断和风险 | 更新 canonical |
| `relate` | 基础关系；可选实验关系 | `relations.jsonl` |
| `map` | 渲染素材地图 | `material_map.md` |
| `propose` | 生成并验证三套提案 | `proposals.json`、`proposals.md` |
| `timeline` | 从已选择提案生成草案 | `timeline_draft.json` |
| `review` | 按 scope 检查当前产物 | `risk_report.md` |
| `run` | 按模式编排命令 | 多个 |
| `status` | 显示能力、步骤和警告 | 终端 / JSON |

`scan` 写入 canonical `sources.jsonl`，仅在用户要求时导出规范化 `sources.csv`。

## 9.4 `validate` 与 `init`

- `validate` 可以在任何项目状态下运行，默认不修改项目。
- `init` 内部必须执行同等级配置验证，验证失败不得创建工作区。
- `init` 只创建：

```text
.artist-portrait/state.json
.artist-portrait/cache/
.artist-portrait/data/
.artist-portrait/runs/<run_id>/
output/
output/run_report.md
```

- `init` 不创建：

```text
sources.jsonl
clips.jsonl
transcripts.jsonl
relations.jsonl
proposals.json
material_map.md
proposals.md
timeline_draft.json
risk_report.md
```

## 9.5 `review` Scope

```text
project
proposal
timeline
all
```

| Scope | 检查内容 | 前置条件 |
|---|---|---|
| `project` | 配置、来源、片段、Schema、风险 | 至少完成 `scan`；仅配置检查可用 `validate` |
| `proposal` | 证据、引用、事实和禁用素材 | `propose` 完成 |
| `timeline` | 时间码、交叠、时长和引用 | `timeline` 完成 |
| `all` | 检查所有当前存在的产物 | 跳过尚未生成的可选产物并警告 |

`review --scope all` 跳过未生成的 proposal 或 timeline，不视为 fatal。

## 9.6 `run`

`core_mode`：

```text
validate
→ init（如未初始化）
→ scan
→ segment
→ transcribe（off / auto / required）
→ analyze
→ relate（仅基础关系）
→ map
→ review --scope project
```

`creative_mode`：

```text
core_mode
→ propose
→ review --scope proposal
```

默认不自动生成时间线。只有显式指定提案时：

```bash
artist-portrait run \
  --project ./project.yaml \
  --mode creative \
  --proposal proposal_advanced
```

才执行：

```text
timeline
→ review --scope all
```

---

# 10. 状态账本与失效规则

单一线性 `state` 无法表达可选 ASR、创意分支和不同 review scope，因此 V0 使用**步骤状态账本**，而不是把项目强制塞进一条线性状态机。

## 10.1 `state.json`

```json
{
  "schema_version": "0.3",
  "project_id": "chen_haoyu_portrait_001",
  "overall_status": "ready",
  "active_mode": "core",
  "capabilities": {
    "ffmpeg": true,
    "ffprobe": true,
    "pyscenedetect": false,
    "faster_whisper": false,
    "opencv": false,
    "text_model": false,
    "vision_model": false
  },
  "steps": {
    "validate": {
      "status": "completed",
      "input_fingerprint": "sha256:...",
      "output_refs": [],
      "last_run_id": "run_...",
      "warnings": []
    },
    "init": {
      "status": "completed",
      "input_fingerprint": "sha256:...",
      "output_refs": [".artist-portrait/state.json"],
      "last_run_id": "run_...",
      "warnings": []
    },
    "scan": {
      "status": "pending",
      "input_fingerprint": null,
      "output_refs": [],
      "last_run_id": null,
      "warnings": []
    }
  },
  "latest_run_id": "run_...",
  "updated_at": "2026-06-21T00:00:00Z"
}
```

## 10.2 步骤状态

```text
pending
running
completed
completed_with_warnings
skipped
blocked
failed
invalidated
```

`failed` 属于某个步骤或某次运行，不把整个项目永久改成不可恢复的 `failed` 状态。

## 10.3 项目总体状态

```text
new
ready
running
degraded
blocked
```

总体状态是步骤账本的派生结果：

- `new`：未初始化。
- `ready`：可继续执行，无阻塞问题。
- `running`：有命令正在运行。
- `degraded`：存在可降级警告，但仍可继续。
- `blocked`：缺少当前请求所必需的依赖、确认或有效产物。

## 10.4 步骤依赖

| 步骤 | 依赖 |
|---|---|
| `validate` | 无 |
| `init` | 配置验证通过 |
| `scan` | `init` |
| `segment` | `scan` |
| `transcribe` | `scan`；可与 `segment` 并行或独立 |
| `analyze` | `segment`；文本标签还依赖 `transcribe` |
| `relate` | `analyze` |
| `map` | `analyze` |
| `propose` | `map` + 可用文本模型 |
| `timeline` | `propose` + 用户选择 |
| `review_project` | `scan`；完整检查建议 `map` |
| `review_proposal` | `propose` |
| `review_timeline` | `timeline` |

## 10.5 失效规则

- 媒体内容变化：使 `scan` 及其下游失效。
- 媒体仅移动路径但哈希不变：更新路径，不重建实体 ID；使依赖路径的缓存失效。
- 创作主题、目标时长或平台变化：使 `propose`、`timeline` 和相关 review 失效。
- 用户修改人物、作品或角色确认：使 `analyze` 及其创意下游失效。
- 仅输出格式变化：只使对应渲染输出失效。
- 算法或 Schema 版本变化：按版本迁移策略决定重建范围。

## 10.6 重跑规则

- 命令必须幂等。
- 不重复创建相同实体。
- 不覆盖用户确认和人工标注。
- 每次运行生成新 `run_id`。
- 状态更新应原子写入，失败时保留上一份有效状态。
- canonical 文件写入使用临时文件 + 校验 + 原子替换。

---

# 11. 依赖与降级

## 11.1 阶段 A 必需

```text
Python 3.11+
PyYAML
Pydantic
```

Python 标准库提供：

```text
sqlite3（如内部需要）
hashlib
pathlib
json
```

阶段 A 仅检测 FFmpeg / ffprobe，不要求它们存在才能完成 `init`。

## 11.2 媒体命令必需

```text
FFmpeg
ffprobe
```

缺失时：

- `validate`、`init`、`status` 可成功并报告能力缺失。
- `scan` 及媒体下游返回缺少必需依赖。
- 不生成伪造媒体数据。

## 11.3 推荐增强

```text
PySceneDetect
faster-whisper
OpenCV
```

降级：

- 无 PySceneDetect 且 `scene_detection: auto`：降级为 `fixed_window` 并警告。
- 无 PySceneDetect 且 `scene_detection: required`：切分命令失败。
- 无 faster-whisper 且配置为 `auto`：步骤 `skipped`，不创建 `transcripts.jsonl`。
- 无 faster-whisper 且配置为 `required`：命令失败。
- 无 OpenCV：相关字段保持 `null`，不生成伪造值。

## 11.4 创意模型

- 无文本生成模型：`core_mode` 正常，`creative_mode` 被阻塞。
- 无视觉模型：仍可基于元数据、文本和人工标注生成提案。
- 无 Embedding：关系退化为结构字段和关键词匹配。
- 不再生成“模板化 proposals”冒充 `creative_mode` 成功。

## 11.5 单个素材失败

- 单文件解码或转写失败不阻断整批任务。
- 失败写入来源级或转写级风险。
- 若所有素材均失败，命令返回 fatal。
- 部分成功返回 `success_with_warnings`。

---

# 12. CLI 退出码

```text
0   success
1   success_with_warnings
2   invalid_arguments
3   invalid_project_config
4   missing_required_dependency_for_command
5   media_operation_failed
6   generated_artifact_schema_invalid
7   prerequisite_step_missing
8   model_call_failed
9   output_or_reference_validation_failed
10  user_confirmation_required
11  forbidden_content_reference
12  unrecoverable_internal_error
```

边界：

- `3`：`project.yaml` 的 Schema 或语义配置错误。
- `6`：系统生成的 canonical 或输出文件不符合 Schema。
- 缺少 FFmpeg 对 `init` 是警告，对 `scan` 是退出码 `4`。
- 单个素材失败但仍有有效结果返回 `1`。
- 所有素材扫描失败返回 `5`。
- 不存在的 `clip_id/source_id` 返回 `9`。
- 引用禁用素材返回 `11`。

---

# 13. 人工确认点

## 13.1 初始化时

确认：

- 人物与创作主题
- 目标平台和时长
- 是否允许真人与角色混剪
- 是否允许角色台词
- 是否使用音乐与采访原声
- 是否允许远程模型处理数据

## 13.2 分析后

确认：

- 作品和角色
- 素材来源
- 文本类型
- 权利状态
- 冲突元数据
- 低置信度身份判断

## 13.3 创意阶段

确认或组合 `ProposalSet` 中的稳妥、高级和冒险方案。

允许：

```text
高级方案的结构
+ 冒险方案的开场
+ 稳妥方案的结尾
```

## 13.4 时间线前

确认：

- 选择的素材
- 角色台词使用
- 高风险片段
- 未确认事实
- 禁用素材排除结果
- 关键反常规剪辑意图

---

# 14. 三套提案与反方案

## 14.1 稳妥方案

- 信息清楚
- 风险较低
- 适合普通观众
- 优先使用高置信度素材
- 结构可以接近人物介绍、身份展开、高光和当下状态

## 14.2 高级方案

- 跨媒介互文
- 非纯时间线
- 使用动作、声音或情绪关系
- 保持可理解性
- 允许留白

## 14.3 冒险方案

- 非线性
- 强反差
- 延迟完成
- 声画错位
- 高潮不一定使用最直接的高光素材
- 必须明确说明风险

## 14.4 反方案挑战

每套提案至少回答一个挑战：

- 不按时间顺序会怎样？
- 不用正脸开场会怎样？
- 高潮不使用最强画面会怎样？
- 音乐高潮突然静音会怎样？
- 用后台细节替代舞台高光会怎样？
- 动作中断并延迟完成会怎样？
- 使用完全相反的情绪或运动连接会怎样？

反方案仍须引用真实证据。

---

# 15. Fixture 与测试

## 15.1 阶段 A Fixture

```text
fixtures/stage_a/
├── valid_project.yaml
├── invalid_missing_field.yaml
├── invalid_enum.yaml
├── invalid_path_policy.yaml
└── expected/
    ├── directory_tree.txt
    ├── state.json
    ├── exit_codes.json
    └── capability_expectations.json
```

阶段 A 测试不得读取或分析媒体。

## 15.2 完整 V0 Fixture

```text
fixtures/minimal_project/
├── project.yaml
├── sources.csv
├── media/
│   ├── interview_short.mp4
│   ├── stage_short.mp4
│   ├── role_scene_short.mp4
│   ├── silent_video.mp4
│   ├── corrupt_video.mp4
│   └── duplicate_interview.mp4
└── expected/
    ├── required_artifacts.txt
    ├── source_expectations.json
    ├── clip_expectations.json
    ├── risk_expectations.json
    ├── transcript_expectations.json
    ├── relation_expectations.json
    ├── core_mode_expectations.json
    ├── creative_mode_expectations.json
    └── exit_codes.json
```

素材必须是：

- 自制
- 公共领域
- 明确可再分发
- 程序生成

## 15.3 必测情形

- 正常采访
- 舞台素材
- 角色台词
- 音频素材
- 无音轨视频
- 损坏视频
- 重复素材
- 文件移动
- 文件内容变化
- 未知来源
- 用户禁用素材
- 缺少 FFmpeg
- 缺少 Whisper
- 缺少 PySceneDetect
- 缺少 OpenCV
- 缺少文本模型
- 缺少视觉模型
- 重复运行
- 中断恢复
- 用户确认不被覆盖

## 15.4 验收分层

### 阶段 A

必须通过：

```text
Pydantic Model
生成 JSON Schema
validate
init
目录初始化
能力检测
状态账本
运行日志
固定退出码
dry-run
幂等重跑
```

### `core_mode`

必须在无文本模型、无视觉模型环境通过：

```text
scan
canonical sources
segment
可选 transcribe
基础 analyze
基础 relations
material map
project review
```

### `creative_mode`

在模型环境验证：

```text
三套可回溯提案
结构差异
反方案
proposal review
用户选择后的 timeline
timeline review
```

创意质量测试与基础 CI 分离。

---

# 16. 开发顺序

## 16.1 阶段 A：工程底座

仅实现：

1. 仓库骨架
2. Pydantic Models
3. 自动生成 JSON Schema
4. CLI 框架
5. 状态账本
6. 能力检测
7. 退出码
8. 阶段 A Fixture
9. `validate`
10. `init`
11. `status`

第一条链路：

```text
project.yaml
→ Pydantic validation
→ JSON Schema contract check
→ init
→ capability detection
→ .artist-portrait/state.json
→ run record
→ output/run_report.md
→ fixed exit code
```

阶段 A 完成条件：

- `init` 不读取媒体。
- `init` 不创建业务产物。
- `validate` 可独立运行。
- 缺少 FFmpeg 不阻断阶段 A。
- 所有状态和运行记录可审计。
- 重跑不会破坏已有项目。

## 16.2 V0-002：媒体扫描

目标：

- 扫描媒体
- 计算内容哈希
- ffprobe
- 导入 `sources.csv`
- 写入 canonical `sources.jsonl`

验收：

- 支持 MP4、MOV、MKV、M4V、MP3、WAV。
- 文件移动保持实体 ID。
- 内容变化创建新版本。
- 重复素材不重复建实体。
- 单文件失败可降级。

## 16.3 V0-003：切分

- 视频优先 PySceneDetect，缺失时固定窗口。
- 音频使用转写窗口或固定窗口。
- 保留原始时间码和切分算法版本。
- 稳定生成 `clip_id`。

## 16.4 V0-004：转写

- 生成可回溯时间戳。
- 不自动认定采访、歌词或角色台词。
- 缺少 ASR 时按功能开关规则处理。

## 16.5 V0-005：关键帧与缓存

- 为视频片段抽取关键帧。
- 音频片段不要求关键帧。
- 缓存可安全重建。
- canonical 不依赖缓存永久存在。

## 16.6 V0-006：基础分析

- 素材类型
- 景别
- 镜头运动
- 基础情绪和动作候选
- 画质
- 原声可用性
- 风险标记

所有算法结果必须带 `method / level / confidence / evidence`。

## 16.7 V0-007：素材地图

生成：

```text
output/material_map.md
```

素材地图应回答：

- 有哪些素材
- 素材类型与分布
- 哪些片段值得优先查看
- 判断依据
- 待确认项
- 风险项

## 16.8 V0-008：创作提案

生成：

```text
.artist-portrait/data/proposals.json
output/proposals.md
```

三套方案必须结构不同、证据可回溯且不使用禁用素材。

## 16.9 V0-009：时间线草案

在用户选择提案后生成：

```text
output/timeline_draft.json
```

验证：

- 引用
- 时间码
- 交叠
- 时长
- 禁用素材
- 权利与事实风险

## 16.10 V0-010：整体验收

生成或更新：

```text
output/risk_report.md
output/run_report.md
```

完成 contract、integration 和 mode-specific 测试。

---

# 17. 成功标准

## 17.1 阶段 A

> 项目能稳定完成配置验证、工作区初始化、能力检测、步骤状态记录和固定退出码，且不触碰媒体分析。

## 17.2 `core_mode`

> 项目能在没有文本生成模型和视觉模型的环境中，稳定生成可回溯的结构化素材数据、基础关系、风险信息和素材地图。

## 17.3 `creative_mode`

> 系统能基于已有证据生成三套结构真正不同的提案，并在用户选择后生成可验证的时间线草案。

## 17.4 总体

系统应最终告诉用户：

- 哪些素材有用
- 为什么有用
- 依据来自哪里
- 哪些内容只是推断
- 哪些事实与权利存在风险
- 可以怎样组合
- 哪份草案可以继续人工或程序处理

V0 不以自动精品成片为成功标准。

---

# 18. 后续路线

## V1：低清粗剪与基础修改

- FFmpeg 预览
- 基础字幕与音乐
- 片段替换、延长、缩短和顺序修改
- 基础横竖屏适配

目标：可用的助理剪辑师。

## V2：创意系统

- 高级镜头关系
- 视觉押韵
- 情绪反差
- 延迟动作完成
- 非线性叙事
- 声画错位
- 多轨声音导演
- 自动审片和局部版本比较

目标：开始具备导演式创意能力。

## V3：专业工程

- FCPXML
- Resolve / Premiere 兼容时间线
- 版本管理
- 人物知识库
- 创作记忆
- 团队协作
- 专业混音与调色接口

目标：进入专业剪辑工作流。

---

# 19. 职责分工

## 产品与创作设计

- 产品边界
- 创作理念
- 数据与文件协议
- Prompt 和模型边界
- 任务拆分
- 验收与创意审查

## Codex 工程执行

- 仓库和 Python 实现
- Pydantic / JSON Schema
- CLI 和状态账本
- FFmpeg、Whisper、PySceneDetect、OpenCV 集成
- Fixture、测试和修复
- 提交代码变更

## 用户最终决策

- 人物和素材来源确认
- 审美方向
- 角色与真人关系
- 提案选择
- 风险接受程度
- 创意结果评价

---

# 20. Revision 5 优化摘要

本版在完整阅读 Revision 4 后完成以下结构和逻辑修订：

1. 将状态、canonical 数据和用户确认历史移出可重建的 `output/`。
2. 用步骤状态账本替代无法表达可选分支的线性状态机。
3. 修正 `project_state` 示例中“状态与完成步骤不一致”的问题。
4. 明确 `scan` 写入 `sources.jsonl`，`sources.csv` 仅为交换格式。
5. 将含义含混的 `source_confidence` 改为 `provenance_confidence`。
6. 增加机器可读 `proposals.json`，避免后续解析 Markdown。
7. 将风险枚举按来源、片段、转写、提案和时间线拆分。
8. 修正关系置信度：不得高于其上游证据。
9. 取消固定 `level_4 > level_0 > ...` 的错误统一排序，改为字段级冲突解析。
10. 明确 `validate` 可独立运行，`init` 内部也必须验证。
11. 明确缺少 FFmpeg 对 `init` 只是能力警告，对 `scan` 才是 fatal。
12. 明确无文本模型时 `creative_mode` 被阻塞，不生成模板提案冒充成功。
13. 统一空值规则，删除与 `null` 冲突的 `"unknown"` 枚举用法。
14. 为音频素材补充 `media_kind`、音频切分和时间线角色。
15. 将视频转场与音频转场拆开，避免 `audio_bridge` 混入视频枚举。
16. 细化 CLI 参数优先级、`--force` 边界和 review scope 前置条件。
17. 将阶段 A Fixture 与完整媒体 Fixture 分离，保证阶段 A 不读取媒体。
18. 合并重复出现的冻结范围、成功标准和开发限制，减少文档冗余。

---

# 21. 最终冻结结论

本文档可作为：

```text
VISION.md
PRODUCT_SPEC_V0.md
ENGINEERING_SPEC_V0.md
```

的优化母版。

当前只允许 Codex 开始阶段 A：

```text
仓库骨架
Pydantic Models
自动生成 JSON Schema
CLI 框架
状态账本
能力检测
退出码
阶段 A Fixture
validate
init
status
```

阶段 A 通过前，不得实现任何媒体分析或创意能力。
