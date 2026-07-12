# Artist Portrait Editor Skill
## Revision 5：优化后的 V0 工程冻结母版

> **文档状态**：V0 Engineering Freeze  
> **工作名称**：`artist-portrait-editor`  
> **中文名称**：人物向剪辑导演 / 艺人肖像剪辑 Skill  
> **适用范围**：产品愿景、V0 产品规格、V0 工程规格  
> **当前开发闸门**：V2-01 Real Video Aesthetic Baseline，本地已完成、尚未发布。下一完整版本是 V2-02 Frame Composition And Reframing，但尚未启动。具体执行任务、验收和发布状态分别以 `docs/CURRENT_BATCH.md`、`docs/DEVELOPMENT_PROGRESS.md`、`docs/RELEASES.md` 与 `docs/current_progress.json` 为准。

---

# 0.0 文档职责分工

本母版文档负责记录长期稳定的战略内容：

- 产品定位
- 能力边界
- 数据契约
- 创作原则
- 风险原则
- 阶段闸门
- 不可违背的设计约束

战术信息按唯一归属拆分：

| 文件 | 唯一职责 |
|---|---|
| `docs/DEVELOPMENT_PROGRESS.md` | 当前阶段、能力完成度、主要阻塞和下一大方向 |
| `docs/CURRENT_BATCH.md` | 当前批次、十项版本任务、状态、验收证据和收口 |
| `docs/ISSUES.md` | open、blocked、accepted、resolved、superseded 问题与风险 |
| `docs/DECISIONS.md` | 长期有效的产品、架构、流程和发布决策 |
| `docs/RELEASES.md` | 大版本结果、当前验证证据和 Git 发布状态 |
| `docs/current_progress.json` | 供自动检查使用的机器可读镜像 |

旧 `V0_*_RELEASE_READINESS.md` 只保留为历史验收证据，其中测试数字和发布状态
不得作为当前状态引用。母版不记录每次小版本流水账；任何战术事实只允许有一个
canonical owner，其它文档只能链接或摘要，不得建立第二套任务、问题或发布台账。

当用户提出会改变长期产品能力或创作原则的新要求时：

- 母版记录战略原则和长期约束。
- `DEVELOPMENT_PROGRESS.md` 更新当前阶段影响。
- 当前执行任务进入 `CURRENT_BATCH.md`。
- 新风险、决策和发布结果分别进入对应专用台账。

## 0.1 第三方能力复用原则

建设本 Skill 时，不要求所有能力从零实现。只要进入相应开发闸门并通过验证，可以直接复用成熟第三方能力，包括：

- Codex 自带插件
- 已安装 Skill
- 本地或远程搜索
- image2 / image generation / image editing 能力
- OpenAI、Codex/ChatGPT 宿主 Agent、本地模型或其它模型能力
- ffmpeg、ffprobe、PySceneDetect、Whisper、OpenCV 等专业工具
- 其它稳定、可验证、可替换的开源或商业工具

原则：

- 公开素材场景下，第三方工具调用不是默认禁区。
- 不重复造轮子；优先复用成熟工具，再补本项目特有的数据契约、证据链、审查和降级逻辑。
- 第三方结果不得直接冒充 canonical truth，必须记录来源、输入、输出、置信度、失败模式和可复验路径。
- 使用第三方模型、联网能力、搜索、image2/image generation/editing 或本地模型时，必须由对应 gate、配置开关、provenance、validation、fallback 和 review 规则控制。
- 当前 V0-011 使用 Codex/ChatGPT 宿主 Agent 生成候选提案；CLI 只执行本地 handoff、quarantine、validation 与 atomic promotion。不得接入付费 API、API key、远程 provider 或隐藏网络调用。

# 0. 执行摘要

`artist-portrait-editor` 面向广义人物向影像创作，不局限于偶像团体、舞台直拍或歌曲卡点。它需要理解一个人物在歌唱、影视、音乐剧、话剧、采访、排练、幕后等不同媒介中的素材，并帮助创作者发现素材之间新的叙事、情绪和视听关系。

长期目标是：

> 以人物为中心，完成素材研究、创意构思、叙事设计、声音设计、视听剪辑和专业工程输出。

V0 不做“一键精品成片”，而是先成为：

> **可靠的素材研究员 + 可解释的剪辑策划师。**

V0 分为两个模式：

- `core_mode`：不依赖文本生成模型或视觉模型，负责确定性媒体处理、canonical 数据、风险规则和素材结构报告。
- `creative_mode`：在 `core_mode` 证据基础上，生成三套可回溯创作提案，并在用户选择后生成时间线草案。

## 0.2 最终验收定义与阶段路线

从 V0-051 之后，项目推进按最终验收阶段衡量，不再把单个 artifact、schema、
report、packet、测试或局部修复当成大版本进度。

最终验收的含义：

- 操作者从 raw materials 到 proposal、timeline、BGM、preview、final export、
  editor package、FCPXML/NLE handoff 和 release install 有一条清晰主路径。
- 创作链路中 proposal、timeline、文字、BGM、节奏、转场、预览、导出保持连接，
  不是互相孤立的工程产物。
- BGM 支持 direct audio、video-extracted audio、source embedded audio、多个候选
  和 no-file-yet planning，并保留 source/range/stream/hash/contamination provenance。
- 交付链路能产出或明确阻塞 preview MP4、final MP4、editor package、cue sheet、
  FCPXML、NLE map 和 handoff 文档。
