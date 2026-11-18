# -*- coding: utf-8 -*-
"""云栖优选 · 销售数据看板（实验2：数据看板的设计与实现）。

启动：python -m streamlit run app.py
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.metrics import (  # noqa: E402
    build_text_report,
    category_mom_drop,
    category_month_matrix,
    category_summary,
    channel_share,
    filter_orders,
    kpi_summary,
    load_orders,
    member_summary,
    mom_growth,
    monthly_trend,
    region_rank,
    target_achievement,
)

st.set_page_config(
    page_title="云栖优选 · 销售数据看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CLEAN_PATH = ROOT / "data" / "orders_clean.csv"
REPORT_PATH = ROOT / "data" / "clean_report.json"

PALETTES = {
    "亮色": {
        "bg": "#f2f5fa", "card": "#ffffff", "text": "#16233a", "sub": "#5c6b85",
        "line": "#e3eaf4", "grid": "#e8edf6", "primary": "#2563eb", "accent": "#0f9d8f",
        "warn": "#d9480f", "danger": "#c92a2a", "ok": "#0b8f5a",
        "hero1": "#0f2f7a", "hero2": "#2563eb", "hero3": "#0ea5a4",
        "series": ["#2563eb", "#0f9d8f", "#f59f00", "#7c5cf0", "#e8590c", "#2f9e44"],
        "plot_bg": "rgba(0,0,0,0)", "hover": "#ffffff",
    },
    "暗色": {
        "bg": "#0b1220", "card": "#131c2e", "text": "#e8edf7", "sub": "#98a6c0",
        "line": "#22304a", "grid": "#1d2a42", "primary": "#4c8dff", "accent": "#2dd4bf",
        "warn": "#ff922b", "danger": "#ff6b6b", "ok": "#37b26c",
        "hero1": "#0a1730", "hero2": "#1d4ed8", "hero3": "#0f766e",
        "series": ["#4c8dff", "#2dd4bf", "#ffc061", "#a78bfa", "#ff8e6e", "#5dd39e"],
        "plot_bg": "rgba(0,0,0,0)", "hover": "#1b2740",
    },
}

CSS_TEMPLATE = """
<style>
:root {
  --bg: __BG__; --card: __CARD__; --text: __TEXT__; --sub: __SUB__;
  --line: __LINE__; --primary: __PRIMARY__; --accent: __ACCENT__;
}
.stApp { background: var(--bg); }
#MainMenu { visibility: hidden; }
[data-testid="stAppDeployButton"] { display: none; }
header[data-testid="stHeader"] { background: rgba(0, 0, 0, 0); }
.block-container { padding-top: 1.1rem; padding-bottom: 2.5rem; max-width: 1480px; }
html, body, [class*="css"] { font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif; }

@keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }

.dash-hero {
  display: flex; justify-content: space-between; align-items: flex-end; gap: 24px;
  padding: 22px 28px; border-radius: 20px; color: #fff;
  background: linear-gradient(118deg, __HERO1__ 0%, __HERO2__ 58%, __HERO3__ 100%);
  box-shadow: 0 16px 38px rgba(15, 40, 90, .22); animation: rise .7s ease both;
}
.dash-hero h1 { margin: 0; font-size: 1.72rem; letter-spacing: .02em; font-weight: 700; }
.dash-hero p { margin: 8px 0 0; font-size: .86rem; opacity: .82; }
.hero-meta { text-align: right; font-size: .78rem; line-height: 1.7; opacity: .9; white-space: nowrap; }
.hero-tag { display: inline-block; margin-top: 6px; padding: 3px 10px; border-radius: 999px;
  background: rgba(255,255,255,.16); font-size: .72rem; }

.sec { display: flex; align-items: center; gap: 10px; margin: 26px 0 10px; animation: fade .6s ease both; }
.sec-bar { width: 4px; height: 18px; border-radius: 3px; background: __PRIMARY__; }
.sec-title { font-size: 1.02rem; font-weight: 700; color: var(--text); }
.sec-sub { font-size: .76rem; color: var(--sub); }

