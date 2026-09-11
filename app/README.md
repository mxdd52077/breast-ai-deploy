# APEX 珊瑚红照护平台

PC 优先、手机自适应的 React Web 界面，FastAPI + Python 确定性计算内核。新版复用 `../source/breast_roi_copilot` 中的计算、校验和检索模块；原始压缩包未修改。

## 新版机构工作流（2026-09-09）

- 数据检查：真实执行字段、重复、年龄、日期校验，展示派生规则；可下载或载入虚构CSV。人工应用人数、平均年龄、当前筛查率后，来源绑定测算方案。机构CSV上限4MB、50000行。
- AI决策助手：Kimi解析场景并生成PubMed查询；医院汇总参数优先，AI候选需要人工应用。
- 证据：实时NCBI E-utilities检索，保留PMID、标题、摘要；Kimi提取绝对DBT检出率/召回率。逐字引文、数字与单位校验后仍须人工评估适用性。没有合适候选时不编造参数。
- 参数治理：审批记录绑定账户；测算时服务端核对参数与来源数值；修改参数后前端清除过期归因；历史方案保存输入、结果、来源、情景及敏感性分析。
- 外展：支持合成人群和医院CSV；医院模式使用已保存方案的经济参数、人工确认的外展成本及基础完成概率，排除无同意或已有预约者。可导出优先顺序与原CSV行号；仅保存汇总，原始行与选择行号不写入审计库。规则分数不是已验证的癌症预测模型。
- 评估：上传不含身份信息的label/score CSV计算混淆矩阵、准确率、敏感度、特异度和F1；保存来源说明和汇总。标签质量、观察窗口和外部验证由机构负责。
- 报告：Kimi撰写说明，服务端附上原始锁定计算快照；正文数字、PMID与引文经过本地校验，失败不保存报告。人工审批后导出Markdown及完整计算、来源、审批记录。
- 长任务：场景解析、证据提取和报告生成通过NDJSON持续返回处理状态，只有通过校验的完整结果才发送给页面；瞬时模型错误最多重试一次，限流后等待再重试。连接中断可查看历史记录判断是否已完成。
- 持久化：机构工作流记录使用现有账户隔离的Audit JSON记录与Simulation表，账户删除级联清理；不新增公开数据库权限。

真实机构功能由`institution_access`权限控制。真实资料试用仍受`APEX_ALLOW_REAL_UPLOADS`控制，需完成原约定的数据生命周期、权限和服务商处理边界核验；此次未开放该开关。未接入医院系统，也不发送外部外展通知。

验证：`python -m pytest app/tests source/breast_roi_copilot/tests -q`；`python audit/verify_institution.py --local`执行真实Kimi/PubMed验证，仅使用自动清理的虚构账户。去掉`--local`针对线上环境。

## 本地启动

在项目根目录运行（当前工作区已安装依赖）：

```powershell
.venv/Scripts/python.exe -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

另开终端：

```powershell
cd app/frontend
npm run dev
```

浏览器打开 http://127.0.0.1:5173，点击“体验独立演示空间”。每次新建演示空间使用独立账户与虚构资料。演示空间仅适合虚构或脱敏文件。

首次安装：根目录创建 Python 3.12 虚拟环境，安装 `app/requirements.txt`；前端运行 `npm ci`。可选 OCR SDK 使用 `pip install paddleocr`。生产构建执行 `npm run build` 后重启 API，可通过同源 8000 端口访问静态页面。真实部署需 HTTPS 反向代理。

## API 配置

将 `.env.example` 复制为 `app/.env`，在本机编辑。密钥不要粘贴到聊天、截图、前端或版本库。

| 用途 | 配置项 | 未配置行为 |
|---|---|---|
| 照片、扫描 PDF 识别 | `BAIDU_OCR_API_KEY` + `BAIDU_OCR_SECRET_KEY` | 文件保存，提示识别尚未连接，支持重试 |
| 文档智能摘录、知识问答 | `APEX_LLM_API_KEY` | 演示账户使用本地逐行原文整理；问答返回检索原文 |
| 数据库 | `DATABASE_URL` | 本机 SQLite；境内部署改 PostgreSQL |
| 私有原件存储 | `SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY` | 本机私有目录；云端使用私有 Supabase Storage bucket |
| 真实资料入口 | `APEX_ALLOW_REAL_UPLOADS` | 默认 false，尚未开放 |

OCR 当前使用百度托管 PaddleOCR-VL 异步解析接口（`APEX_OCR_PROVIDER=baidu_paddle`），保留页码和表格。问答采用 LangGraph + Kimi K3（`kimi-k3`），使用境内接口 `https://api.moonshot.cn/v1`；前端不会收到密钥。服务商区域、留存和数据处理条款尚需核验后才能用于真实资料。