- 外部 workflow/NLE evidence 可以导入、审查、修复，但不得被 CLI 直接当作成功。
- release candidate 必须通过 package validation、install simulation、full tests、
  Git state、tag 和 remote freshness 检查。

最终验收阶段：

| Stage | 状态 | 目的 |
|---|---|---|
| `ACCEPTANCE-STAGE-01` Final acceptance target refactor | completed | 明确最终验收定义、六阶段路线、当前差距和防碎片化约束 |
| `ACCEPTANCE-STAGE-02` Guided creator workflow | completed | 建立从素材到交付物的一条主流程和 next-command 体验 |
| `ACCEPTANCE-STAGE-03` Golden real-project baseline | completed | 用真实感项目证明端到端输出，而不只靠生成 fixture |
| `ACCEPTANCE-STAGE-04` BGM and rhythm quality pass | completed | 将 BGM、节奏、字幕、转场、停顿和导出质量作为一个剪辑质量阶段 |
| `ACCEPTANCE-STAGE-05` NLE round-trip readiness | completed | 形成可交给剪辑软件/操作者使用的 NLE 往返闭环 |
| `ACCEPTANCE-STAGE-06` Release candidate and publication | completed | 完成安装、验证、提交、tag、push 和远端状态确认 |

## 0.3 审美成熟度判断

V0 发布证明的是工程闭环：真实素材可以进入项目，生成 proposal、timeline、preview、
final MP4、NLE/FCPXML 交付证据和 release 证据。它不能被误读为已经具备成熟剪辑师
审美。当前真实素材验收暴露出的问题很明确：系统可以跑通，但剪辑判断仍然粗糙，
尤其是目标时长、镜头粒度、内容理解、节奏判断、BGM/原音策略和成片复审。

V1-01 到 V1-08 已经把工程流水线推进到可修订、可提升、可发布的助理剪辑基础。
V2 开始的核心判断标准改为真实视频审美能力：系统必须能解释为什么选这个时长、
为什么保留或舍弃某段、为什么这个开头更强、BGM 和字幕如何影响节奏，以及第一版
哪里弱、第二版如何改。

长期路线图只在第 18 节维护；当前任务只在 `docs/CURRENT_BATCH.md` 维护。母版不再复制
每个 gate 的命令、字段、schema 或测试细节。

## 0.4 当前战略指针

当前 active gate 是 `V2-01 Real Video Aesthetic Baseline`，本地已完成并等待发布；下一完整版本是 `V2-02 Frame Composition And Reframing`。母版只记录战略边界：

- V1-01 到 V1-08 的能力现包含在保留的 `v0.30.0` 架构基线中，证明工程流水线、时长/评分/时间线、声音/BGM、复审、修订、修订提升和 release packaging 可用。
- V2-01 的目标不是新增一批文件，而是在真实视频上建立审美基线：时长推荐、高光/弱点地图、多剪辑概念、最终画幅/重构图审查、BGM/text/rhythm 风险、一版自评和二版候选。
- V2-01 的高光/弱点地图与多方案比较必须收敛为同一个审美基线：逐段绑定真实时间线/源区间、抽帧和本地声音证据，明确不确定性，并保留短版、标准版、扩展版的实质差异与用户选择权。
- 技术交付、节奏兼容和媒体 QC 只能证明文件与绑定成立，不能推出审美可发布；真实一版复核必须允许明确给出 `not_publishable`，并覆盖旧阈值规则漏掉的构图、选段、等长节奏、双音乐冲突和结尾问题。
- 第二版候选必须以用户明确选择的 concept id 为入口，把选段、结构、裁切、逐镜头重构图、源音频/BGM、文字、转场、停顿和结尾作为联动动作；缺少明确选择时只能准备能力，不能暗选方案或声称已生成真实二版。
- 当前真实样片以 `runs/chenhaoyu_klein_blue` 和《克莱因蓝的独白》项目为主验收对象；合成 fixture 只能证明稳定性，不能证明审美成熟。
- V2 之后允许复用宿主 Agent、本地模型、搜索、image2 或第三方工具，但必须显式记录来源、成本/公开性假设、可替代路径和验证边界；涉及付费能力默认放弃。
- Skill 分发包不得携带本地 `runs/`、`output/`、`.artist-portrait/` 状态或可重建缓存；本地
  样片证据保持可见，但缓存必须可由 `cleanup` 清理并从源素材重建。Git 历史中的大媒体对象
  只能通过单独审批的历史重写处理，不能用隐藏或普通删除伪装为已解决。
- 不再把具体命令字段、schema、测试、局部修复或单个 JSON 文件写进母版当作战略进度。当前批次任务写入 `docs/CURRENT_BATCH.md`，当前状态写入 `docs/DEVELOPMENT_PROGRESS.md`，发布事实写入 `docs/RELEASES.md`，机器镜像写入 `docs/current_progress.json`。

当前验收阶段和后续 V2-01 的可数任务、验收标准及 JSON 治理要求只在 `docs/CURRENT_BATCH.md` 维护。V2-V4 长线阶段表在第 18 节维护。

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
13. **BGM 不是最后装饰层，而是视听结构的一部分。**

补充说明：