.kpi-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }
.kpi-card {
  background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 15px 18px 14px; box-shadow: 0 8px 22px rgba(16, 36, 74, .07);
  animation: rise .55s ease both;
}
.kpi-label { font-size: .76rem; color: var(--sub); letter-spacing: .08em; }
.kpi-value { margin-top: 7px; font-size: 1.66rem; font-weight: 700; color: var(--text);
  font-variant-numeric: tabular-nums; letter-spacing: -.01em; }
.kpi-unit { font-size: .78rem; font-weight: 500; color: var(--sub); margin-left: 4px; }
.kpi-delta { display: inline-flex; align-items: center; gap: 4px; margin-top: 9px;
  padding: 2px 9px; border-radius: 999px; font-size: .74rem; font-weight: 600; }
.up { color: __OK__; background: rgba(11, 143, 90, .12); }
.down { color: __DANGER__; background: rgba(201, 42, 42, .12); }
.flat { color: var(--sub); background: rgba(120, 135, 160, .12); }
.kpi-note { margin-top: 8px; font-size: .72rem; color: var(--sub); }

.rank { background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 16px 18px; box-shadow: 0 8px 22px rgba(16, 36, 74, .07); animation: rise .65s ease both; }
.rank-head { display: flex; justify-content: space-between; font-size: .78rem; color: var(--sub); margin-bottom: 10px; }
.rank-row { display: grid; grid-template-columns: 24px 64px 1fr 92px; align-items: center;
  gap: 10px; padding: 7px 0; font-size: .82rem; color: var(--text); }