页面连接标识只表示配置存在。2026-09-06 已另外完成真实服务联调：虚构图片、两页扫描 PDF、Kimi 摘录及带引用问答均成功；报告位于 `../deliverables/verification/live-*.json`。

## 功能与边界

- 患者账户、会话、CSRF、账户隔离；服务端持久化档案。
- 上传 PDF/DOCX/TXT/图片；后台队列、失败重试、同账户内容去重。
- 摘录默认待核对；逐条确认/排除/撤回；原文来源和图片/PDF原件对照。
- 明确日期且已确认的事项生成任务；重新确认保留完成状态；日期不明不猜测。
- 照护日历、状态变更、摘要导出、来源问答与历史引用。
- 问答使用 NDJSON 流式响应：先显示检索状态，再逐段呈现回答，完成后附加经校验来源并持久化。
- 已确认的个人资料事实写入 Supabase `document_chunks` 和 `pgvector`；问答使用账户内精确余弦检索与中文关键词重排，并将个人资料、页码、核对状态和公共医学知识分开引用。
- 机构参数编辑、原 Python ROI 内核、保存和导出测算结果。

目前机构CSV质量检查、情景对照和敏感性分析已接入；文献检索、循证参数审核等工作流尚未完整迁移。Supabase PostgreSQL 与私有对象存储已完成生产接入；生产备份恢复、数据生命周期和服务商处理边界仍需在真实患者资料试用前验收。

## 验证

```powershell
.venv/Scripts/python.exe -m pytest app/tests -q
cd app/frontend
npm run build
```

测试使用临时隔离数据库与虚构数据，自动清空测试进程中的 API 配置，绝不调用真实 OCR/模型服务。当前已通过 21 个测试，包含流式协议、历史落库、确认状态门控和个人资料跨账户隔离；其中 OCR 恢复测试采用模拟响应。另有独立真实服务冒烟测试，使用虚构资料，不代表医疗识别质量评测。

## Supabase 与 Vercel

迁移文件位于 `../supabase/migrations`。Supabase 项目名为 `APEX Care`，生产运行使用 Postgres transaction pooler 连接串，并设置 `APEX_AUTO_CREATE_DB=false`；原件存入私有 `patient-documents` bucket。`SUPABASE_SERVICE_ROLE_KEY` 只放在 Vercel 服务端环境变量，不能以 `VITE_` 或其他公开前缀暴露。

个人资料检索使用 `pgvector 0.8.2` 的 384 维向量。当前规模采用精确 KNN，不创建近似向量索引；向量由应用内 `apex-zh-char-v1` 生成，不把原文额外发送给第三方 Embedding 服务。每次查询都同时限制 `user_id` 和 `review_status=confirmed`。

仓库根目录的 `index.py`、`requirements.txt` 和 `vercel.json` 是 Vercel 入口。生产站点为 `https://apex-care-tan.vercel.app`，部署区域配置为新加坡，Python Function 最长运行 300 秒，支持 FastAPI 流式响应。Vercel 已配置 `DATABASE_URL`、Supabase Storage、百度 OCR、Kimi、`APEX_ALLOW_DEMO`、`APEX_ALLOW_REAL_UPLOADS` 和 `APEX_AUTO_CREATE_DB`；所有密钥均为服务端 Secret。

DOCX 解析还包含嵌套表格与嵌入图片OCR；图片缺少OCR配置时整份文件保留并提示失败重试，避免静默漏读。DOCX来源是逻辑片段，不能当作物理页码。

配置检查：`.venv/Scripts/python.exe -m app.backend.check_config`。此命令只输出配置是否存在，不显示密钥、不调用外部API。