- 系统不得默认所有视频都以 BGM、BPM 或卡点为中心。
- 一旦输出方案使用 BGM，BGM 必须与文字、视频节奏、镜头停留、转场、原声和情绪曲线协同设计。
- 不同输出目标需要不同 BGM 策略：高燃短视频、人物肖像、采访纪实、舞台表演和角色混剪不能使用同一套音乐逻辑。
- 后续提案、时间线、review 和 preview 阶段必须能够解释 BGM 选择理由、入点/出点、节拍或段落对齐、ducking 与原声保留策略。
- BGM 输入不得假设为单独音频文件。用户可能直接上传音频、上传一个需要提取音轨的视频、指定现有素材中的音轨、一次提供多个候选文件，或暂时不提供 BGM。
- 从视频提取音轨只证明获得了该视频的混合音频，不证明获得了干净 BGM。系统必须保留原视频引用、提取时间范围和音轨信息，并标记其中可能存在的人声、对白、现场声、环境声、音效或版权不确定性。
- 用户提供的视频既可能是“只借用其中音乐”的 BGM 来源，也可能是需要保留原声的画面素材；两种用途不得因文件类型相同而混淆。

## 1.2.1 BGM 输入来源契约

后续 BGM/timeline gate 至少必须支持：

```text
direct_audio
video_audio_extract
source_embedded_audio
multiple_candidates
none_yet
```

每个音乐候选必须保留：

```text
music_candidate_id
input_mode
source_ref
source_media_kind
extract_in
extract_out
audio_stream_index
content_hash
duration
rights_status
contains_speech
contains_vocals
contains_environment
contains_sound_effects
user_intent
analysis_status
```

规则：

- `direct_audio`：直接上传的音频文件，可作为完整曲目或局部候选。
- `video_audio_extract`：从用户上传视频的指定音轨与时间范围确定性提取。
- `source_embedded_audio`：复用素材库中已有视频/音频的原声或音乐段。
- `multiple_candidates`：保留多个候选，按不同提案或输出版本分别评估，不得过早覆盖。
- `none_yet`：允许先完成无具体曲目的节奏与声音结构设计，后续再绑定音乐。
- 提取、转码、分离与分析产物放入可重建 cache；原始上传文件和候选身份必须可追溯。
- 未执行人声/音乐分离时，禁止把视频混合音轨标记为 instrumental、clean BGM 或纯伴奏。

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
│   ├── ENGINEERING_SPEC_V0.md
│   ├── DEVELOPMENT_PROGRESS.md
│   ├── CURRENT_BATCH.md
│   ├── ISSUES.md
│   ├── DECISIONS.md
│   ├── RELEASES.md
│   └── current_progress.json
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
| `scan` | 扫描媒体、哈希、ffprobe、导入 CSV、记录扫描证据 | `sources.jsonl`、`scan_report.md` |
| `segment` | 固定窗口切分当前 source ledger；不做场景检测或转写 | `clips.jsonl`、`clip_report.md` |
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

阶段 A 仅检测 FFmpeg / ffprobe，不要求它们存在才能完成 `init`。V0-003 的 `scan` 命令正式要求 FFmpeg / ffprobe 存在。

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

## 16.3 V0-003：媒体扫描基础收口

- 对齐 Stage A 已验收和当前媒体扫描 gate。
- `scan` 写入 `sources.jsonl` 与 `scan_report.md`。
- `status`、`doctor`、`review` 识别 scan report 和下游失效状态。
- 重扫后如果 `sources.jsonl` 变化，旧 `material_map.md` 和 `risk_report.md` 对应步骤必须标记为 `invalidated`。
- 仍不得执行 PySceneDetect、Whisper、OpenCV、模型调用、联网搜索、image generation/editing、BGM 选择、创作提案、时间线或预览。

验收：

- `scan` 缺 FFmpeg / ffprobe 返回固定依赖错误。
- 有 FFmpeg / ffprobe 时真实小媒体 fixture 可扫描。
- scan report 可重建、可审计、包含边界声明。
- 文件移动、重复、同路径替换和 supersedes 行为稳定。
- 下游失效可被 `status` / `doctor` / `run_checks.py` 检出。

## 16.4 V0-004：固定窗口切分基础

- `segment` 读取 `sources.jsonl`。
- 对视频和音频统一使用固定窗口切分。
- 生成 canonical `clips.jsonl`。
- 生成 rebuildable `clip_report.md`。
- 保留 source_id、source hash、source fingerprint、原始时间码、切分方法和方法版本。
- 稳定生成 `clip_id`。
- `status`、`doctor`、`review` 识别 clip report、invalid clips ledger 和下游失效状态。
- 重扫后如果 `sources.jsonl` 变化，旧 `clips.jsonl` / `clip_report.md` 对应步骤必须标记为 `invalidated`。
- 当前 V0-004 不调用 PySceneDetect、Whisper、OpenCV、模型、联网、image generation/editing、BGM 选择、创作提案、时间线或预览。

验收：

- `segment` 缺 `scan` 返回固定前置错误。
- 25 秒素材按 10 秒窗口生成 3 个 clips。
- 音频素材也可固定窗口切分。
- clip report 可重建、可审计、包含边界声明。
- invalid `clips.jsonl` 可被 `status` / `doctor` 检出。
- `scan` 更新 source ledger 后，旧 segment/map/review 状态可被 invalidated。

## 16.5 V0-005：PySceneDetect 场景切分闸门

- 视频受 `features.scene_detection` 控制：
  - `off`：只使用固定窗口。
  - `auto`：有 PySceneDetect 时使用场景切分，缺失或失败时固定窗口并警告。
  - `required`：PySceneDetect 缺失或失败时命令失败。
