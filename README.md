# 实验2 · 数据看板的设计与实现（云栖优选销售看板）

Streamlit + Pandas + Plotly 实现的单页销售数据看板，覆盖实验要求的基础任务、进阶任务与扩展任务。
数据为脚本生成的模拟电商订单（2026-01-01 ~ 2026-09-30），含 5 类脏数据，用于演示预处理流程。

实验博客：[Python Vibe Coding 实验 2：用 Streamlit + Plotly 搭一个能用的销售数据看板](blog/Python-Vibe-Coding-lab2.md)

## 快速开始

```bash
pip install -r requirements.txt
python data/generate_dataset.py      # 生成含脏数据的原始订单 data/raw_orders.csv
python data/clean_data.py            # 清洗，输出 data/orders_clean.csv 与 clean_report.json
python -m streamlit run app.py       # 打开 http://localhost:8501
```

跑测试：

```bash
python -m pytest tests -v
```

## 目录结构

```
dashboard-lab2/
├─ app.py                     # 看板主程序（四大区域 + 进阶/扩展功能）
├─ src/metrics.py             # 统计口径（KPI、趋势、占比、排行、热力、目标达成）
├─ data/
│  ├─ generate_dataset.py     # 模拟数据生成（含脏数据注入）
│  ├─ clean_data.py           # 清洗流水线 + 清洗报告
│  ├─ raw_orders.csv          # 原始脏数据 3810 行
│  ├─ orders_clean.csv        # 清洗后 3729 行
│  └─ clean_report.json       # 逐步骤剔除统计
├─ tests/                     # 31 条单元测试（清洗规则 19 条 + 统计口径 12 条）
├─ 截图/                       # 8 张真实运行截图 + 版面草图
├─ blog/                      # 实验博客（Markdown）与配图
├─ 实验报告.docx               # 实验报告
├─ 验证记录.md                 # 生成 / 清洗 / 测试 / 截图核对记录
├─ logs/                      # 生成、清洗、测试的真实终端输出
├─ requirements.txt
└─ README.md
```

## 功能清单

| 层级 | 内容 |
| --- | --- |
| 基础任务 | 需求分析与四区布局、配色方案；数据生成与清洗；KPI 卡片、品类条形图、月度折线图、渠道环形图；单页整合；结果验证 |
| 进阶任务 | 渐入动画与 hover 提示、宽屏自适应；时间/品类/渠道/地区四维筛选；点击品类条形图联动下方趋势与明细；热力图、地区排行榜、目标完成率仪表盘 |
| 扩展任务 | 模拟实时数据流（`st.fragment(run_every=5)` 每 5 秒局部刷新）；退款率与品类下滑预警；明细 CSV / 数据报告 Markdown 导出；亮色/暗色主题切换 |

## 数据口径

| 项目 | 口径 |
| --- | --- |
| 统计区间 | 2026-01-01 ~ 2026-09-30 |
| 关键字段 | 日期、品类、渠道、地区、会员等级、数量、单价、金额 |
| 缺失处理 | 任一关键字段为空 → 整行剔除，不插补 |
| 数值异常 | 数量 ≤ 0 或 > 20、单价 ≤ 0、金额 ≤ 0 → 剔除 |
| 金额一致性 | amount 与「数量 × 单价」偏差 > 5% → 剔除，保留行按乘积重算 |
| 去重 | 全字段重复保留首次；订单号重复保留首次 |
| 客单价 | 销售额 / 订单数 |
| 退款率 | 退款订单数 / 订单数 |

清洗结果：3810 行 → 3729 行（剔除 81 行，脏数据占比 2.13%），销售额合计 1,503,956.26 元。

## 已知限制

- 实时区为「模拟接口推流」，在内存中生成订单，不写库，刷新页面后重新累计。
- 图表导出图片依赖 kaleido 与 Chrome，本仓库只提供数据与报告导出，避免额外依赖。
- 主题切换只覆盖自定义组件与图表配色，Streamlit 原生输入控件保持浏览器默认样式。