.rank-no { width: 20px; height: 20px; line-height: 20px; text-align: center; border-radius: 6px;
  font-size: .72rem; font-weight: 700; color: #fff; background: var(--primary); }
.rank-no.grey { background: rgba(120, 135, 160, .45); }
.rank-track { height: 8px; background: rgba(120, 135, 160, .16); border-radius: 999px; overflow: hidden; }
.rank-bar { height: 8px; border-radius: 999px; background: linear-gradient(90deg, __PRIMARY__, __ACCENT__); }
.rank-val { text-align: right; font-variant-numeric: tabular-nums; color: var(--sub); font-size: .78rem; }

.alert-box { background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 14px 18px; box-shadow: 0 8px 22px rgba(16, 36, 74, .07); animation: rise .7s ease both; }
.alert-row { display: flex; gap: 10px; align-items: flex-start; padding: 9px 0; border-bottom: 1px dashed var(--line); }
.alert-row:last-child { border-bottom: none; }
.dot { width: 9px; height: 9px; border-radius: 50%; margin-top: 6px; flex: 0 0 auto; }
.dot-red { background: __DANGER__; box-shadow: 0 0 0 4px rgba(201, 42, 42, .14); }
.dot-amber { background: __WARN__; box-shadow: 0 0 0 4px rgba(217, 72, 15, .14); }
.dot-green { background: __OK__; box-shadow: 0 0 0 4px rgba(11, 143, 90, .14); }
.alert-text { font-size: .82rem; color: var(--text); line-height: 1.6; }
.alert-text span { color: var(--sub); font-size: .76rem; display: block; }

.chip { display: inline-flex; align-items: center; gap: 8px; padding: 5px 12px; border-radius: 999px;
  background: rgba(37, 99, 235, .12); color: var(--primary); font-size: .78rem; font-weight: 600; }
.mono { font-variant-numeric: tabular-nums; }
.footnote { font-size: .74rem; color: var(--sub); margin-top: 6px; }
div[data-testid="stMetric"] { background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; padding: 12px 16px; }
div[data-testid="stMetricLabel"] { color: var(--sub); }
section[data-testid="stSidebar"] { background: var(--card); border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] .stMarkdown { color: var(--text); }
</style>
"""


@st.cache_data(show_spinner=False)
def get_orders(path_str: str, mtime: float) -> pd.DataFrame:
    return load_orders(Path(path_str))


@st.cache_data(show_spinner=False)
def get_clean_report(path_str: str, mtime: float) -> dict:
    p = Path(path_str)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def style_fig(fig: go.Figure, pal: dict, title: str = "", height: int = 340) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Microsoft YaHei, PingFang SC, sans-serif", size=12, color=pal["text"]),
        margin=dict(l=8, r=8, t=44 if title else 14, b=8),
        hoverlabel=dict(bgcolor=pal["hover"], bordercolor=pal["line"],
                        font=dict(color=pal["text"], size=12)),
        showlegend=False,
    )
    if title:
        fig.update_layout(title=dict(text=title, x=0.02, y=0.97, xanchor="left",
                                     font=dict(size=14.5, color=pal["text"])))
    fig.update_xaxes(gridcolor=pal["grid"], zeroline=False, linecolor=pal["line"],
                     tickfont=dict(size=11.5))
    fig.update_yaxes(gridcolor=pal["grid"], zeroline=False, linecolor=pal["line"],
                     tickfont=dict(size=11.5))
    return fig


def section(title: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="sec"><div class="sec-bar"></div><div class="sec-title">{title}</div>'
        f'<div class="sec-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def kpi_cards(items: list[dict]) -> None:
    cards = []
    for it in items:
        delta_html = ""
        if it.get("delta") is not None:
            cls = "up" if it["delta"] > 0 else ("down" if it["delta"] < 0 else "flat")
            arrow = "▲" if it["delta"] > 0 else ("▼" if it["delta"] < 0 else "—")
            delta_html = f'<div class="kpi-delta {cls}">{arrow} {abs(it["delta"]):.2%}</div>'
        note_html = f'<div class="kpi-note">{it["note"]}</div>' if it.get("note") else ""
        cards.append(
            f'<div class="kpi-card"><div class="kpi-label">{it["label"]}</div>'
            f'<div class="kpi-value">{it["value"]}<span class="kpi-unit">{it.get("unit", "")}</span></div>'
            f"{delta_html}{note_html}</div>"
        )
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def rank_panel(rows: list[tuple[str, float, float]]) -> str:
    body = []
    top = max((r[1] for r in rows), default=1.0) or 1.0
    for i, (name, value, share) in enumerate(rows, 1):
        no_cls = "" if i <= 3 else " grey"
        width = max(6.0, value / top * 100)
        body.append(
            f'<div class="rank-row"><span class="rank-no{no_cls}">{i}</span>'
            f'<span>{name}</span><div class="rank-track"><div class="rank-bar" style="width:{width:.1f}%"></div></div>'
            f'<span class="rank-val">{value / 10000:.1f} 万 ({share:.1%})</span></div>'
        )
    return (
        '<div class="rank"><div class="rank-head"><span>地区销售排行</span><span>销售额 / 占比</span></div>'
        + "".join(body)
        + "</div>"
    )


def make_live_order(rng: random.Random) -> dict:
    cats = ["数码配件", "家居日用", "美妆个护", "运动户外", "食品生鲜", "图书文创"]
    chans = ["自营商城", "小程序", "直播间", "第三方平台"]
    regs = ["华东", "华南", "华北", "西南", "华中"]
    qty = rng.choices([1, 2, 3], weights=[0.7, 0.22, 0.08], k=1)[0]
    price = round(rng.uniform(39, 780), 2)
    now = datetime.now()
    return {
        "时间": now.strftime("%H:%M:%S"),
        "订单号": f"LIVE{now:%H%M%S}{rng.randint(10, 99)}",
        "品类": rng.choice(cats),
        "渠道": rng.choice(chans),
        "地区": rng.choice(regs),
        "金额": round(qty * price, 2),
    }


@st.fragment(run_every=5)
def live_panel(enabled: bool) -> None:
    if not enabled:
        st.caption("在侧边栏打开「模拟实时数据流」后，本区域每 5 秒自动刷新，其余区域保持不动。")
        return

    state = st.session_state.setdefault("live_orders", [])
    rng = random.Random()
    state.extend([make_live_order(rng) for _ in range(2)])
    del state[:-24]
    live = pd.DataFrame(state)
    total = float(live["金额"].sum())
    st.markdown(
        f'<div class="kpi-grid" style="grid-template-columns:repeat(3,minmax(0,1fr));">'
        f'<div class="kpi-card"><div class="kpi-label">实时累计销售额</div>'
        f'<div class="kpi-value">{total:,.2f}<span class="kpi-unit">元</span></div>'
        f'<div class="kpi-note">每 5 秒自动追加 2 笔订单</div></div>'
        f'<div class="kpi-card"><div class="kpi-label">实时订单量</div>'
        f'<div class="kpi-value">{len(live)}<span class="kpi-unit">单</span></div>'
        f'<div class="kpi-note">仅保留最近 24 笔</div></div>'
        f'<div class="kpi-card"><div class="kpi-label">最近刷新</div>'
        f'<div class="kpi-value" style="font-size:1.3rem;">{datetime.now():%H:%M:%S}</div>'
        f'<div class="kpi-note">st.fragment(run_every=5s)</div></div></div>',
        unsafe_allow_html=True,
    )
    st.dataframe(live.tail(6).iloc[::-1], hide_index=True, height=232,
                 column_config={"金额": st.column_config.NumberColumn(format="%.2f")})


def main() -> None:
    if not CLEAN_PATH.exists():
        st.error("缺少清洗后的数据文件，请先运行：python data/generate_dataset.py 与 python data/clean_data.py")
        st.stop()

    # ---------- 侧边栏：全局筛选 ----------
    st.sidebar.markdown("### 看板控制台")
    theme = st.sidebar.radio("界面主题", ["亮色", "暗色"], horizontal=True)
    pal = PALETTES[theme]
    st.markdown(
        CSS_TEMPLATE.replace("__BG__", pal["bg"]).replace("__CARD__", pal["card"])
        .replace("__TEXT__", pal["text"]).replace("__SUB__", pal["sub"])
        .replace("__LINE__", pal["line"]).replace("__PRIMARY__", pal["primary"])
        .replace("__ACCENT__", pal["accent"]).replace("__HERO1__", pal["hero1"])
        .replace("__HERO2__", pal["hero2"]).replace("__HERO3__", pal["hero3"])
        .replace("__OK__", pal["ok"]).replace("__DANGER__", pal["danger"])
        .replace("__WARN__", pal["warn"]),
        unsafe_allow_html=True,
    )

    df_all = get_orders(str(CLEAN_PATH), CLEAN_PATH.stat().st_mtime)
    report = get_clean_report(str(REPORT_PATH), REPORT_PATH.stat().st_mtime if REPORT_PATH.exists() else 0.0)

    min_day = df_all["order_date"].min().date()
    max_day = df_all["order_date"].max().date()

    start, end = st.sidebar.date_input(
        "统计区间", value=(min_day, max_day), min_value=min_day, max_value=max_day, format="YYYY-MM-DD"
    )
    if isinstance(start, tuple):
        start, end = start
    cats = st.sidebar.multiselect("品类", sorted(df_all["category"].unique()), default=[],
                                  placeholder="全部品类")
    chans = st.sidebar.multiselect("渠道", sorted(df_all["channel"].unique()), default=[],
                                   placeholder="全部渠道")
    regs = st.sidebar.multiselect("地区", sorted(df_all["region"].unique()), default=[],
                                  placeholder="全部地区")

    st.sidebar.divider()
    monthly_target = st.sidebar.number_input("月度销售目标（元）", min_value=10000, max_value=1000000,
                                            value=180000, step=10000)
    refund_threshold = st.sidebar.slider("退款率预警阈值（%）", 3, 15, 8, 1) / 100

    st.sidebar.divider()
    live_enabled = st.sidebar.toggle("模拟实时数据流（5 秒刷新）", value=True)
    st.sidebar.caption("数据源：data/orders_clean.csv（本地离线）")

    base = filter_orders(df_all, start=start, end=end, categories=cats, channels=chans, regions=regs)

    drill = st.session_state.get("drill_cat")
    if drill and drill not in set(base["category"]):
        drill = None
        st.session_state["drill_cat"] = None

    # ---------- 顶部标题 ----------
    quality = report.get("dirty_ratio", 0.0)
    upd = datetime.fromtimestamp(CLEAN_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f'<div class="dash-hero"><div><h1>云栖优选 · 销售数据看板</h1>'
        f'<p>电商订单明细 · 2026 年 1—9 月 · 数据概览 / 维度统计 / 趋势分析 / 明细下钻</p></div>'
        f'<div class="hero-meta">数据更新：{upd}<br>有效订单 {len(df_all):,} 行 · 清洗剔除 {quality:.2%}'
        f'<br><span class="hero-tag">Streamlit + Pandas + Plotly</span></div></div>',
        unsafe_allow_html=True,
    )

    # ---------- 一、数据概览区 ----------
    section("数据概览区", "五张核心指标卡：总量、订单、客单价、退款、环比")
    kpis = kpi_summary(base)
    growth = mom_growth(base)
    kpi_cards([
        {"label": "总销售额", "value": f"{kpis['total_amount'] / 10000:,.1f}", "unit": "万元",
         "delta": growth, "note": f"筛选后 {len(base):,} 单"},
        {"label": "订单量", "value": f"{kpis['orders']:,}", "unit": "单",
         "note": f"日均 {kpis['orders'] / max((end - start).days + 1, 1):.1f} 单"},
        {"label": "客单价", "value": f"{kpis['avg_order_value']:,.0f}", "unit": "元",
         "note": "销售额 / 订单量"},
        {"label": "退款金额", "value": f"{kpis['refund_amount'] / 10000:,.2f}", "unit": "万元",
         "note": f"退款率 {kpis['refund_rate']:.2%}"},
        {"label": "环比增长", "value": f"{growth:+.1%}", "delta": None,
         "note": "末月 vs 上月销售额"},
    ])

    # ---------- 二、维度统计区 ----------
    section("维度统计区", "点击左侧条形图可直接联动下方趋势与明细")
    cats_df = category_summary(base)
    share_df = channel_share(base)
    rank_df = region_rank(base, top_n=5)
    mem_df = member_summary(base)

    view = base if not drill else base[base["category"] == drill]
    if drill:
        st.markdown(
            f'<span class="chip">已联动：品类 = {drill}</span>', unsafe_allow_html=True
        )
        if st.button("清除联动", type="secondary", key="clear_drill"):
            st.session_state["drill_cat"] = None
            st.rerun()

    col1, col2, col3 = st.columns([5, 3, 4], gap="medium")
    with col1:
        desc_order = list(cats_df.sort_values("amount", ascending=False)["category"])
        bar_colors = [pal["series"][desc_order.index(c) % len(pal["series"])] for c in cats_df["category"]]
        fig_bar = go.Figure(
            go.Bar(
                x=cats_df["amount"] / 10000,
                y=cats_df["category"],
                orientation="h",
                marker=dict(color=bar_colors, line=dict(width=0)),
                text=[f"{v / 10000:.1f} 万" for v in cats_df["amount"]],
                textposition="outside",
                textfont=dict(size=11.5, color=pal["sub"]),
                hovertemplate="%{y}<br>销售额 %{x:.1f} 万元<extra></extra>",
            )
        )
        fig_bar = style_fig(fig_bar, pal, "各品类销售额（万元）", height=386)
        fig_bar.update_xaxes(title=None, range=[0, max(cats_df["amount"] / 10000) * 1.36])
        fig_bar.update_layout(margin=dict(l=78, r=52, t=50, b=28))
        ev = st.plotly_chart(fig_bar, width="stretch", theme=None, key="chart_category",
                             on_select="rerun", selection_mode="points",
                             config={"displayModeBar": False})
        clicked = None
        try:
            pts = ev["selection"]["points"]  # type: ignore[index]
            if pts:
                clicked = pts[0].get("y") or pts[0].get("label")
        except Exception:  # 未发生选择时结构不同
            clicked = None
        if clicked and clicked != st.session_state.get("drill_cat"):
            st.session_state["drill_cat"] = clicked
            st.rerun()

    with col2:
        fig_donut = go.Figure(
            go.Pie(labels=share_df["channel"], values=share_df["amount"], hole=0.52,
                   marker=dict(colors=[pal["series"][i % len(pal["series"])] for i in range(len(share_df))]),
                   textinfo="percent", textfont=dict(size=11.5, color=pal["text"]),
                   hovertemplate="%{label}<br>%{value:,.0f} 元（%{percent}）<extra></extra>")
        )
        fig_donut = style_fig(fig_donut, pal, "渠道销售额占比", height=386)
        fig_donut.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.16, x=0,
                                            font=dict(size=11, color=pal["sub"])))
        st.plotly_chart(fig_donut, width="stretch", theme=None, config={"displayModeBar": False})

    with col3:
        rows = [(r["region"], float(r["amount"]), float(r["share"])) for _, r in rank_df.iterrows()]
        st.markdown(rank_panel(rows), unsafe_allow_html=True)
        if not mem_df.empty:
            st.markdown(
                f'<div class="footnote">会员维度：{mem_df.iloc[-1]["member_level"]} 客单价最高，'
                f'{mem_df.iloc[-1]["avg_order_value"]:,.0f} 元 / 单</div>',
                unsafe_allow_html=True,
            )

    # ---------- 三、趋势分析区 ----------
    section("趋势分析区", "月度走势 + 目标完成率")
    trend = monthly_trend(view)
    target = target_achievement(view, monthly_target)

    c1, c2 = st.columns([8, 4], gap="medium")
    with c1:
        fig_line = go.Figure()
        fig_line.add_trace(go.Bar(x=trend["month"], y=trend["orders"], name="订单量",
                                  marker=dict(color=pal["grid"], line=dict(width=0)),
                                  hovertemplate="%{x}<br>订单量 %{y} 单<extra></extra>"))
        fig_line.add_trace(go.Scatter(x=trend["month"], y=trend["amount"] / 10000, name="销售额",
                                      mode="lines+markers", yaxis="y2",
                                      line=dict(color=pal["primary"], width=3),
                                      marker=dict(size=7, color=pal["primary"]),
                                      hovertemplate="%{x}<br>销售额 %{y:.1f} 万元<extra></extra>"))
        fig_line = style_fig(fig_line, pal, "月度销售额与订单量", height=356)
        fig_line.update_layout(
            hovermode="x unified",
            margin=dict(l=54, r=72, t=48, b=46),
            yaxis=dict(title="订单量（单）", gridcolor=pal["grid"], tickformat=",.0f",
                       title_font=dict(size=11.5, color=pal["sub"])),
            yaxis2=dict(title="销售额（万元）", overlaying="y", side="right", showgrid=False,
                        tickformat=",.0f", title_font=dict(size=11.5, color=pal["sub"]),
                        gridcolor="rgba(0,0,0,0)"),
            legend=dict(orientation="h", y=1.16, x=0.62, font=dict(size=11.5, color=pal["sub"])),
            bargap=0.35,
        )
        fig_line.update_xaxes(type="category")
        st.plotly_chart(fig_line, width="stretch", theme=None, config={"displayModeBar": False})

    with c2:
        rate = target["rate"] * 100
        gauge_color = pal["ok"] if rate >= 100 else (pal["warn"] if rate >= 80 else pal["danger"])
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(rate, 1),
            number=dict(suffix="%", font=dict(size=30, color=pal["text"])),
            gauge=dict(
                axis=dict(range=[0, 120], tickcolor=pal["sub"], tickfont=dict(size=10)),
                bar=dict(color=gauge_color, thickness=0.28),
                bgcolor="rgba(0,0,0,0)", borderwidth=0,
                steps=[dict(range=[0, 80], color="rgba(201,42,42,.10)"),
                       dict(range=[80, 100], color="rgba(217,72,15,.10)"),
                       dict(range=[100, 120], color="rgba(11,143,90,.10)")],
                threshold=dict(line=dict(color=pal["danger"], width=3), thickness=0.8, value=100),
            ),
        ))
        fig_gauge = style_fig(fig_gauge, pal, f"{target['month']} 目标完成率", height=356)
        fig_gauge.update_layout(margin=dict(l=26, r=26, t=56, b=10))
        st.plotly_chart(fig_gauge, width="stretch", theme=None, config={"displayModeBar": False})
        st.markdown(
            f'<div class="footnote">目标 {monthly_target:,.0f} 元 · 实际 {target["amount"]:,.0f} 元</div>',
            unsafe_allow_html=True,
        )

    # ---------- 四、多维度分析 + 预警 ----------
    section("多维度分析区", "品类 × 月份热力图，定位结构性变化")
    c3, c4 = st.columns([7, 5], gap="medium")
    with c3:
        matrix = category_month_matrix(view)
        z = (matrix.values / 10000).round(1)
        fig_heat = go.Figure(go.Heatmap(
            z=z, x=list(matrix.columns), y=list(matrix.index),
            colorscale=[[0, pal["card"]], [0.45, "#93b8ff"], [1, pal["primary"]]],
            text=[[f"{v:.1f}" for v in row] for row in z],
            texttemplate="%{text}", textfont=dict(size=10.5, color=pal["text"]),
            hovertemplate="%{y} / %{x}<br>%{z:.1f} 万元<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(size=10, color=pal["sub"])),
            xgap=3, ygap=3,
        ))
        fig_heat = style_fig(fig_heat, pal, "品类 × 月份 销售额热力图（万元）", height=376)
        fig_heat.update_layout(margin=dict(l=76, r=26, t=52, b=36))
        fig_heat.update_xaxes(type="category")
        st.plotly_chart(fig_heat, width="stretch", theme=None, config={"displayModeBar": False})

    with c4:
        drops = category_mom_drop(view)
        alerts = []
        if kpis["refund_rate"] > refund_threshold:
            alerts.append(("red", f"退款率 {kpis['refund_rate']:.2%} 超过阈值 {refund_threshold:.0%}",
                           f"退款金额 {kpis['refund_amount']:,.0f} 元，建议排查高退款品类与渠道"))
        else:
            alerts.append(("green", f"退款率 {kpis['refund_rate']:.2%} 处于阈值内",
                           f"阈值 {refund_threshold:.0%}，当前无异常"))
        if target["rate"] < 0.8:
            alerts.append(("red", f"{target['month']} 目标完成率仅 {target['rate']:.1%}",
                           f"距离目标 {monthly_target:,.0f} 元还差 {monthly_target - target['amount']:,.0f} 元"))
        elif target["rate"] < 1:
            alerts.append(("amber", f"{target['month']} 目标完成率 {target['rate']:.1%}",
                           "尚未达成月度目标，末段需关注转化"))
        for cat, chg in drops[:2]:
            alerts.append(("amber", f"{cat} 环比下滑 {abs(chg):.1%}", "已触发品类下滑预警（阈值 -15%）"))
        if growth > 0:
            alerts.append(("green", f"整体环比增长 {growth:.1%}", "销售额处于上行通道"))
        body = "".join(
            f'<div class="alert-row"><div class="dot dot-{lv}"></div>'
            f'<div class="alert-text">{txt}<span>{sub}</span></div></div>'
            for lv, txt, sub in alerts
        )
        st.markdown(
            f'<div class="alert-box"><div class="rank-head"><span>数据预警与洞察</span>'
            f'<span>阈值可调</span></div>{body}</div>',
            unsafe_allow_html=True,
        )

    # ---------- 五、实时监控区（扩展1） ----------
    section("实时监控区（扩展）", "动态数据源 + 秒级自动刷新")
    live_panel(live_enabled)

    # ---------- 六、明细数据区 ----------
    section("明细数据区", "筛选后的订单明细，可导出 CSV / 数据报告")
    detail = view.sort_values("order_date", ascending=False).head(200)
    show = detail[["order_id", "order_date", "category", "channel", "region",
                   "member_level", "quantity", "unit_price", "amount", "refund_flag"]].copy()
    show["order_date"] = show["order_date"].dt.strftime("%Y-%m-%d")
    show.columns = ["订单号", "日期", "品类", "渠道", "地区", "会员等级", "数量", "单价", "金额", "退款"]
    st.dataframe(
        show, hide_index=True, height=320,
        column_config={
            "单价": st.column_config.NumberColumn(format="%.2f"),
            "金额": st.column_config.NumberColumn(format="%.2f"),
            "退款": st.column_config.CheckboxColumn(),
        },
    )

    dl1, dl2, dl3 = st.columns([2, 2, 6])
    with dl1:
        st.download_button(
            "导出明细 CSV",
            data=view.to_csv(index=False).encode("utf-8-sig"),
            file_name="dashboard_orders.csv",
            mime="text/csv",
            width="stretch",
        )
    with dl2:
        st.download_button(
            "导出数据报告 MD",
            data=build_text_report(view, kpi_summary(view), target_achievement(view, monthly_target)).encode("utf-8"),
            file_name="dashboard_report.md",
            mime="text/markdown",
            width="stretch",
        )
    with dl3:
        st.markdown(
            f'<div class="footnote">当前筛选：{start} ~ {end} ｜ 品类 {len(cats) or "全部"} ｜ '
            f'渠道 {len(chans) or "全部"} ｜ 地区 {len(regs) or "全部"} ｜ 联动 {drill or "无"}</div>',
            unsafe_allow_html=True,
        )

    if report:
        with st.expander("数据处理说明（清洗日志）"):
            st.json(report.get("steps", []), expanded=False)


if __name__ == "__main__":
    main()