- 音频继续使用固定窗口，直到转写 gate 打开。
- 记录场景检测工具版本、失败模式、降级路径和 `ClipMethod`。
- PySceneDetect 输出只作为本地工具边界证据，不构成视觉理解、创意判断、BGM 策略或时间线决策。
- 仍不得执行 Whisper、OpenCV、模型调用、联网搜索、image generation/editing、BGM 选择、创作提案、时间线或预览。

验收：

- `scene_detection: off` 稳定生成 `fixed_window` clips。
- `scene_detection: auto` 且缺少 PySceneDetect 时固定窗口回退并写入 warning。
- `scene_detection: auto` 且 PySceneDetect 可用时生成 `pyscenedetect` clips。
- `scene_detection: required` 且缺少或失败时返回固定依赖错误。
- `status` / `doctor` / `clip_report.md` 能暴露方法、回退或依赖问题。

## 16.6 V0-006：转写

- 受 `features.transcription` 控制：
  - `off`：标记 `transcribe` 为 `skipped`，不创建伪造 `transcripts.jsonl`。
  - `auto`：有本地 faster-whisper 和本地模型时转写；缺失或失败时 `skipped` 并警告。
  - `required`：faster-whisper 缺失或本地模型加载/转写失败时命令失败。
- 生成 canonical `.artist-portrait/data/transcripts.jsonl`。
- 生成可回溯 source_id、source hash、source fingerprint、时间戳、文本、语言、方法、方法版本、置信度和 word timestamps。
- faster-whisper 必须本地运行，不得触发模型下载或联网。
- ASR 只能证明“听到了什么”，不能独立证明文本属于采访、歌词、角色台词、字幕或旁白。
- `status` / `doctor` 能暴露 transcripts summary、invalid transcripts ledger、required dependency missing 和 transcribe invalidated。
- `scan` 更新 source ledger 后，旧 `transcribe` 状态必须标记为 `invalidated`。
- 仍不得执行 OpenCV、视觉模型、Embedding、模型调用、联网搜索、image generation/editing、BGM 选择、创作提案、时间线或预览。

验收：

- `transcribe` 缺 `scan` 返回固定前置错误。
- `transcription: off` 不写 `transcripts.jsonl`，step 为 `skipped`。
- `transcription: auto` 且缺少 faster-whisper 时跳过并写入 warning。
- `transcription: required` 且缺少 faster-whisper 或本地模型失败时返回固定依赖错误。
- 本地 adapter 返回 segments 时写入合法 `TranscriptRecord`。
- invalid `transcripts.jsonl` 可被 `status` / `doctor` 检出。
- `scan` 更新 source ledger 后，旧 transcribe 状态可被 invalidated。

## 16.7 V0-007：关键帧与缓存

- `keyframes` 读取当前 `clips.jsonl`。
- 为每个视频 clip 抽取一个确定性中点关键帧。
- 关键帧图片写入 `.artist-portrait/cache/keyframes/`。
- canonical `keyframes.jsonl` 记录 keyframe_id、clip_id、source_id、source hash、clip fingerprint、timestamp、image_path、method、method_version 和 evidence。
- 音频 clip 不要求关键帧，允许生成空 keyframe manifest 并警告。
- 缓存可安全删除重建；canonical 不依赖缓存图片永久存在。
- 缓存缺失由 `doctor` 作为可重建 warning 报告。
- `scan` 或 `segment` 更新上游 ledger 后，旧 `keyframes` 状态必须标记为 `invalidated`。
- 关键帧只代表视觉采样，不得推断景别、镜头运动、情绪、画质、人物身份或可用性。
- 仍不得执行 OpenCV、视觉模型、Embedding、模型调用、联网搜索、image generation/editing、BGM 选择、创作提案、时间线或预览。

验收：

- `keyframes` 缺 `segment` 返回固定前置错误。
- 视频 clip 缺 ffmpeg 返回固定依赖错误。
- 视频 clip 可生成合法 `KeyframeRecord` 和缓存图片。
- 音频-only clips 生成空 `keyframes.jsonl` 并 warning。
- invalid `keyframes.jsonl` 可被 `status` / `doctor` 检出。
- 缓存图片缺失可被 `doctor` 检出并建议重建。
- `scan` 或 `segment` 更新上游 ledger 后，旧 keyframes 状态可被 invalidated。

## 16.8 V0-008：基础分析

- `analyze` 读取当前 `clips.jsonl`。
- 若存在 `transcripts.jsonl`，可引用 transcript refs 作为文本/原声证据。
- 若存在 `keyframes.jsonl`，可引用 keyframe refs 作为视觉采样证据。
- canonical `analysis.jsonl` 记录 analysis_id、clip_id、source_id、source hash、clip fingerprint、analysis fingerprint、时间边界、素材类型、原声可用性、transcript refs、keyframe refs、risk flags 和 evidence。
- `analysis_report.md` 只是从 `analysis.jsonl` 渲染的人类可读报告，不是 canonical。
- V0-008 只允许 level_0/1/2 evidence-only 分析：
  - 素材类型可继承 `SourceRecord.source_type`。
  - 原声可用性可由 ffprobe audio_present 和 transcript refs 推导。
  - 风险标记可由 source risk、缺 transcript、缺 keyframe、audio-only、short clip 等确定性条件生成。
- 景别、镜头运动、基础情绪、动作候选和画质在当前 gate 不得被视觉分类；字段必须保持 `null` 或空候选，并标记 `method: not_run_current_gate`。
- 所有字段都必须带 `method / level / confidence / evidence`。
- `scan`、`segment`、`transcribe` 或 `keyframes` 更新上游 ledger 后，旧 `analyze` 状态必须标记为 `invalidated`。
- `analyze` 更新后，旧 `map` 和 `review_project` 状态必须标记为 `invalidated`。
- invalid `analysis.jsonl` 必须可被 `status` / `doctor` 检出。
- 仍不得执行 OpenCV、视觉模型、Embedding、模型调用、联网搜索、image generation/editing、BGM 选择、创作提案、时间线或预览。

验收：

- `analyze` 缺 `segment` 返回固定前置错误。
- 当前 clips 可生成合法 `AnalysisRecord`。
- `analysis.jsonl` 和 `analysis_report.md` 均可写入。
- 景别、镜头运动、情绪、动作和画质不得被伪造分类。
- invalid `analysis.jsonl` 可被 `status` / `doctor` 检出。
- 上游 source、clip、transcript、keyframe ledger 变化后，旧 analyze 状态可被 invalidated。
- analyze 更新后，旧 map / review_project 状态可被 invalidated。

## 16.9 V0-009：素材地图

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

实现边界：

- `map` 必须读取当前 `analysis.jsonl`，不得退回 source-only map。
- `material_map.md` 是从 `sources.jsonl` 与 `analysis.jsonl` 渲染的 rebuildable 报告，不是 canonical 数据。
- 优先查看片段只能基于证据覆盖、风险标记、时长和待确认项等确定性规则排序。
- 待确认项必须明确列出尚未打开 gate 的字段，例如景别、镜头运动、情绪、动作和画质。
- 风险项必须回指 `clip_id` / `source_id` / evidence，不得生成无证据判断。
- 仍不得执行 OpenCV、视觉模型、Embedding、模型调用、联网搜索、image generation/editing、BGM 选择、创作提案、时间线或预览。

验收：

- `map` 缺 `analyze` 返回固定前置错误。
- `map` 从合法 `analysis.jsonl` 生成 `output/material_map.md`。
- `material_map.md` 包含素材分布、优先查看队列、判断依据、待确认项和风险项。
- `analysis.jsonl` 变化后旧 map 状态可被 invalidated。

## 16.10 V0-010：创作提案

生成：

```text
.artist-portrait/data/proposals.json
output/proposals.md
```

三套方案必须结构不同、证据可回溯且不使用禁用素材。

### 16.10a V0-010a：提案就绪闸门

当前小版本只允许实现提案就绪面，不允许生成完整创作提案。

允许：

- `ProposalSet` Pydantic 模型和 `schemas/proposal_set.schema.json`。
- `status` / `doctor` 可识别存在但非法的 `.artist-portrait/data/proposals.json`。
- `propose` 必须要求 `output/material_map.md` 已存在。
- `propose` 必须检测获批文本模型能力。
- 无获批文本模型时，`propose` 必须写入 blocked step ledger、run metadata 和 warning，返回固定 dependency 错误。
- 无获批文本模型时，`propose` 不得写入 `.artist-portrait/data/proposals.json` 或 `output/proposals.md`。
- 上游 source、clip、transcript、keyframe、analysis 或 material map 变化后，旧 proposal 状态必须可被 invalidated。

禁止：

- fake proposals
- template proposals
- model-free creative proposals
- BGM selection、beat analysis、music recommendation 或 music/timeline fitting
- timeline draft
- preview render
- OpenCV、vision model、embedding、network search、image generation/editing
- 未经 gate 批准的文本模型调用

验收：

- 缺 `map` 时，`propose` 返回固定前置错误。
- 缺文本模型时，`propose --json` 返回 blocked 状态和固定 dependency 错误。
- 缺文本模型时，不存在 `proposals.json` 和 `proposals.md`。
- 非法 `proposals.json` 可被 `status` / `doctor` 检出。
- committed JSON Schema 与 live Pydantic schema 一致。

### 16.10b V0-010b：提案上下文闸门

当前小版本只允许生成未来提案模型调用的确定性输入包，不允许调用模型或生成提案。

生成：

```text
.artist-portrait/data/proposal_context.json
```

允许：

- `ProposalContext` Pydantic 模型和 `schemas/proposal_context.schema.json`。
- `propose` 在阻塞前写入合法 `proposal_context.json`。
- context 必须包含 project brief、content policy、三套固定 proposal id、source/clip/analysis 摘要、material map 指纹、证据 refs、约束、BGM 需求和 blocked capabilities。
- BGM 只作为未来 proposal/timeline 必须考虑的约束写入，不得做曲目选择、节拍分析或时间线 fitting。
- `status` / `doctor` 可识别存在但非法的 `proposal_context.json`。

禁止：

- 文本模型调用
- fake/template/model-free proposals
- 完整创作提案生成
- BGM selection、beat analysis、music recommendation 或 music/timeline fitting
- timeline draft
- preview render

验收：

- `propose --json` 缺文本模型时仍返回 blocked 和固定 dependency 错误。
- blocked `propose` 写入合法 `proposal_context.json`。
- blocked `propose` 仍不得写入 `proposals.json` 或 `proposals.md`。
- context 中必须携带 BGM requirements，但不得携带具体曲目选择。
- 非法 `proposal_context.json` 可被 `status` / `doctor` 检出。

### 16.10c V0-011：宿主 Agent 提案 handoff 与候选提升

当前提案链只保留真实的三段边界：

- `propose` 从本地 source、clip、analysis、score 与 material map 构建
  `.artist-portrait/data/proposal_context.json`，并写
  `output/proposal_agent_handoff.json`。
- 当前 Codex/ChatGPT 宿主 Agent 基于 handoff 生成一个 `ProposalSet` 候选；CLI
  不调用模型、网络、API key 或付费 provider。
- `propose --agent-output <candidate.json>` 先以原始字节写入 quarantine，再做
  schema、来源、事实、素材、差异化、BGM 策略与风险校验；仅 error 为零时原子写入
  `.artist-portrait/data/proposals.json` 与
  `.artist-portrait/data/proposal_validation.json`。

不得生成 provider registry、模拟 adapter handshake、审批请求/记录、执行就绪计划、
input bundle、provider dry-run、执行 authorization、响应接收/校验计划、promotion
计划或空的 provider result。它们不能提升剪辑能力，且会制造状态与 schema 维护负担。

### 16.10 Foundation 收口规则（不新增能力闸门）

V0-010t 之后不得继续用“再增加一个 blocked packet”冒充任务进度。进入真实
provider/model 执行前，proposal foundation 必须先满足以下工程收口条件：

- 所有 proposal artifact 的 canonical path、状态键和非法产物诊断来自单一注册表。
- `status` 与 `doctor` 必须验证跨产物引用，而不只验证单文件 schema。
- 必须检测 missing dependency、wrong ref、project identity conflict、upstream
  fingerprint stale 和 duplicate ledger output refs。
- 上游 material map 或 proposal context 变化后，旧 proposal 链不得继续显示为可信。
- 健康链与破坏性故障链必须有独立 integration tests。
- canonical 安装模拟必须执行 proposal 链完整性检查。

完成这些条件只代表 proposal 基础设施可进入下一次 gate 评审，不代表已经允许
model call、network access、provider execution、raw output capture、proposal
generation、promotion 或 canonical proposal write。

工程进度与能力进度必须分开记录。`docs/current_progress.json` 是当前
machine-readable 进度快照：任务完成只能改变 task status；任何能力闸门变化必须
同时修改 `capability_gate`、母版允许范围、AGENTS.md 和对应 contract tests。
不得因为完成维护、重构或测试任务，就把 proposal generation、timeline、BGM
analysis、preview 或其他禁用能力标成已开放。

Proposal JSON artifact 读取必须由独立 IO 模块统一执行。所有 canonical proposal
artifact model 必须进入同一 typed registry，保持稳定的 invalid JSON 错误前缀；
`workspace.py` 只允许保留兼容包装，不得重新直接读取这些 JSON 文件。状态摘要
路由必须覆盖完整 artifact registry，避免新增 artifact 后漏接 `status` 或
`doctor`。

现有 `proposals.json` 的确定性 review 不得只做 schema 和引用存在性检查。每套
提案必须具备 story structure、visual motif、minimum viable timeline、唯一的
required clips，以及 clip/analysis/material-map 证据闭环。safe、advanced、
risky 三套提案的 story 与 sound structure 不得完全相同。BGM 策略必须同时说明
编辑用途和至少一种可执行的混音或节奏手段；只写“有 BGM”不算策略。该规则只
验证已有提案，不生成、不修复、不排序提案。

提案还必须与当前 creative brief 保持一致：theme、audience 不得漂移，标题不得
重复，每套必须列出风险并回答至少一个反方案挑战。ProposalSet 顶层 evidence
必须绑定当前 proposal context，引用必须唯一且有效。三套 visual motifs 不得
完全相同。任何 proposal 文本或 evidence ref 都不得泄漏 `/Users/...`、
`/home/...`、Windows drive 或其他绝对本地路径。

Proposal review 还必须执行内容政策和证据语义检查：fake、template、mock、
model-free、dummy 等方法不得作为提案来源；禁用 source 不得通过 source/clip
fact ref 绕过；analysis fact ref 必须属于 required clip，且每个有效 required
clip 必须有对应 analysis 证据。`missing_material` 不得把当前 context 已存在 ID
声称为缺失。三套 counter proposal 不得复用同一句挑战。若
`content_policy.allow_music: false`，sound structure 必须明确采用无新增音乐、
原声、人声或留白策略，不得继续规划 BGM。

下一次大版本评审应直接决定是否开放 evidence-grounded creative proposal
generation。未开放前，不再增加 transaction recovery、retry planning 或其他只
记录 `blocked` 的中间 packet。

### 16.10.1 开发批次硬约束

后续开发必须按“最终验收阶段”或“版本结果”计数，不得按代码改动数、字段数、
文件数或测试数机械计数。每个实施批次开始前必须先确定下一大版本方向，并满足
以下两种条件之一：

- 选择一个已命名的 final-acceptance stage，并关闭该阶段的项目级验收缺口。
- 或列出至少十个彼此独立、可计数的版本任务。

以下结果可独立计作版本任务：

- 增加可运行的端到端 pipeline behavior
- 增加用户可感知的 workflow behavior
- 开放并验证一个新的 capability gate
- 关闭一个直接阻碍最终成片目标的 acceptance gap
- 完成一个达到发布级别的 contract、quality、architecture 或 hardening 结果
- 完成一个已命名 final-acceptance stage 的核心验收目标

字段、schema、测试、重构和修 bug 不按工作类型一刀切，而按规模和版本作用判定。
以下零碎或配套工作禁止单独计作任务、版本或进度：

- 增删孤立字段
- 单独增加一个局部 schema、model、packet、manifest 或 blocked artifact
- 增加单项测试、fixture、文档或验证命令
- 局部重构、拆文件、registry、wrapper、改名、格式化或清理
- 当前任务过程中顺手发现并修复的普通 bug
- 单独增加 status、doctor、diagnostic 或 proposal review 规则

上述工作只有在同时满足以下条件时，才可作为大版本任务：

- 属于一个已命名的大版本里程碑
- 有独立、发布级的验收标准
- 范围足够大，具有跨模块影响或发布关键性
- 能改变能力就绪度、发布安全性或最终目标完成度
- 没有被人为拆成多个字段、schema、测试、重构或 bug 小项

可计数的典型例子包括：完整的版本化数据契约迁移、系统性验收或评测工程、为下一
能力开放服务的架构重构、重大缺陷收口或发布加固。单个字段、单条测试、一次拆文件
或一个顺手修复的 bug 不计数。

每批结束必须报告最终目标完成度的前后变化，而不是只报告修改文件数或测试数。
如果当前 gate 无法支持一个真实 final-acceptance stage 或十个真实版本任务，
必须停止实现，明确提出所需 gate promotion 和下一个能力里程碑，等待用户批准；
不得用字段、packet、测试、文档、重构或 review 规则凑满任务数。

V0-010 foundation 与 proposal review 已关闭普通扩展。除非修复 critical
regression/security issue，或用户明确指定该项，否则不得继续扩充 V0-010
packet、schema、review rule 或 diagnostic。正常下一步必须是实际 capability gate promotion。

## 16.11 V0-012：用户选定提案后的规范时间线

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

硬约束：

- 用户必须显式选择 `proposal_safe`、`proposal_advanced` 或
  `proposal_risky`；系统不得自动替用户决定。
- 时间线只可引用当前 canonical `proposals.json`、`clips.jsonl` 和
  `sources.jsonl` 中存在且一致的对象。
- 时间线可以记录 `none_yet` 或 policy-disabled 音乐槽，不得因为尚未上传
  BGM 而阻塞画面结构生成。
- 本 gate 不执行 BGM 选择、提取、分离、节拍分析、推荐或 fitting。
- 本 gate 不执行 preview/render，不访问网络，不调用付费或远程模型。

## 16.12 V0-012：整体验收

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

## V1：成熟审美助理剪辑师

V1 不再以“能导出 MP4”为核心目标；V0 已经证明这一点。V1 的核心目标是建立真正的
剪辑判断：目标时长、内容取舍、镜头粒度、声音策略、节奏推进、成片复审和用户修改闭环。

阶段：

1. `V1-01` 时长决策与剪辑 Brief：用户可指定时长；未指定时系统基于素材、平台和题材
   推荐短/中/长版本。
2. `V1-02` 内容理解与片段评分：引入转写、音频能量、镜头变化、关键帧聚类和片段价值
   评分，替代固定 10 秒窗口。
3. `V1-03` 审美时间线生成器：已发布；生成 hook/build/payoff canonical timeline，并解释保留、舍弃与 source continuity。
4. `V1-04` 声音与 BGM 决策：已发布；把原音、BGM、视频提取音频、ducking、停顿、转场和结尾
   统一进声音策略。
5. `V1-05` 成片复审与人工二次改稿计划：已发布；审片、发现弱点，并生成 manual second-pass action plan，不声称已应用剪辑。
6. `V1-06` 用户修改闭环：支持“短一点、节奏更强、保留某段、换结尾、少点字幕”等自然
   修改意图，并生成可比较版本。
7. `V1-07` 受控修订应用：已发布；把明确选择的修订候选变成可审查的 revised timeline candidate。
8. `V1-08` 修订提升与 V1 release packaging：现包含在 `v0.30.0` 架构基线；把明确修订应用提升为 canonical timeline，并让 preview/final 重新绑定 revised timeline。

目标：可用且有审美判断的助理剪辑师。最小可用 V1 预计 2-3 周；更接近成熟剪辑师的
体验预计 4-6 周，前提是允许复用成熟转写、视觉、节奏和模型/Agent 能力并保留验证边界。

## V2：真实视频审美剪辑基线

V2 的目标不是继续证明流水线能跑，而是让系统在真实视频上形成可复盘的剪辑判断。
验收必须绑定真实样片，默认主样片为《克莱因蓝的独白》。合成 fixture 只能验证稳定性，
不能作为审美成熟证据。

阶段：

1. `V2-01` Real Video Aesthetic Baseline：为主样片建立审美验收闭环。系统必须读取真实
   视频项目证据，推荐 30/45/60/90 秒候选时长，生成高光/弱点/开头/结尾/BGM 风险审美
   标注，审查最终画幅内的主体占比、上下栏/贴片/水印侵入和安全重构图候选，提出 2-3 个
   可比较剪辑方案，并写出“为什么这么剪”和“哪里可能不好”。
2. `V2-02` Frame Composition And Reframing：把真实画面布局变成可执行的编辑约束。系统必须
   识别或由 Agent 明确标注主体安全区、持久上下栏/贴片/水印、无效留白、横竖画幅冲突和
   允许的裁切/重构图候选；不得把裁切建议声称为已渲染效果。
3. `V2-03` Transcript / Vision / Audio Evidence Fusion：把转写、画面关键帧/场景、音频
   能量/静默/掌声/音乐、人声重叠和用户目标合成一个 evidence map。缺失某一路证据时必须
   显式降级，不能伪造视觉语义、歌词、情绪或 BPM。
4. `V2-04` Highlight, Hook, Ending Scoring：建立真实片段评分器。每个候选片段必须有
   hook 分、情绪分、信息密度分、画面可用分、声音可用分、节奏分、结尾余韵分和风险扣分；
   开头和结尾不能再只是时间线首尾窗口。
5. `V2-05` Duration And Structure Recommendation：根据素材密度、用户平台、BGM 情况和
   高光分布推荐短版、标准版、延展版时长，并解释哪些内容会牺牲、哪些情绪会保留。
6. `V2-06` BGM Mood And Rhythm Matching：把用户上传音频、视频提取音频、源视频内嵌音频、
   无 BGM 四种模式纳入同一审美判断。输出 mood fit、rhythm risk、ducking pressure、
   text timing pressure、transition pressure，不自动选择付费音乐，不把混合视频音频当干净 BGM。
7. `V2-07` Text, Subtitle, And On-Screen Timing Plan：规划标题、字幕、强调字、停顿、空镜
   和屏幕文字节奏。每条文字必须绑定片段、进入/退出时机、阅读风险和是否会压住表演。
8. `V2-08` First-Cut Aesthetic Self-Review：第一版 preview/final 之后，系统必须自评开头、
   中段拖沓、情绪断裂、BGM 压人声、字幕过密、结尾无力、转场突兀，并给出证据引用。
9. `V2-09` Second-Cut Candidate Generation：根据自评和用户目标生成第二版候选，不只列
   问题。候选必须说明具体替换片段、压缩/延长原因、BGM/字幕/转场连带影响和预期改善。
10. `V2-10` Real Video Benchmark Pack：建立不少于三类真实样片基准：舞台人物、访谈/口播、
   活动/宣传混剪。每个基准保留输入、目标、审美检查表、失败样例和验收报告，防止只会剪
   单一素材。
11. `V2-11` V2 Release：发布真实视频审美基线版本。release 必须证明至少一个真实样片从
    输入到第二版候选闭环跑通，并且没有把 schema、字段、测试、重构或 bugfix 当成独立阶段。

V2 完成标准：系统能产出可讨论的第一版和有方向的第二版候选。它不要求直接达到专业成片，
但必须能明确解释审美取舍，而不是只证明文件齐全。

## V3：成熟剪辑师工作流

V3 的目标是把 V2 的单项目审美判断变成可持续的人机共剪工作流。

阶段：

1. `V3-01` Multi-Version Creative Strategies：同一素材自动生成情绪版、燃向版、叙事版、
   人物高光版等策略包，并解释每版牺牲了什么。
2. `V3-02` Style Templates：沉淀舞台人物、访谈人物、活动混剪、短视频口播、宣传片、
   纪实人物等风格模板。模板包含结构、节奏、BGM、字幕密度、转场克制程度和验收标准。
3. `V3-03` Interactive Revision Semantics：把“更高级一点、节奏快点、少点字、别压人声、
   更有情绪、结尾更有力量”等自然语言转成具体剪辑动作，并追踪动作是否真的应用。
4. `V3-04` A/B Version Review：自动比较两个或多个版本的 hook、情绪线、信息密度、
   BGM 冲突、字幕负担、结尾力量和平台适配性。
5. `V3-05` NLE Round-Trip Plus：提升 FCPXML / Resolve / Premiere 交付。目标不是只导出
   占位工程，而是让剪辑师能在 NLE 中 relink、查看 marker、理解 cue sheet，并继续精修。
6. `V3-06` Publishability Tiers：输出可预览、可发布、需人工精修、不可用四类质量结论，
   并明确阻塞原因和下一步修复命令。
7. `V3-07` Personal/Subject Memory：为公开人物或项目沉淀可审计创作记忆：常用风格、
   禁用镜头、偏好 BGM、字幕风格、封面方向、过往用户修改偏好。
8. `V3-08` V3 Release：发布成熟剪辑助理工作流版本。验收必须包含多版本生成、人类修改、
   A/B 复审和 NLE handoff。

## V4：导演型创作系统

V4 的目标是从“剪辑助理”升级为“导演型创作系统”：能根据素材和目标提出创作概念，并协调
剪辑、声音、文字、封面、文案和交付包。

阶段：

1. `V4-01` Theme Discovery：从素材中反推主题、人物弧光、冲突、反差和可传播钩子。
2. `V4-02` Concept Pitch Generation：输出多个剪辑概念 pitch，包括标题方向、叙事结构、
   声音策略、视觉风格和风险。
3. `V4-03` Nonlinear Story Design：支持倒叙、悬念、延迟动作完成、声画错位、视觉押韵、
   情绪反差等导演式结构，而不是只按时间顺序拼接。
4. `V4-04` External Creative Tool Orchestration：在用户允许时调用搜索、image2、第三方
   音频/视觉/转写工具、本地模型或其他 skill。所有外部能力必须记录来源、成本、版权/公开性
   假设和可替代路径；涉及付费能力默认放弃。
5. `V4-05` Cover, Copy, And Distribution Package：输出成片之外的封面方向、标题、简介、
   平台版本、发布说明和修改建议。
6. `V4-06` Director Review Loop：系统先提出导演意见，再生成剪辑方案，再自评，再做二次版；
   人类可以在概念、结构、片段、音乐、字幕、封面任一层级介入。
7. `V4-07` V4 Release：发布导演型创作系统版本。验收必须证明不只是剪视频，还能提出并执行
   创作概念。

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

本文档是产品愿景、产品边界、非目标和模型原则的唯一优化母版；
`ENGINEERING_SPEC_V0.md` 只负责工程实现规范。

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
