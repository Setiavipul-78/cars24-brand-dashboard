"""Cars24 Brand Key Metrics — v3 · Streamlit dashboard."""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from pathlib import Path
from glob import glob
import base64

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Brand Key Metrics",
    page_icon="assets/cars24-logo-blue.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={},
)

# ── Brand tokens ─────────────────────────────────────────────────────────────
C24_BLUE    = "#4736FE"
C24_MINT    = "#63FFB1"
C24_BLACK   = "#020618"
C24_WHITE   = "#FFFFFF"
C24_GREY_BG = "#F8F8FC"
C24_BORDER  = "#E3E1FF"
C24_BLUE_LT = "#EEF0FF"
C24_BLUE_MED= "#2B2098"
C24_GREEN   = "#00C951"
C24_RED_FB  = "#FB2C36"
C24_ORANGE  = "#FF4F01"
C24_TEXTGREY= "#6B7280"
C24_MINT_DK = "#1A7A50"

SPINNY_COLOR  = "#E91E8C"
CARWALE_COLOR = "#FF6B6B"
DEKHO_COLOR   = "#FFA500"
MFC_COLOR     = "#9B59B6"
MTV_COLOR     = "#2ECC71"
OLX_COLOR     = "#3498DB"

BRAND_COLORS = {
    "Cars24": C24_BLUE, "Spinny": SPINNY_COLOR, "CarWale": CARWALE_COLOR,
    "Cardekho": DEKHO_COLOR, "MFC": MFC_COLOR, "MTV": MTV_COLOR, "OLX": OLX_COLOR,
}
BRAND_DISPLAY = {
    "Cars24": "Cars24", "Spinny": "Spinny", "CarWale": "CarWale",
    "Cardekho": "Cardekho", "MFC": "Mahindra First Choice",
    "MTV": "Maruti True Value", "OLX": "OLX Auto",
}
def bdisplay(b): return BRAND_DISPLAY.get(b, b)

CORE_CATS     = ["Cars24","Cars24 Buy","Cars24 Sell","Cars24 Cities",
                 "Cars24 + Car Model","Cars24 Customer Care"]
ANCILLARY_CATS= ["Cars24 Challan","PDI","ELITE","Others"]
ALL_B         = ["Cars24","CarWale","Cardekho","MFC","MTV"]
ALL_B_7       = ["Cars24","Spinny","CarWale","Cardekho","MFC","MTV","OLX"]

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html,body,[class*="css"]{{font-family:'Inter',-apple-system,sans-serif!important;color:{C24_BLACK}}}
*{{box-sizing:border-box}}
[data-testid="stSidebar"],[data-testid="collapsedControl"]{{display:none!important}}
[data-testid="stHeader"]{{display:none!important}}
.main .block-container{{padding:0 0 3rem!important;max-width:100%!important}}
[data-testid="stAppViewContainer"]{{background:#F4F3FF;padding-top:0!important}}
/* Remove Streamlit's internal top gap so banner truly starts at y=0 */
.main>div:first-child{{padding-top:0!important}}
section[data-testid="stMain"]>div:first-child{{padding-top:0!important}}
[data-testid="stVerticalBlock"]>div:first-child>div:first-child{{margin-top:0!important}}
.element-container:first-of-type{{margin-top:0!important}}

/* ── Banner ─────────────────────────────────────────────────────────────── */
.c24-banner{{background:linear-gradient(135deg,{C24_BLUE} 0%,{C24_BLUE_MED} 100%);
  border-bottom:3px solid {C24_MINT};padding:14px 32px;color:white;
  display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:999;width:calc(100% + 8rem);
  margin:-1px -4rem 0;box-shadow:0 4px 24px rgba(71,54,254,.35)}}
.banner-title{{font-size:18px;font-weight:800;letter-spacing:-0.3px;
  color:white;line-height:1;margin-left:16px}}
.banner-right{{text-align:right;font-size:11px;opacity:.85;line-height:1.7}}
.banner-right strong{{opacity:1;font-weight:700;color:{C24_MINT}}}

/* ── Overview strip (replaces mband) ───────────────────────────────────── */
.overview-strip{{display:grid;grid-template-columns:1fr 1fr 1fr;
  background:{C24_WHITE};box-shadow:0 2px 8px rgba(71,54,254,.05)}}
.ov-metric{{padding:28px 36px;border-top:4px solid;position:relative;overflow:hidden}}
.ov-metric:not(:last-child){{border-right:1px solid {C24_BORDER}}}
.ov-metric::before{{content:'';position:absolute;top:0;left:0;right:0;height:80px;
  background:linear-gradient(180deg,rgba(71,54,254,.03) 0%,transparent 100%);pointer-events:none}}
.ov-lbl{{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;
  color:{C24_TEXTGREY};margin-bottom:12px}}
.ov-value{{font-size:52px;font-weight:900;color:{C24_BLACK};line-height:1;letter-spacing:-2.5px}}
.ov-value .ov-unit{{font-size:28px;font-weight:700;letter-spacing:0;color:{C24_TEXTGREY}}}
.ov-badge{{display:inline-flex;align-items:center;gap:4px;padding:5px 14px;
  border-radius:20px;font-size:13px;font-weight:700;margin-top:12px}}
.ov-badge-up{{background:#D1FAE5;color:#065F46}}
.ov-badge-down{{background:#FEE2E2;color:#991B1B}}
.ov-badge-flat{{background:{C24_BLUE_LT};color:{C24_BLUE}}}
.ov-sub{{font-size:11px;color:{C24_TEXTGREY};margin-top:5px}}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"]{{background:{C24_WHITE};border-radius:0;padding:0 32px;
  gap:0;border-bottom:3px solid {C24_BORDER};margin:0;box-shadow:none}}
.stTabs [data-baseweb="tab"]{{border-radius:0;font-weight:600;font-size:13px;
  padding:14px 20px;color:{C24_TEXTGREY};border-bottom:3px solid transparent;
  transition:color .15s,border-color .15s;background:transparent!important;
  margin-bottom:-3px;letter-spacing:.1px;
  border-top:none!important;border-left:none!important;border-right:none!important}}
.stTabs [data-baseweb="tab"]:hover{{color:{C24_BLUE};background:rgba(71,54,254,.03)!important}}
.stTabs [aria-selected="true"]{{color:{C24_BLUE}!important;font-weight:800!important;
  border-bottom-color:{C24_BLUE}!important;background:transparent!important}}
.stTabs [data-baseweb="tab-panel"]{{padding:24px 32px 0;background:#F4F3FF}}

/* ── Chart auto-card (wraps every Plotly chart) ─────────────────────────── */
[data-testid="stPlotlyChart"]{{background:{C24_WHITE};border-radius:14px;
  border:1px solid {C24_BORDER};box-shadow:0 2px 12px rgba(71,54,254,.06);
  padding:16px 12px 8px;margin-bottom:4px;overflow:hidden}}

/* ── Hero ───────────────────────────────────────────────────────────────── */
.hero-wrap{{background:{C24_WHITE};border-radius:16px;padding:24px 28px;
  box-shadow:0 2px 16px rgba(71,54,254,.07);margin-bottom:20px;
  border-top:4px solid {C24_BLUE}}}
.hero-kicker{{font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.8px;color:{C24_TEXTGREY};margin-bottom:8px}}
.hero-num{{font-size:52px;font-weight:900;color:{C24_BLUE};line-height:1;
  letter-spacing:-2px;display:inline}}
.hero-month{{font-size:14px;font-weight:500;color:{C24_TEXTGREY};
  margin-left:12px;vertical-align:middle}}
.hero-deltas{{margin-top:12px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
.dp{{display:inline-flex;align-items:center;gap:3px;padding:5px 14px;
  border-radius:20px;font-size:13px;font-weight:700}}
.dp-up{{background:#D1FAE5;color:{C24_MINT_DK}}}
.dp-down{{background:#FEE2E2;color:#991B1B}}
.dp-flat{{background:{C24_BLUE_LT};color:{C24_BLUE}}}
.ath-badge{{background:{C24_MINT};color:{C24_BLACK};border-radius:12px;
  padding:4px 12px;font-size:11px;font-weight:800;letter-spacing:.3px}}

/* ── Section headers ────────────────────────────────────────────────────── */
.sec-wrap{{margin:24px 0 10px;display:flex;align-items:baseline;gap:10px}}
.sec-kicker{{font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.8px;color:{C24_BLUE};margin-bottom:3px}}
.sec-title{{font-size:16px;font-weight:700;color:{C24_BLACK};
  border-left:3px solid {C24_MINT};padding-left:10px;line-height:1.4}}
.sec-badge{{font-size:10px;color:{C24_TEXTGREY};background:{C24_GREY_BG};
  padding:3px 10px;border-radius:20px;border:1px solid {C24_BORDER};
  font-weight:600;letter-spacing:.3px;white-space:nowrap}}

/* ── KPI cards ──────────────────────────────────────────────────────────── */
.kpi-card{{background:{C24_WHITE};border:1px solid {C24_BORDER};border-radius:14px;
  padding:18px 20px;box-shadow:0 2px 12px rgba(71,54,254,.06);
  border-top:3px solid {C24_BLUE}}}
.kpi-card.green{{border-top-color:{C24_GREEN}}}
.kpi-card.orange{{border-top-color:{C24_ORANGE}}}
.kpi-card.pink{{border-top-color:{SPINNY_COLOR}}}
.kpi-card.mint{{border-top-color:{C24_MINT}}}
.kpi-card.purple{{border-top-color:#9B59B6}}
.kpi-lbl{{font-size:10.5px;font-weight:700;color:{C24_TEXTGREY};
  text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}}
.kpi-val{{font-size:28px;font-weight:800;color:{C24_BLACK};
  line-height:1;letter-spacing:-.5px}}
.kpi-sub{{font-size:11.5px;color:{C24_TEXTGREY};margin-top:5px}}
.kpi-sparkline{{margin-top:8px}}

/* ── Ranked leaderboard list ─────────────────────────────────────────────── */
.rank-card{{background:{C24_WHITE};border-radius:14px;border:1px solid {C24_BORDER};
  box-shadow:0 2px 12px rgba(71,54,254,.06);overflow:hidden;margin-bottom:4px}}
.rank-card-accent{{height:3px;background:{C24_BLUE}}}
.rank-card-hd{{display:flex;justify-content:space-between;align-items:center;
  padding:14px 18px 10px;border-bottom:1px solid #F0EEFF}}
.rank-card-title{{font-size:15px;font-weight:700;color:{C24_BLACK}}}
.rank-card-sub{{font-size:12px;color:{C24_TEXTGREY};padding:6px 18px 10px}}
.rank-card-badge{{font-size:10px;color:{C24_TEXTGREY};background:#F4F3FF;
  padding:3px 10px;border-radius:20px;border:1px solid {C24_BORDER};font-weight:600}}
.rank-item{{display:flex;align-items:center;gap:14px;padding:11px 18px;
  border-bottom:1px solid #F8F7FF;transition:background .12s;cursor:default}}
.rank-item:hover{{background:#F8F7FF}}
.rank-item:last-child{{border-bottom:none}}
.rnum{{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-weight:700;font-size:11px;flex-shrink:0}}
.rnum-1{{background:{C24_BLUE};color:white}}
.rnum-2{{background:#6B5EFF;color:white}}
.rnum-3{{background:#8B7FFF;color:white}}
.rnum-4{{background:#B8B5FF;color:{C24_BLUE}}}
.rnum-5{{background:#D4D2FF;color:{C24_BLUE}}}
.rnum-x{{background:{C24_GREY_BG};color:{C24_TEXTGREY}}}
.rname{{flex:1;min-width:0}}
.rname-main{{font-weight:600;font-size:13px;color:{C24_BLACK};
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rname-sub{{font-size:11px;color:{C24_TEXTGREY};margin-top:1px}}
.rval{{font-weight:700;font-size:14px;flex-shrink:0;text-align:right}}
.rval-arrow{{font-size:11px;font-weight:600;margin-left:8px}}

/* ── Insight + warn ─────────────────────────────────────────────────────── */
.ibox{{background:linear-gradient(90deg,{C24_BLUE_LT},{C24_WHITE}99);
  border-left:3px solid {C24_BLUE};border-radius:0 10px 10px 0;
  padding:10px 16px;font-size:12.5px;line-height:1.65;margin:12px 0}}
.wbox{{background:#FFF8EE;border-left:3px solid {C24_ORANGE};border-radius:0 8px 8px 0;
  padding:9px 14px;font-size:12px;margin:10px 0;line-height:1.5}}

/* ── Tables ─────────────────────────────────────────────────────────────── */
table.pt{{width:100%;border-collapse:collapse;font-size:12.5px}}
table.pt thead tr{{background:{C24_GREY_BG}}}
table.pt th{{padding:9px 12px;text-align:left;font-weight:700;font-size:10.5px;
  text-transform:uppercase;color:{C24_TEXTGREY};border-bottom:2px solid {C24_BORDER};
  letter-spacing:.4px;white-space:nowrap}}
table.pt td{{padding:8px 12px;border-bottom:1px solid #F0EEFF;vertical-align:middle}}
table.pt tbody tr:hover{{background:{C24_BLUE_LT}}}
.scroll-tbl{{max-height:360px;overflow-y:auto;border:1px solid {C24_BORDER};
  border-radius:10px;background:{C24_WHITE}}}
.tbl-card{{background:{C24_WHITE};border-radius:14px;border:1px solid {C24_BORDER};
  box-shadow:0 2px 12px rgba(71,54,254,.06);overflow:hidden;margin-bottom:4px}}
.up{{color:{C24_GREEN};font-weight:700}} .down{{color:{C24_RED_FB};font-weight:700}}
.na{{color:{C24_TEXTGREY};font-style:italic}}

/* ── Category / tier badges ─────────────────────────────────────────────── */
.badge{{display:inline-flex;align-items:center;padding:2px 8px;border-radius:20px;
  font-size:11px;font-weight:600;letter-spacing:.2px}}
.badge-blue{{background:{C24_BLUE_LT};color:{C24_BLUE}}}
.badge-green{{background:#D1FAE5;color:{C24_MINT_DK}}}
.badge-orange{{background:#FEF3E2;color:#B45309}}
.badge-pink{{background:#FCE7F3;color:#9D174D}}
.badge-purple{{background:#EDE9FE;color:#5B21B6}}
.badge-gray{{background:#F3F4F6;color:#374151}}

/* ── Selectbox polish ───────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div{{
  background:{C24_WHITE}!important;border:1.5px solid {C24_BORDER}!important;
  border-radius:8px!important;font-size:13px!important}}

/* ── Home hero ──────────────────────────────────────────────────────────── */
.home-hero{{background:linear-gradient(135deg,{C24_BLUE} 0%,{C24_BLUE_MED} 55%,{C24_BLACK} 100%);
  border-radius:20px;padding:36px 40px;color:white;display:flex;
  justify-content:space-between;align-items:center;margin-bottom:20px;
  position:relative;overflow:hidden;box-shadow:0 8px 32px rgba(71,54,254,.30)}}
.home-hero::before{{content:'';position:absolute;top:-60px;right:-60px;
  width:260px;height:260px;border-radius:50%;background:rgba(99,255,177,.10)}}
.home-hero::after{{content:'';position:absolute;bottom:-40px;left:30%;
  width:180px;height:180px;border-radius:50%;background:rgba(71,54,254,.25)}}
.hh-kicker{{font-size:10.5px;font-weight:700;text-transform:uppercase;
  letter-spacing:1.2px;color:rgba(255,255,255,.65);margin-bottom:14px}}
.hh-num{{font-size:76px;font-weight:900;color:white;line-height:1;
  letter-spacing:-4px;display:flex;align-items:baseline;gap:4px}}
.hh-unit{{font-size:42px;letter-spacing:0;color:{C24_MINT};font-weight:900}}
.hh-sub{{font-size:12.5px;color:rgba(255,255,255,.55);margin-top:10px}}
.hh-pills{{margin-top:18px;display:flex;gap:10px;flex-wrap:wrap}}
.hh-pill{{display:inline-flex;align-items:center;gap:4px;padding:6px 16px;
  border-radius:24px;font-size:13px;font-weight:700;backdrop-filter:blur(4px)}}
.hh-pill-up{{background:rgba(99,255,177,.20);color:{C24_MINT};border:1px solid rgba(99,255,177,.35)}}
.hh-pill-down{{background:rgba(251,44,54,.20);color:#FF8A8F;border:1px solid rgba(251,44,54,.35)}}
.hh-pill-flat{{background:rgba(255,255,255,.12);color:rgba(255,255,255,.8);border:1px solid rgba(255,255,255,.2)}}
.hh-ath{{background:{C24_MINT};color:{C24_BLACK};border-radius:20px;
  padding:5px 14px;font-size:11px;font-weight:900;letter-spacing:.5px;
  display:inline-block;margin-left:12px;vertical-align:middle}}
.hh-right{{position:relative;z-index:1;text-align:right;min-width:200px}}
.hh-trend-lbl{{font-size:10px;color:rgba(255,255,255,.5);margin-top:6px;text-align:right}}
.hh-freshness{{font-size:10.5px;color:rgba(255,255,255,.55);margin-top:14px;line-height:1.8}}
.hh-freshness strong{{color:rgba(255,255,255,.85)}}

/* ── Home stat grid ─────────────────────────────────────────────────────── */
.stat-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.stat-cell{{background:{C24_WHITE};border-radius:14px;border:1px solid {C24_BORDER};
  box-shadow:0 2px 12px rgba(71,54,254,.06);padding:18px 20px;
  border-top:3px solid {C24_BLUE};position:relative;overflow:hidden}}
.stat-cell::after{{content:'';position:absolute;bottom:0;right:0;
  width:60px;height:60px;border-radius:50% 0 0 0;
  background:rgba(71,54,254,.04)}}
.sc-lbl{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;
  color:{C24_TEXTGREY};margin-bottom:8px}}
.sc-val{{font-size:28px;font-weight:800;line-height:1;letter-spacing:-.5px}}
.sc-delta{{margin-top:6px;font-size:12px;font-weight:700}}
.sc-sub{{font-size:11px;color:{C24_TEXTGREY};margin-top:4px}}

/* ── Home section label ─────────────────────────────────────────────────── */
.hs{{font-size:15px;font-weight:700;color:{C24_BLACK};margin:0 0 12px;
  padding-left:10px;border-left:3px solid {C24_MINT}}}
.hs-kicker{{font-size:9.5px;font-weight:700;text-transform:uppercase;
  letter-spacing:.8px;color:{C24_BLUE};margin-bottom:4px}}

/* ── Home navigation cards ──────────────────────────────────────────────── */
.hnav-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:4px}}
.hnav-card{{background:{C24_WHITE};border-radius:12px;border:1px solid {C24_BORDER};
  box-shadow:0 2px 8px rgba(71,54,254,.05);padding:16px 18px;cursor:default;
  transition:box-shadow .15s,border-color .15s}}
.hnav-card:hover{{border-color:{C24_BLUE};box-shadow:0 4px 20px rgba(71,54,254,.14)}}
.hnav-icon{{font-size:22px;margin-bottom:6px}}
.hnav-title{{font-size:13px;font-weight:700;color:{C24_BLACK}}}
.hnav-sub{{font-size:10.5px;color:{C24_TEXTGREY};margin-top:3px}}

/* ── Home insight strip ─────────────────────────────────────────────────── */
.istrip{{display:flex;gap:10px;margin:16px 0;flex-wrap:wrap}}
.istrip-card{{flex:1;min-width:180px;background:{C24_BLUE_LT};border-left:3px solid {C24_BLUE};
  border-radius:0 10px 10px 0;padding:12px 16px}}
.istrip-title{{font-size:11px;font-weight:700;color:{C24_BLUE};
  text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}}
.istrip-body{{font-size:12.5px;color:{C24_BLACK};line-height:1.55}}

/* ── Period pill radio buttons ──────────────────────────────────────────── */
.period-wrap [data-testid="stRadio"] > label{{display:none}}
.period-wrap [data-testid="stRadio"] [role="radiogroup"]{{
  display:flex!important;flex-direction:row!important;gap:5px;flex-wrap:wrap;
  background:{C24_GREY_BG};border-radius:50px;padding:4px;
  width:fit-content;border:1px solid {C24_BORDER}}}
.period-wrap [data-testid="stRadio"] div[role="radio"]{{
  display:inline-flex;align-items:center;padding:7px 18px;border-radius:50px;
  cursor:pointer;font-size:12.5px;font-weight:600;color:{C24_TEXTGREY};
  transition:all .15s;user-select:none}}
.period-wrap [data-testid="stRadio"] div[aria-checked="true"]{{
  background:{C24_BLUE};color:white;box-shadow:0 2px 8px rgba(71,54,254,.30)}}
.period-wrap [data-testid="stRadio"] p{{margin:0;font-size:12.5px}}
.period-wrap [data-testid="stRadio"] [data-baseweb="radio"] span:first-child{{display:none!important}}

/* ── Summary metrics (Tab 1 KPI strip — full-color cards) ──────────────── */
.summary-metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:16px 0 24px}}
.sm-item{{border-radius:18px;padding:26px 28px;position:relative;overflow:hidden;
  box-shadow:0 4px 24px rgba(0,0,0,.12)}}
.sm-item::after{{content:'';position:absolute;top:-40px;right:-40px;width:120px;height:120px;
  border-radius:50%;background:rgba(255,255,255,.08);pointer-events:none}}
.sm-item::before{{content:'';position:absolute;bottom:-30px;left:20px;width:80px;height:80px;
  border-radius:50%;background:rgba(255,255,255,.06);pointer-events:none}}
.sm-lbl{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
  color:rgba(255,255,255,.7);margin-bottom:14px}}
.sm-val{{font-size:40px;font-weight:900;line-height:1;letter-spacing:-1.5px;color:white}}
.sm-sub{{font-size:11.5px;color:rgba(255,255,255,.65);margin-top:10px;line-height:1.4}}
.sm-tag{{display:inline-block;margin-top:10px;background:rgba(255,255,255,.18);
  border:1px solid rgba(255,255,255,.3);border-radius:20px;padding:4px 12px;
  font-size:11px;font-weight:700;color:rgba(255,255,255,.9)}}

/* ── Context / story strip ──────────────────────────────────────────────── */
.ctx-strip{{background:linear-gradient(135deg,{C24_BLUE_LT} 0%,rgba(99,255,177,.08) 100%);
  border-radius:14px;border:1.5px solid {C24_BORDER};
  padding:18px 24px;margin:0 0 22px;box-shadow:0 2px 8px rgba(71,54,254,.06)}}
.ctx-title{{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;
  color:{C24_BLUE};margin-bottom:8px}}
.ctx-body{{font-size:13px;color:{C24_BLACK};line-height:1.75}}
.ctx-body strong{{color:{C24_BLACK};font-weight:700}}
.ctx-body em{{color:{C24_BLUE};font-style:normal;font-weight:800}}

/* ── Colored insight boxes ──────────────────────────────────────────────── */
.ibox-mint{{background:linear-gradient(90deg,rgba(99,255,177,.18),rgba(99,255,177,.04));
  border-left:4px solid {C24_MINT_DK};border-radius:0 12px 12px 0;
  padding:12px 18px;font-size:12.5px;line-height:1.7;margin:12px 0;
  box-shadow:0 2px 8px rgba(99,255,177,.12)}}
.ibox-orange{{background:linear-gradient(90deg,rgba(255,79,1,.12),rgba(255,79,1,.03));
  border-left:4px solid {C24_ORANGE};border-radius:0 12px 12px 0;
  padding:12px 18px;font-size:12.5px;line-height:1.7;margin:12px 0;
  box-shadow:0 2px 8px rgba(255,79,1,.08)}}
.ibox-green{{background:linear-gradient(90deg,rgba(0,201,81,.12),rgba(0,201,81,.03));
  border-left:4px solid {C24_GREEN};border-radius:0 12px 12px 0;
  padding:12px 18px;font-size:12.5px;line-height:1.7;margin:12px 0;
  box-shadow:0 2px 8px rgba(0,201,81,.10)}}

/* ── Section banners ────────────────────────────────────────────────────── */
.sec-banner{{border-radius:12px;padding:14px 20px;margin:28px 0 6px;
  display:flex;align-items:center;gap:14px;position:relative;overflow:hidden}}
.sec-banner::after{{content:'';position:absolute;right:-20px;top:-20px;
  width:100px;height:100px;border-radius:50%;background:rgba(255,255,255,.06)}}
.sec-banner-icon{{font-size:22px;flex-shrink:0}}
.sec-banner-title{{font-size:16px;font-weight:800;color:white;line-height:1.2}}
.sec-banner-sub{{font-size:11.5px;color:rgba(255,255,255,.7);margin-top:2px}}

/* ── Section description text ───────────────────────────────────────────── */
.sec-desc{{font-size:12.5px;color:{C24_TEXTGREY};margin:-4px 0 16px;line-height:1.6;
  padding:10px 14px;background:{C24_WHITE};border-radius:8px;
  border-left:3px solid {C24_BORDER}}}

/* ── Table color coding ─────────────────────────────────────────────────── */
.tbl-up{{background:rgba(0,201,81,.06)!important}}
.tbl-down{{background:rgba(251,44,54,.05)!important}}
.tbl-latest{{background:linear-gradient(90deg,rgba(71,54,254,.08),rgba(71,54,254,.02))!important}}

/* ── Scoreboard card (Best/Worst callout) ──────────────────────────────── */
.score-card{{border-radius:14px;padding:16px 20px;position:relative;overflow:hidden}}
.score-card::after{{content:'';position:absolute;bottom:-20px;right:-20px;
  width:80px;height:80px;border-radius:50%;background:rgba(255,255,255,.12)}}
.score-label{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;
  color:rgba(255,255,255,.75);margin-bottom:6px}}
.score-val{{font-size:24px;font-weight:900;color:white;line-height:1;letter-spacing:-.5px}}
.score-sub{{font-size:11.5px;color:rgba(255,255,255,.7);margin-top:6px}}
</style>""", unsafe_allow_html=True)

# ── Plotly helpers ────────────────────────────────────────────────────────────
_AX = dict(tickfont=dict(size=11, color=C24_BLACK), linecolor=C24_BORDER,
           linewidth=1, gridcolor="#EBEBEB")
_LAYOUT = dict(plot_bgcolor=C24_WHITE, paper_bgcolor=C24_WHITE,
               font=dict(family="Inter,sans-serif", color=C24_BLACK, size=12),
               hoverlabel=dict(bgcolor=C24_WHITE, font_size=12, font_family="Inter",
                               bordercolor=C24_BORDER))
_MARGIN = dict(t=44, b=32, l=60, r=24)

def ax(**kw):
    """Merge overrides into _AX without duplicate-key error."""
    d = dict(_AX); d.update(kw); return d

def std_layout(height=340, **kw):
    d = dict(_LAYOUT, margin=_MARGIN, height=height); d.update(kw); return d

DATA = Path("data")

# ── Utility helpers ───────────────────────────────────────────────────────────
def fmt_lakh(n):
    try: return f"{float(n)/1e5:.2f}L"
    except: return "—"

def pct_ch(curr, prev):
    try:
        if pd.isna(prev) or prev == 0: return float("nan")
        return (float(curr) - float(prev)) / abs(float(prev)) * 100
    except: return float("nan")

def pp_ch(curr, prev):
    try:
        if pd.isna(prev): return float("nan")
        return float(curr) - float(prev)
    except: return float("nan")

def month_label(m):
    try: return pd.Period(m, freq="M").strftime("%b'%y")
    except: return str(m)

def grc(v, is_pp=False):
    """Green/red colored delta cell."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '<span class="na">—</span>'
    sym = "pp" if is_pp else "%"
    cls = "up" if v > 0 else "down" if v < 0 else "na"
    arrow = "▲" if v > 0 else "▼" if v < 0 else "→"
    return f'<span class="{cls}">{arrow}{abs(v):.1f}{sym}</span>'

def pill(v, is_pp=False, label=""):
    """Colored pill badge for hero/KPI sections."""
    if v is None or (isinstance(v, float) and np.isnan(v)): return ""
    sym = "pp" if is_pp else "%"
    cls = "dp-up" if v > 0 else "dp-down" if v < 0 else "dp-flat"
    arrow = "▲" if v > 0 else "▼" if v < 0 else "→"
    pre = f"{label} " if label else ""
    return f'<span class="dp {cls}">{pre}{arrow} {abs(v):.1f}{sym}</span>'

def ibox(text, icon=""):
    """Insight box — returns empty string if text is empty."""
    if not text: return ""
    return f'<div class="ibox">{icon+" " if icon else ""}{text}</div>'

def wbox(text):
    return f'<div class="wbox">ℹ {text}</div>'

def sec(kicker, title, badge=""):
    b = f'<span class="sec-badge">{badge}</span>' if badge else ""
    return (f'<div class="sec-wrap"><div>'
            f'<div class="sec-kicker">{kicker}</div>'
            f'<div class="sec-title">{title}</div></div>{b}</div>')

def rank_list(items, title="", subtitle="", badge="", accent=None):
    """Render a numbered leaderboard card.
    items: list of (name, sub, val, val_color) — up to any length.
    """
    ac = accent or C24_BLUE
    hd = ""
    if title:
        bpart = f'<span class="rank-card-badge">{badge}</span>' if badge else ""
        hd = f'<div class="rank-card-hd"><span class="rank-card-title">{title}</span>{bpart}</div>'
    if subtitle:
        hd += f'<div class="rank-card-sub">{subtitle}</div>'
    rows = ""
    for i, (name, sub, val, vc) in enumerate(items):
        n = i + 1
        nc = f"rnum-{n}" if n <= 5 else "rnum-x"
        s = f'<div class="rname-sub">{sub}</div>' if sub else ""
        rows += (f'<div class="rank-item">'
                 f'<div class="rnum {nc}">{n}</div>'
                 f'<div class="rname"><div class="rname-main">{name}</div>{s}</div>'
                 f'<div class="rval" style="color:{vc}">{val}</div>'
                 f'</div>')
    return (f'<div class="rank-card">'
            f'<div class="rank-card-accent" style="background:{ac}"></div>'
            f'{hd}{rows}</div>')

def sparkline_svg(values, w=80, h=22, color=C24_BLUE, stroke=1.5):
    """SVG sparkline for embedding inside KPI cards."""
    vals = [float(v) for v in values if not pd.isna(v)]
    if len(vals) < 2: return ""
    mn, mx = min(vals), max(vals)
    if mx == mn: return ""
    n = len(vals)
    pts = " ".join(
        f"{i * w / (n-1):.0f},{(1-(v-mn)/(mx-mn)) * h:.0f}"
        for i, v in enumerate(vals)
    )
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'style="display:block;margin-top:6px">'
            f'<polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'</svg>')

def material(v, threshold=3.0):
    """Return True if MoM change is material (|v| >= threshold or nan)."""
    if v is None or (isinstance(v, float) and np.isnan(v)): return False
    return abs(v) >= threshold

# ── Data loaders ─────────────────────────────────────────────────────────────
@st.cache_data
def load_totals():
    """monthly GSC brand impressions — month, total_impressions, mom_pct, yoy_pct"""
    df = pd.read_csv(DATA / "historical_totals.csv")
    df["month"] = df["month"].astype(str)
    return df.sort_values("month").reset_index(drop=True)

@st.cache_data
def load_keywords():
    """per-month keyword files — keyword, category, impressions, month"""
    frames = []
    for fp in sorted(glob(str(DATA / "20*.csv"))):
        try:
            tmp = pd.read_csv(fp)
            if "keyword" in tmp.columns:
                frames.append(tmp)
        except Exception: pass
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

@st.cache_data
def load_city():
    """monthly city-level impressions — month, city, impressions"""
    p = DATA / "city_impressions.csv"
    if p.exists():
        df = pd.read_csv(p); df["month"] = df["month"].astype(str)
        return df
    return pd.DataFrame()

@st.cache_data
def load_bsos_monthly():
    """monthly BSOS — merges 5b (to Jun 2026, primary) with 7b (Spinny/OLX to Mar 2026)"""
    p5 = DATA / "bsos_india_5b_daily.csv"
    p7 = DATA / "bsos_india_daily.csv"
    if not p5.exists(): return pd.DataFrame()
    df5 = pd.read_csv(p5); df5["date"] = pd.to_datetime(df5["date"])
    df5["month"] = df5["date"].dt.to_period("M").astype(str)
    b5 = [c for c in ["Cardekho","Cars24","CarWale","MFC","MTV"] if c in df5.columns]
    m5 = df5.groupby("month")[b5].mean().reset_index()
    if p7.exists():
        df7 = pd.read_csv(p7); df7["date"] = pd.to_datetime(df7["date"])
        df7["month"] = df7["date"].dt.to_period("M").astype(str)
        b7 = [c for c in ["Spinny","OLX"] if c in df7.columns]
        if b7:
            m7 = df7.groupby("month")[b7].mean().reset_index()
            m5 = m5.merge(m7, on="month", how="left")
    return m5.sort_values("month").reset_index(drop=True)

@st.cache_data
def load_bsos_weekly():
    """weekly BSOS SoS % derived from daily 5-brand data"""
    p = DATA / "bsos_india_5b_daily.csv"
    if not p.exists(): return pd.DataFrame()
    df = pd.read_csv(p); df["date"] = pd.to_datetime(df["date"])
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.dayofweek, unit="d")
    df["week_end"] = df["week_start"] + pd.Timedelta(days=6)
    df["week"] = df.apply(lambda r: f"{r['week_start'].strftime('%d %b')} – {r['week_end'].strftime('%d %b %Y')}", axis=1)
    brands = [b for b in ["Cardekho","Cars24","CarWale","MFC","MTV"] if b in df.columns]
    result = df.groupby(["week_start","week"])[brands].mean().reset_index()
    return result.sort_values("week_start").drop(columns=["week_start"]).reset_index(drop=True)

@st.cache_data
def load_bsos_daily():
    """daily BSOS pan-India SoS % (5 brands, May 2025–Jun 2026) — date, Cardekho,Cars24,CarWale,MFC,MTV"""
    p = DATA / "bsos_india_5b_daily.csv"
    if p.exists():
        df = pd.read_csv(p); df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
    return pd.DataFrame()

@st.cache_data
def load_bsos_daily_7b():
    """daily BSOS pan-India 7-brand (includes Spinny/OLX) — date to Mar 2026"""
    p = DATA / "bsos_india_daily.csv"
    if p.exists():
        df = pd.read_csv(p); df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
    return pd.DataFrame()

@st.cache_data
def load_bsos_google_monthly():
    """Google Brandstack BSOS monthly averages — returns empty (data moved to main sheet)"""
    p = DATA / "bsos_google_monthly.csv"
    if p.exists(): return pd.read_csv(p).sort_values("month").reset_index(drop=True)
    return pd.DataFrame()

@st.cache_data
def load_bsos_city_daily():
    """city-level daily BSOS — date, city, Cardekho,Cars24,CarWale,MFC,MTV,OLX,Spinny"""
    p = DATA / "bsos_city_daily.csv"
    if p.exists():
        df = pd.read_csv(p); df["date"] = pd.to_datetime(df["date"])
        return df.sort_values(["city","date"]).reset_index(drop=True)
    return pd.DataFrame()

@st.cache_data
def load_bsos_pan_india_daily():
    """pan-India BSOS DoD from 1GleR3Nf day tab — Jan 2026+"""
    p = DATA / "bsos_pan_india_daily.csv"
    if p.exists():
        df = pd.read_csv(p); df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
    return pd.DataFrame()

@st.cache_data
def load_bsos_pan_monthly():
    """pan-India BSOS MoM from dedicated monthly CSV (1GleR3Nf month tab) — Jan 2023+"""
    p = DATA / "bsos_pan_monthly.csv"
    if p.exists():
        return pd.read_csv(p).sort_values("month").reset_index(drop=True)
    # fallback: compute from daily
    d = load_bsos_pan_india_daily()
    if d.empty: return pd.DataFrame()
    d = d.copy(); d["month"] = d["date"].dt.to_period("M").astype(str)
    brands = [b for b in ["Cardekho","Cars24","CarWale","MFC","MTV","OLX","Spinny"] if b in d.columns]
    return d.groupby("month")[brands].mean().reset_index().sort_values("month").reset_index(drop=True)

@st.cache_data
def load_bsos_pan_weekly():
    """pan-India BSOS WoW from dedicated weekly CSV (1GleR3Nf week tab) — Dec 2024+"""
    p = DATA / "bsos_pan_weekly.csv"
    if p.exists():
        df = pd.read_csv(p)
        df["week_start"] = pd.to_datetime(df["week_start"])
        return df.sort_values("week_start").reset_index(drop=True)
    # fallback: compute from daily
    d = load_bsos_pan_india_daily()
    if d.empty: return pd.DataFrame()
    d = d.copy()
    d["week_start"] = d["date"] - pd.to_timedelta(d["date"].dt.dayofweek, unit="d")
    d["week_end"] = d["week_start"] + pd.Timedelta(days=6)
    d["week"] = d.apply(lambda r: f"{r['week_start'].strftime('%d %b')} – {r['week_end'].strftime('%d %b %Y')}", axis=1)
    brands = [b for b in ["Cardekho","Cars24","CarWale","MFC","MTV","OLX","Spinny"] if b in d.columns]
    return d.groupby(["week_start","week"])[brands].mean().reset_index().sort_values("week_start").reset_index(drop=True)

@st.cache_data
def load_gsc_daily():
    """daily GSC brand impressions — date, impressions, clicks"""
    p = DATA / "gsc_daily_india.csv"
    if p.exists():
        df = pd.read_csv(p); df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
    return pd.DataFrame()

# ── Load data ─────────────────────────────────────────────────────────────────
totals_df   = load_totals()
kw_df       = load_keywords()
city_df     = load_city()
bsos_m      = load_bsos_monthly()
bsos_w      = load_bsos_weekly()
bsos_d      = load_bsos_daily()
bsos_d7     = load_bsos_daily_7b()
bsos_gm     = load_bsos_google_monthly()
bsos_cd     = load_bsos_city_daily()
bsos_pan_d  = load_bsos_pan_india_daily()
bsos_pan_m  = load_bsos_pan_monthly()
bsos_pan_w  = load_bsos_pan_weekly()
gsc_d       = load_gsc_daily()

# ── Globals — always use latest available month ───────────────────────────────
latest_month = totals_df["month"].max()
_months_desc = sorted(totals_df["month"].unique(), reverse=True)
prev_month   = _months_desc[1] if len(_months_desc) > 1 else None
yoy_month    = (pd.Period(latest_month, freq="M") - 12).strftime("%Y-%m")
if yoy_month not in totals_df["month"].values: yoy_month = None
month_lbl    = month_label(latest_month)

_cr  = totals_df[totals_df["month"] == latest_month]
_pr  = totals_df[totals_df["month"] == prev_month] if prev_month else pd.DataFrame()
_yr  = totals_df[totals_df["month"] == yoy_month]  if yoy_month  else pd.DataFrame()
curr_imp = int(_cr["total_impressions"].iloc[0]) if not _cr.empty else 0
prev_imp = int(_pr["total_impressions"].iloc[0]) if not _pr.empty else None
yoy_imp  = int(_yr["total_impressions"].iloc[0]) if not _yr.empty else None
mom_imp  = pct_ch(curr_imp, prev_imp)
yoy_imp_pct = pct_ch(curr_imp, yoy_imp)
peak_row = totals_df.loc[totals_df["total_impressions"].idxmax()]
is_ath   = curr_imp == int(peak_row["total_impressions"])

_bl = bsos_m.iloc[-1] if not bsos_m.empty else None
_pb = bsos_m.iloc[-2] if len(bsos_m) >= 2 else None
c24_sos  = float(_bl["Cars24"]) if _bl is not None else None
c24_sos_mom = pp_ch(c24_sos, float(_pb["Cars24"])) if _pb is not None and c24_sos else None
c24_sos_month = month_label(_bl["month"]) if _bl is not None else month_lbl
# Spinny: use latest row from merged monthly that has Spinny data
_sp_rows = bsos_m[bsos_m["Spinny"].notna()] if not bsos_m.empty and "Spinny" in bsos_m.columns else pd.DataFrame()
_sp_bl = _sp_rows.iloc[-1] if not _sp_rows.empty else None
_sp_pb = _sp_rows.iloc[-2] if len(_sp_rows) >= 2 else None
sp_sos   = float(_sp_bl["Spinny"]) if _sp_bl is not None else None
_sp_lbl  = month_label(_sp_bl["month"]) if _sp_bl is not None else month_lbl
# Ratio: current C24 SoS (latest month) vs last known Spinny SoS
sos_ratio = (c24_sos / sp_sos * 100) if c24_sos and sp_sos and sp_sos > 0 else None
sos_ratio_mom = pp_ch(sos_ratio, (float(_pb["Cars24"]) / sp_sos * 100) if _pb is not None and sp_sos and sp_sos > 0 else None)

# Freshness stamps
_bsos_fresh = f"BSOS to {month_label(bsos_m['month'].max())}" if not bsos_m.empty else "BSOS —"
_gsc_fresh  = f"GSC to {month_lbl}"
_dly_fresh  = f"Daily to {bsos_d['date'].max().strftime('%d %b %Y')}" if not bsos_d.empty else ""

# Latest WoW (BSOS weekly proxy)
_wk_lbl, _wk_wow = "", None
if not bsos_w.empty and len(bsos_w) >= 2:
    _wl = bsos_w.iloc[-1]; _wpl = bsos_w.iloc[-2]
    _wk_lbl = f"w/{_wl['week']}"
    _wk_wow = pp_ch(float(_wl["Cars24"]), float(_wpl["Cars24"]))

# ── Logo ──────────────────────────────────────────────────────────────────────
_svg_path = Path("assets/cars24-logo-blue.svg")
if _svg_path.exists():
    with open(_svg_path) as _f:
        _svg_b64 = base64.b64encode(_f.read().encode()).decode()
    _logo_html = (f'<img src="data:image/svg+xml;base64,{_svg_b64}" height="26" '
                  f'style="filter:brightness(0) invert(1);display:inline-block;'
                  f'vertical-align:middle;line-height:0;image-rendering:crisp-edges" />')
else:
    _logo_html = '<span style="font-size:17px;font-weight:900;color:white">CARS24</span>'

# ── Static banner ─────────────────────────────────────────────────────────────
st.markdown(f"""<div class="c24-banner">
  <div style="display:flex;align-items:center;gap:0">
    {_logo_html}
    <span class="banner-title">Brand Key Metrics</span>
  </div>
</div>""", unsafe_allow_html=True)

# ── Always-visible overview strip ────────────────────────────────────────────
def _ov_badge(v, is_pp=False):
    if v is None or (isinstance(v, float) and np.isnan(v)): return ""
    sym = "pp" if is_pp else "%"
    cls = "ov-badge-up" if v > 0 else "ov-badge-down" if v < 0 else "ov-badge-flat"
    arrow = "▲" if v > 0 else "▼" if v < 0 else "→"
    return f'<span class="ov-badge {cls}">{arrow}&thinsp;{abs(v):.1f}{sym}</span>'

_imp_int  = fmt_lakh(curr_imp).rstrip("L")
_sos_int  = f"{c24_sos:.1f}" if c24_sos else "—"
_rat_int  = f"{sos_ratio:.0f}" if sos_ratio else "—"

# ── Country / Channel top-level tabs ─────────────────────────────────────────
_ctry_india, _ctry_au, _ctry_uae, _ctry_yt, _ctry_ig, _ctry_inf, _ctry_li = st.tabs([
    "🇮🇳  India", "🇦🇺  Australia", "🇦🇪  UAE",
    "📺  YouTube", "📸  Instagram", "👥  Influencers", "💼  LinkedIn",
])

with _ctry_india:
    # Overview strip (India KPIs, always visible at the top of India tab)
    st.markdown(f'<div class="overview-strip"><div class="ov-metric" style="border-top-color:{C24_BLUE}"><div class="ov-lbl">Brand Search Impressions · {month_lbl}</div><div class="ov-value">{_imp_int}<span class="ov-unit">L</span></div>{_ov_badge(mom_imp)}<div class="ov-sub">vs prev month · Google Search Console</div></div><div class="ov-metric" style="border-top-color:{C24_MINT_DK}"><div class="ov-lbl">Cars24 Share of Searches · {c24_sos_month}</div><div class="ov-value">{_sos_int}<span class="ov-unit">%</span></div>{_ov_badge(c24_sos_mom, True)}<div class="ov-sub">MoM · Brandstack BSOS data</div></div><div class="ov-metric" style="border-top-color:{C24_ORANGE}"><div class="ov-lbl">C24 vs Spinny SoS · {c24_sos_month}</div><div class="ov-value">{_rat_int}<span class="ov-unit">%</span></div>{_ov_badge(sos_ratio_mom, True)}<div class="ov-sub">C24 ({c24_sos_month}) ÷ Spinny ({_sp_lbl})</div></div></div>', unsafe_allow_html=True)

    # ── India metric tabs ──────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊  Search Impressions",
        "🔑  Keywords",
        "🆚  Share of Searches",
        "📡  Google Indexed",
        "📈  Impressions × SoS",
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — BRAND SEARCH IMPRESSIONS
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:

    _all_months_asc  = sorted(totals_df["month"].unique())
    _all_months_desc = sorted(totals_df["month"].unique(), reverse=True)

    # ── Period filter (selectbox) ─────────────────────────────────────────────
    _pf_col, _pf_spc = st.columns([4, 1])
    with _pf_col:
        st.markdown(sec("📊 Brand Search Impressions", f"Aggregated metrics · {month_lbl}"), unsafe_allow_html=True)
    with _pf_spc:
        _period_opts = [f"Current — {month_lbl}", "Last 3 months", "Last 6 months",
                        "Last 12 months", "All time"]
        _period_keys = ["current", "3m", "6m", "12m", "all"]
        _period_sel = st.selectbox("Period", _period_opts, index=0, key="t1_period",
                                   label_visibility="collapsed")
    _pkey = _period_keys[_period_opts.index(_period_sel)]

    # ── Compute period KPIs ───────────────────────────────────────────────────
    if _pkey == "current":
        _hero_imp, _hero_mom, _hero_yoy = curr_imp, mom_imp, yoy_imp_pct
        _hero_lbl = month_lbl
        _hero_sub = "Google Search Console · Brand keywords"
        _hero_ath = is_ath
    else:
        _n = {"3m": 3, "6m": 6, "12m": 12}.get(_pkey, len(_all_months_desc))
        _p_mths  = _all_months_desc[:_n]
        _pp_mths = _all_months_desc[_n:2*_n] if _pkey != "all" else []
        _yoy_mths = [(pd.Period(m, freq="M") - 12).strftime("%Y-%m") for m in _p_mths] if _pkey != "all" else []
        _p_df2   = totals_df[totals_df["month"].isin(_p_mths)]
        _pp_df2  = totals_df[totals_df["month"].isin(_pp_mths)] if _pp_mths else pd.DataFrame()
        _py_df2  = totals_df[totals_df["month"].isin(_yoy_mths)] if _yoy_mths else pd.DataFrame()
        _hero_imp = int(_p_df2["total_impressions"].sum())
        _hero_mom = pct_ch(_hero_imp, int(_pp_df2["total_impressions"].sum()) if not _pp_df2.empty else None)
        _hero_yoy = pct_ch(_hero_imp, int(_py_df2["total_impressions"].sum()) if not _py_df2.empty else None)
        _hero_lbl = "All time" if _pkey == "all" else f"Last {_n} months"
        _hero_sub = (f"Sum across {len(_p_df2)} months" if _pkey == "all"
                     else f"{month_label(_p_mths[-1])} – {month_label(_p_mths[0])}")
        _hero_ath = False

    # ── Summary KPI strip ─────────────────────────────────────────────────────
    def _v(v): return v is not None and not (isinstance(v, float) and np.isnan(v))
    _mc = C24_GREEN if (_v(_hero_mom) and _hero_mom > 0) else C24_RED_FB if (_v(_hero_mom) and _hero_mom < 0) else C24_TEXTGREY
    _yc = C24_GREEN if (_v(_hero_yoy) and _hero_yoy > 0) else C24_RED_FB if (_v(_hero_yoy) and _hero_yoy < 0) else C24_TEXTGREY
    _ms = f"{'▲' if _hero_mom > 0 else '▼'} {abs(_hero_mom):.1f}%" if _v(_hero_mom) else "—"
    _ys = f"{'▲' if _hero_yoy > 0 else '▼'} {abs(_hero_yoy):.1f}%" if _v(_hero_yoy) else "—"
    _atg = ' <span class="ath-badge" style="font-size:9px;padding:2px 8px;vertical-align:middle">ATH</span>' if _hero_ath else ""

    _mom_momentum = ("accelerating 🚀" if _v(_hero_mom) and _hero_mom > 10
                      else "recovering ↗" if _v(_hero_mom) and _hero_mom > 0
                      else "declining ↘" if _v(_hero_mom) and _hero_mom < 0 else "stable →")
    _mom_bg = (f"linear-gradient(135deg,{C24_GREEN} 0%,#00A844 100%)" if (_v(_hero_mom) and _hero_mom > 0)
               else f"linear-gradient(135deg,{C24_RED_FB} 0%,#C5001C 100%)" if (_v(_hero_mom) and _hero_mom < 0)
               else f"linear-gradient(135deg,#6B7280 0%,#374151 100%)")
    _yoy_bg = (f"linear-gradient(135deg,#1D1160 0%,{C24_BLUE} 100%)" if (_v(_hero_yoy) and _hero_yoy > 0)
               else f"linear-gradient(135deg,{C24_RED_FB} 0%,#C5001C 100%)" if (_v(_hero_yoy) and _hero_yoy < 0)
               else f"linear-gradient(135deg,#6B7280 0%,#374151 100%)")
    _ath_tag = '<span class="sm-tag">✨ ALL-TIME HIGH</span>' if _hero_ath else ""
    st.markdown(f"""<div class="summary-metrics">
      <div class="sm-item" style="background:linear-gradient(135deg,{C24_BLUE} 0%,{C24_BLUE_MED} 60%,#1A0A8F 100%)">
        <div class="sm-lbl">📊 Brand Search Impressions · {_hero_lbl}</div>
        <div class="sm-val">{fmt_lakh(_hero_imp)}</div>
        <div class="sm-sub">{_hero_sub}</div>
        {_ath_tag}
        {sparkline_svg(list(totals_df["total_impressions"].tail(12)/1e5), w=110, h=22, color=C24_MINT)}
      </div>
      <div class="sm-item" style="background:{_mom_bg}">
        <div class="sm-lbl">{"📈" if (_v(_hero_mom) and _hero_mom > 0) else "📉"} Month-on-Month Growth</div>
        <div class="sm-val">{_ms}</div>
        <div class="sm-sub">vs previous {"month" if _pkey == "current" else "period"}</div>
        <span class="sm-tag">{_mom_momentum}</span>
      </div>
      <div class="sm-item" style="background:{_yoy_bg}">
        <div class="sm-lbl">{"🗓️" } Year-on-Year Growth</div>
        <div class="sm-val">{_ys}</div>
        <div class="sm-sub">vs {"same month last year" if _pkey == "current" else "same period last year"}</div>
        <span class="sm-tag">{"long-term momentum ✓" if _v(_hero_yoy) and _hero_yoy > 0 else "structural headwind ✗" if _v(_hero_yoy) and _hero_yoy < 0 else "flat"}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Context strip ─────────────────────────────────────────────────────────
    _total_months = len(totals_df)
    _best_month   = totals_df.loc[totals_df["total_impressions"].idxmax(), "month"]
    _best_imp     = totals_df["total_impressions"].max()
    _avg_imp      = totals_df["total_impressions"].mean()
    _ctx_rel = ("above" if curr_imp > _avg_imp else "below")
    _ctx_gap = abs(curr_imp - _avg_imp) / _avg_imp * 100
    st.markdown(f"""<div class="ctx-strip">
      <div class="ctx-title">📖 What this tells us</div>
      <div class="ctx-body">
        <strong>Brand Search Impressions</strong> = how many times Cars24 appeared in Google Search results
        for brand-related queries. Higher impressions = stronger brand awareness & recall.<br>
        The latest month (<em>{month_lbl}</em>) recorded <em>{fmt_lakh(curr_imp)}</em> impressions —
        <strong>{_ctx_gap:.0f}% {_ctx_rel} the {_total_months}-month average</strong> ({fmt_lakh(_avg_imp)}).
        {f'All-time peak was <strong>{fmt_lakh(_best_imp)}</strong> in <strong>{month_label(_best_month)}</strong>.' if _best_month != latest_month else f'This is the <strong>all-time high</strong> in our dataset — a brand demand milestone.'}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Monthly Trendline ─────────────────────────────────────────────────────
    _tr_hd, _tr_flt = st.columns([4, 1])
    with _tr_hd:
        st.markdown(f"""<div class="sec-banner" style="background:linear-gradient(135deg,{C24_BLUE} 0%,{C24_BLUE_MED} 100%)">
          <span class="sec-banner-icon">📈</span>
          <div><div class="sec-banner-title">Monthly Trendline</div>
          <div class="sec-banner-sub">How brand search volume has evolved over time</div></div>
        </div>""", unsafe_allow_html=True)
        st.markdown('<div class="sec-desc">Each point = total Google Search impressions for Cars24 brand keywords that month. The dashed line shows the overall trend direction. Mint star = all-time peak.</div>', unsafe_allow_html=True)
    with _tr_flt:
        _tr_per = st.selectbox("Period", ["All time", "Last 6 months", "Last 12 months", "Last 3 months"],
                                index=0, key="t1_tr_period", label_visibility="collapsed")

    _tr_n  = {"All time": len(_all_months_asc), "Last 3 months": 3,
               "Last 6 months": 6, "Last 12 months": 12}.get(_tr_per, len(_all_months_asc))
    _tr_df = totals_df.sort_values("month").tail(_tr_n).copy()
    _tr_df["imp_lakh"] = _tr_df["total_impressions"] / 1e5
    _tr_df["lbl"]      = _tr_df["month"].apply(month_label)

    _ath_idx = _tr_df["imp_lakh"].idxmax() if not _tr_df.empty else None
    _ath_r   = _tr_df.loc[_ath_idx] if _ath_idx is not None else None
    _lt_r    = _tr_df.iloc[-1] if not _tr_df.empty else None
    _z_tr    = np.polyfit(range(len(_tr_df)), _tr_df["imp_lakh"].fillna(0), 1) if len(_tr_df) >= 2 else [0, 0]
    _ty_tr   = np.poly1d(_z_tr)(range(len(_tr_df)))

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=_tr_df["lbl"], y=_tr_df["imp_lakh"], name="Impressions",
        mode="lines+markers", fill="tozeroy",
        fillgradient=dict(type="vertical", colorscale=[[0, "rgba(71,54,254,0.22)"], [1, "rgba(71,54,254,0.02)"]]),
        line=dict(color=C24_BLUE, width=3), marker=dict(size=7, color=C24_BLUE,
            line=dict(color="white", width=2)),
        hovertemplate="<b>%{x}</b><br><b>%{y:.2f}L</b> impressions<extra></extra>",
    ))
    if len(_tr_df) >= 2:
        fig_trend.add_trace(go.Scatter(
            x=_tr_df["lbl"], y=_ty_tr, name="Trend",
            mode="lines", line=dict(color=C24_MINT_DK, width=2, dash="dot"), hoverinfo="skip",
        ))
    if _ath_r is not None:
        fig_trend.add_trace(go.Scatter(
            x=[_ath_r["lbl"]], y=[_ath_r["imp_lakh"]], name="All-time high",
            mode="markers+text",
            marker=dict(color=C24_MINT, size=12, symbol="star", line=dict(color=C24_MINT_DK, width=1)),
            text=[f"ATH {fmt_lakh(_ath_r['total_impressions'])}"],
            textposition="top center", textfont=dict(color=C24_MINT_DK, size=10), hoverinfo="skip",
        ))
    if _lt_r is not None and (_ath_r is None or _lt_r["month"] != _ath_r["month"]):
        fig_trend.add_trace(go.Scatter(
            x=[_lt_r["lbl"]], y=[_lt_r["imp_lakh"]], name="Latest",
            mode="markers+text", marker=dict(color=C24_BLUE, size=8),
            text=[fmt_lakh(_lt_r["total_impressions"])],
            textposition="top center", textfont=dict(color=C24_BLUE, size=10), hoverinfo="skip",
        ))
    fig_trend.update_layout(**std_layout(360,
        plot_bgcolor="#F7F5FF",
        xaxis=ax(tickangle=-45, tickfont=dict(size=9, color=C24_BLACK), showgrid=False),
        yaxis=ax(ticksuffix="L", showgrid=True, gridcolor="#EBE8FF", title=""),
        legend=dict(orientation="h", y=1.06, x=0, font=dict(size=11)),
    ))
    st.plotly_chart(fig_trend, use_container_width=True)

    if len(_tr_df) >= 2:
        _sd = "upward ▲" if _z_tr[0] > 0 else "downward ▼"
        _tr_min_r = _tr_df.loc[_tr_df["imp_lakh"].idxmin()]
        _tr_range  = _tr_df["imp_lakh"].max() - _tr_df["imp_lakh"].min()
        _tr_box_cls = "ibox-mint" if _z_tr[0] > 0 else "ibox-orange"
        _tr_icon   = "📈" if _z_tr[0] > 0 else "📉"
        st.markdown(f"""<div class="{_tr_box_cls}">
          {_tr_icon} <strong>Trend:</strong> Overall trajectory is <strong>{_sd}</strong>
          at <strong>{_z_tr[0]:+.2f}L/month</strong> average growth.
          {f'Peak in this view: <strong>{fmt_lakh(_ath_r["total_impressions"])}</strong> in <strong>{month_label(_ath_r["month"])}</strong>.' if _ath_r is not None else ""}
          Lowest: <strong>{fmt_lakh(_tr_min_r["total_impressions"])}</strong> in {month_label(_tr_min_r["month"])}.
          Range across {len(_tr_df)} months: <strong>{_tr_range:.2f}L</strong>.
          {f'<br>💡 <em>{month_lbl} at {fmt_lakh(curr_imp)} — up {mom_imp:.1f}% MoM, up {yoy_imp_pct:.1f}% YoY.</em>' if _pkey == "current" and _v(mom_imp) and _v(yoy_imp_pct) else ""}
        </div>""", unsafe_allow_html=True)

    # ── Month-on-Month Table ──────────────────────────────────────────────────
    _mt_hd, _mt_flt = st.columns([4, 1])
    with _mt_hd:
        st.markdown(f"""<div class="sec-banner" style="background:linear-gradient(135deg,#1D1160 0%,{C24_BLUE} 100%)">
          <span class="sec-banner-icon">📋</span>
          <div><div class="sec-banner-title">Month-on-Month Table</div>
          <div class="sec-banner-sub">Impressions volume with MoM and YoY growth rates — latest month highlighted</div></div>
        </div>""", unsafe_allow_html=True)
        st.markdown('<div class="sec-desc"><strong>MoM</strong> = momentum vs the prior month. <strong>YoY</strong> = structural year-over-year trajectory. Green rows = growth months. Red rows = decline months.</div>', unsafe_allow_html=True)
    with _mt_flt:
        _mt_per = st.selectbox("Period", ["All time", "Last 6 months", "Last 12 months", "Last 3 months", "Custom range"],
                                index=0, key="t1_mt_period", label_visibility="collapsed")

    if _mt_per == "Custom range":
        _mt_c1, _mt_c2 = st.columns(2)
        with _mt_c1:
            _mt_from = st.date_input("From month", value=pd.Timestamp(_all_months_desc[-1]), key="t1_mt_from",
                                      min_value=pd.Timestamp(_all_months_desc[-1]),
                                      max_value=pd.Timestamp(_all_months_desc[0]))
        with _mt_c2:
            _mt_to = st.date_input("To month", value=pd.Timestamp(_all_months_desc[0]), key="t1_mt_to",
                                    min_value=pd.Timestamp(_all_months_desc[-1]),
                                    max_value=pd.Timestamp(_all_months_desc[0]))
        _from_m = pd.Timestamp(_mt_from).strftime("%Y-%m")
        _to_m   = pd.Timestamp(_mt_to).strftime("%Y-%m")
        _tbl_df = totals_df[totals_df["month"].between(_from_m, _to_m)].sort_values("month", ascending=False).copy()
    else:
        _mt_n   = {"All time": len(_all_months_desc), "Last 3 months": 3,
                    "Last 6 months": 6, "Last 12 months": 12}.get(_mt_per, len(_all_months_desc))
        _tbl_df = totals_df.sort_values("month", ascending=False).head(_mt_n).copy()

    t_rows = ""
    for _, r in _tbl_df.iterrows():
        mom_v = r.get('mom_pct')
        if r["month"] == latest_month:
            row_cls = "tbl-latest"
        elif mom_v is not None and not (isinstance(mom_v, float) and np.isnan(mom_v)):
            row_cls = "tbl-up" if mom_v > 0 else "tbl-down"
        else:
            row_cls = ""
        is_lat = r["month"] == latest_month
        t_rows += f"""<tr class="{row_cls}">
          <td><strong>{month_label(r['month'])}</strong>
            {"&nbsp;<span style='background:{C24_BLUE};color:white;font-size:9px;padding:2px 7px;border-radius:10px;font-weight:700'>LATEST</span>" if is_lat else ""}</td>
          <td style="font-weight:800;color:{C24_BLACK};font-size:14px">{fmt_lakh(r['total_impressions'])}</td>
          <td style="font-size:11px;color:{C24_TEXTGREY}">{r['total_impressions']:,}</td>
          <td>{grc(r.get('mom_pct'))}</td>
          <td>{grc(r.get('yoy_pct'))}</td>
        </tr>"""
    st.markdown(f"""<div class="tbl-card"><div class="scroll-tbl"><table class="pt"><thead><tr>
      <th>Month</th><th>Impressions (Lakh)</th><th>Absolute</th><th>MoM Growth</th><th>YoY Growth</th>
    </tr></thead><tbody>{t_rows}</tbody></table></div></div>""", unsafe_allow_html=True)

    # Post-table MoM insights
    if not _tbl_df.empty and "mom_pct" in _tbl_df.columns:
        _mt_valid = _tbl_df.dropna(subset=["mom_pct"])
        if not _mt_valid.empty:
            _best_mom_r  = _mt_valid.loc[_mt_valid["mom_pct"].idxmax()]
            _worst_mom_r = _mt_valid.loc[_mt_valid["mom_pct"].idxmin()]
            _pos_months  = (_mt_valid["mom_pct"] > 0).sum()
            _total_v_months = len(_mt_valid)
            _best_lbl  = month_label(_best_mom_r["month"])
            _worst_lbl = month_label(_worst_mom_r["month"])
            st.markdown(f"""<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0">
              <div class="score-card" style="background:linear-gradient(135deg,{C24_GREEN} 0%,#00873A 100%)">
                <div class="score-label">🏆 Best Month (MoM)</div>
                <div class="score-val">▲{_best_mom_r['mom_pct']:.1f}%</div>
                <div class="score-sub">{_best_lbl} · {fmt_lakh(_best_mom_r['total_impressions'])} impressions</div>
              </div>
              <div class="score-card" style="background:linear-gradient(135deg,{C24_RED_FB} 0%,#C5001C 100%)">
                <div class="score-label">⚠️ Weakest Month (MoM)</div>
                <div class="score-val">▼{abs(_worst_mom_r['mom_pct']):.1f}%</div>
                <div class="score-sub">{_worst_lbl} · {fmt_lakh(_worst_mom_r['total_impressions'])} impressions</div>
              </div>
            </div>""", unsafe_allow_html=True)
            st.markdown(ibox(
                f"In the selected period, <strong>{_pos_months} out of {_total_v_months} months</strong> showed positive MoM growth "
                f"({_pos_months/_total_v_months*100:.0f}% hit rate). "
                + (f"Current month {month_lbl} is <strong>{'on track 🟢' if mom_imp and mom_imp > 0 else 'declining 🔴'}</strong> MoM." if _v(mom_imp) else "")
            ), unsafe_allow_html=True)

    # ── Week-on-Week ──────────────────────────────────────────────────────────
    if not bsos_w.empty:
        _ww_hd, _ww_flt = st.columns([4, 1])
        with _ww_hd:
            st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#4736FE 0%,#2818B4 100%)"><span class="sec-banner-icon">📅</span><div><div class="sec-banner-title">Week-on-Week Brand Demand</div><div class="sec-banner-sub">Weekly Cars24 search share — powered by Brandstack BSOS data</div></div></div>', unsafe_allow_html=True)
            st.markdown('<div class="sec-desc"><strong>Brand Demand Index</strong> = Cars24\'s share of branded auto-category searches that week. Higher % = Cars24 dominates search intent. Spikes often align with campaigns or media coverage.</div>', unsafe_allow_html=True)
        with _ww_flt:
            _ww_per = st.selectbox("Period", ["Last 12 weeks", "Last 8 weeks", "Last 17 weeks",
                                         "Last 26 weeks", "All available", "Custom range"],
                                    index=0, key="t1_ww_period", label_visibility="collapsed")

        _wkd = bsos_w.sort_values("week", ascending=False).reset_index(drop=True)
        if _ww_per == "Custom range":
            _bsos_dates = pd.to_datetime([w.split("–")[0].strip() for w in bsos_w["week"]], errors="coerce").dropna()
            _bsos_min = _bsos_dates.min().date() if not _bsos_dates.empty else None
            _bsos_max = _bsos_dates.max().date() if not _bsos_dates.empty else None
            _ww_c1, _ww_c2 = st.columns(2)
            with _ww_c1:
                _ww_from = st.date_input("From week starting", value=_bsos_min, key="t1_ww_from",
                                          min_value=_bsos_min, max_value=_bsos_max)
            with _ww_c2:
                _ww_to = st.date_input("To week starting", value=_bsos_max, key="t1_ww_to",
                                        min_value=_bsos_min, max_value=_bsos_max)
            def _wk_in_range(wlbl):
                try:
                    d = pd.Timestamp(wlbl.split("–")[0].strip()).date()
                    return _ww_from <= d <= _ww_to
                except Exception:
                    return False
            _wkd = bsos_w[bsos_w["week"].apply(_wk_in_range)].sort_values("week", ascending=False).reset_index(drop=True)
            _ww_n = len(_wkd)
        else:
            _ww_n = {"Last 8 weeks": 8, "Last 12 weeks": 12, "Last 17 weeks": 17,
                     "Last 26 weeks": 26, "All available": len(bsos_w)}.get(_ww_per, 12)

        wr = ""
        for i, (_, r) in enumerate(_wkd.head(_ww_n).iterrows()):
            pw = _wkd.iloc[i + 1] if i + 1 < len(_wkd) else None
            wm = pp_ch(float(r["Cars24"]), float(pw["Cars24"])) if pw is not None else float("nan")
            if i == 0:
                wrow_cls = "tbl-latest"
            elif not np.isnan(wm):
                wrow_cls = "tbl-up" if wm > 0 else "tbl-down"
            else:
                wrow_cls = ""
            wr += f"""<tr class="{wrow_cls}">
              <td><strong>{r['week']}</strong>
                {"&nbsp;<span style='background:#7C3AED;color:white;font-size:9px;padding:2px 7px;border-radius:10px;font-weight:700'>LATEST</span>" if i == 0 else ""}</td>
              <td style="color:#7C3AED;font-weight:800;font-size:14px">{r['Cars24']:.1f}%</td>
              <td>{grc(wm, is_pp=True)}</td>
            </tr>"""
        st.markdown(f"""<div class="tbl-card"><div class="scroll-tbl"><table class="pt"><thead><tr>
          <th>Week</th><th>Brand Demand Index</th><th>WoW Δ</th>
        </tr></thead><tbody>{wr}</tbody></table></div></div>""", unsafe_allow_html=True)

        # Chart BELOW table
        _wk_p  = bsos_w.tail(_ww_n).reset_index(drop=True)
        _c24v  = _wk_p["Cars24"].values
        _wow_d = np.full(len(_wk_p), np.nan)
        _wow_d[1:] = np.diff(_c24v)
        _wow_bc = [C24_GREEN if (not np.isnan(v) and v >= 0) else C24_RED_FB for v in _wow_d]

        fig_wow = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                row_heights=[0.65, 0.35], vertical_spacing=0.08,
                                subplot_titles=["Weekly Brand Demand (%)", "WoW Change (pp)"])
        _wx  = list(range(len(_wk_p)))
        _wtx = [_wk_p.iloc[i]["week"] for i in range(len(_wk_p))]
        fig_wow.add_trace(go.Scatter(
            x=_wx, y=_wk_p["Cars24"], name="Cars24 brand demand",
            mode="lines+markers", fill="tozeroy", fillcolor="rgba(71,54,254,0.08)",
            line=dict(color=C24_BLUE, width=2.5), marker=dict(size=4),
            customdata=_wk_p["week"],
            hovertemplate="<b>%{customdata}</b><br>%{y:.1f}%<extra></extra>",
        ), row=1, col=1)
        if len(_wx) > 1:
            fig_wow.add_trace(go.Bar(
                x=_wx[1:], y=_wow_d[1:], name="WoW Δ",
                marker_color=_wow_bc[1:],
                hovertemplate="WoW: %{y:+.2f}pp<extra></extra>",
            ), row=2, col=1)
        fig_wow.update_layout(**std_layout(380, showlegend=True,
                                           legend=dict(orientation="h", y=1.06, x=0, font=dict(size=10))))
        fig_wow.update_xaxes(ax(tickangle=-45, tickfont=dict(size=8, color=C24_BLACK),
                                ticktext=_wtx, tickvals=_wx, showgrid=False))
        fig_wow.update_yaxes(ax(tickformat=".1f", ticksuffix="%", showgrid=True), row=1, col=1)
        fig_wow.update_yaxes(ax(tickformat=".2f", ticksuffix="pp", zeroline=True,
                                zerolinecolor=C24_BORDER, showgrid=False), row=2, col=1)
        st.plotly_chart(fig_wow, use_container_width=True)

        if len(bsos_w) >= 2:
            _wi = pp_ch(float(bsos_w.iloc[-1]["Cars24"]), float(bsos_w.iloc[-2]["Cars24"]))
            _wkd_n = _wkd.head(_ww_n)
            _wk_avg = float(bsos_w["Cars24"].mean()) if not bsos_w.empty else None
            _wk_max = bsos_w.loc[bsos_w["Cars24"].idxmax()] if not bsos_w.empty else None
            _wk_latest_val = float(bsos_w.iloc[-1]["Cars24"])
            _wk_box_cls = "ibox-mint" if _wi > 0 else "ibox-orange" if _wi < -0.3 else "ibox"
            st.markdown(f"""<div class="{_wk_box_cls}">
              📅 <strong>Latest week ({bsos_w.iloc[-1]['week']}):</strong>
              brand demand at <strong>{_wk_latest_val:.1f}%</strong>
              ({grc(_wi, is_pp=True)} WoW).
              {f'All-time peak: <strong>{_wk_max["Cars24"]:.1f}%</strong> in {_wk_max["week"]}.' if _wk_max is not None else ""}
              {f'Dataset average: <strong>{_wk_avg:.1f}%</strong> — current is <strong>{"above" if _wk_latest_val > _wk_avg else "below"} avg</strong> by {abs(_wk_latest_val - _wk_avg):.1f}pp.' if _wk_avg else ""}
            </div>""", unsafe_allow_html=True)

    # ── Day-on-Day ────────────────────────────────────────────────────────────
    if not gsc_d.empty:
        _dd_hd, _dd_flt = st.columns([4, 1])
        with _dd_hd:
            st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#020618 0%,#1D1160 100%)"><span class="sec-banner-icon">📆</span><div><div class="sec-banner-title">Day-on-Day Impressions</div><div class="sec-banner-sub">Daily brand search volume from Google Search Console</div></div></div>', unsafe_allow_html=True)
            st.markdown('<div class="sec-desc">Raw daily impressions for Cars24 brand keywords. <strong>Weekends</strong> show lower volumes — this is normal. Unexpected spikes correlate with campaigns, sales events, or media coverage. Latest day is highlighted.</div>', unsafe_allow_html=True)
        with _dd_flt:
            _dd_per = st.selectbox("Period", ["Last 30 days", "Last 14 days", "Last 60 days", "Last 90 days", "Custom range"],
                                    index=0, key="t1_dd_period", label_visibility="collapsed")

        if _dd_per == "Custom range":
            _gsc_min = gsc_d["date"].min().date()
            _gsc_max = gsc_d["date"].max().date()
            _dd_c1, _dd_c2 = st.columns(2)
            with _dd_c1:
                _dd_from = st.date_input("From date", value=(_gsc_max - pd.Timedelta(days=29)),
                                          key="t1_dd_from", min_value=_gsc_min, max_value=_gsc_max)
            with _dd_c2:
                _dd_to = st.date_input("To date", value=_gsc_max,
                                        key="t1_dd_to", min_value=_gsc_min, max_value=_gsc_max)
            _dd_df = gsc_d[(gsc_d["date"].dt.date >= _dd_from) & (gsc_d["date"].dt.date <= _dd_to)]\
                         .sort_values("date", ascending=False).copy()
            _dd_n  = len(_dd_df)
        else:
            _dd_n  = {"Last 14 days": 14, "Last 30 days": 30,
                       "Last 60 days": 60, "Last 90 days": 90}.get(_dd_per, 30)
            _dd_df = gsc_d.sort_values("date", ascending=False).head(_dd_n).copy()

        # Table (most recent first) — badges pre-computed to avoid blank lines that break markdown HTML blocks
        dr = ""
        for i, (_, r) in enumerate(_dd_df.iterrows()):
            pw_d = _dd_df.iloc[i + 1] if i + 1 < len(_dd_df) else None
            dm   = pct_ch(r["impressions"], pw_d["impressions"]) if pw_d is not None else float("nan")
            if i == 0:
                drow_cls = "tbl-latest"
            elif not np.isnan(dm):
                drow_cls = "tbl-up" if dm > 0 else "tbl-down"
            else:
                drow_cls = ""
            is_wknd = r['date'].weekday() >= 5
            _we_b = "&nbsp;<span style='background:#E5E7EB;color:#6B7280;font-size:9px;padding:2px 6px;border-radius:8px;font-weight:600'>WE</span>" if is_wknd else ""
            _td_b = "&nbsp;<span style='background:#FF4F01;color:white;font-size:9px;padding:2px 7px;border-radius:10px;font-weight:700'>TODAY</span>" if i == 0 else ""
            dr += (f'<tr class="{drow_cls}"><td>'
                   f'<strong>{r["date"].strftime("%d %b %Y")}</strong>'
                   f'<span style="font-size:10px;color:{C24_TEXTGREY};margin-left:6px">{r["date"].strftime("%A")}</span>'
                   f'{_we_b}{_td_b}</td>'
                   f'<td style="font-weight:800;color:{C24_BLACK};font-size:14px">{int(r["impressions"]):,}</td>'
                   f'<td>{grc(dm)}</td></tr>')
        st.markdown(f'<div class="tbl-card"><div class="scroll-tbl"><table class="pt"><thead><tr><th>Date</th><th>Impressions</th><th>DoD Δ</th></tr></thead><tbody>{dr}</tbody></table></div></div>', unsafe_allow_html=True)

        # Chart BELOW table
        _dd_ch = gsc_d.sort_values("date").tail(_dd_n).copy()
        _ddy   = _dd_ch["impressions"].values.astype(float)
        _dod_d = np.full(len(_dd_ch), np.nan)
        _dod_d[1:] = np.where(_ddy[:-1] > 0,
                               (_ddy[1:] - _ddy[:-1]) / _ddy[:-1] * 100, np.nan)
        _dod_bc = [C24_GREEN if (not np.isnan(v) and v >= 0) else C24_RED_FB for v in _dod_d]

        fig_dod = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                row_heights=[0.65, 0.35], vertical_spacing=0.08,
                                subplot_titles=["Daily Impressions", "Day-on-Day Δ (%)"])
        fig_dod.add_trace(go.Scatter(
            x=_dd_ch["date"], y=_dd_ch["impressions"], name="Daily impressions",
            mode="lines", fill="tozeroy", fillcolor="rgba(71,54,254,0.07)",
            line=dict(color=C24_BLUE, width=2),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,}<extra></extra>",
        ), row=1, col=1)
        if len(_dd_ch) > 1:
            fig_dod.add_trace(go.Bar(
                x=_dd_ch["date"].iloc[1:], y=_dod_d[1:], name="DoD Δ",
                marker_color=_dod_bc[1:],
                hovertemplate="DoD: %{y:+.1f}%<extra></extra>",
            ), row=2, col=1)
        fig_dod.update_layout(**std_layout(380, showlegend=False))
        fig_dod.update_xaxes(ax(tickangle=-45, tickfont=dict(size=8, color=C24_BLACK), showgrid=False))
        fig_dod.update_yaxes(ax(showgrid=True), row=1, col=1)
        fig_dod.update_yaxes(ax(tickformat=".1f", ticksuffix="%", zeroline=True,
                                zerolinecolor=C24_BORDER, showgrid=False), row=2, col=1)
        st.plotly_chart(fig_dod, use_container_width=True)

        # DoD insights
        if not _dd_df.empty:
            _dd_latest = _dd_df.iloc[0]
            _dd_avg    = _dd_ch["impressions"].mean()
            _dd_peak_r = _dd_ch.loc[_dd_ch["impressions"].idxmax()]
            _dd_latest_vs_avg = pct_ch(_dd_latest["impressions"], _dd_avg)
            _dd_dod_last = pct_ch(_dd_df.iloc[0]["impressions"], _dd_df.iloc[1]["impressions"]) if len(_dd_df) > 1 else float("nan")
            _dd_box_cls = "ibox-mint" if _v(_dd_dod_last) and _dd_dod_last > 0 else "ibox-orange" if _v(_dd_dod_last) and _dd_dod_last < -5 else "ibox"
            st.markdown(f"""<div class="{_dd_box_cls}">
              📆 <strong>Latest day ({_dd_latest['date'].strftime('%d %b %Y')}):</strong>
              <strong>{int(_dd_latest['impressions']):,}</strong> impressions
              ({grc(_dd_dod_last)} DoD).
              {f'Period average: <strong>{int(_dd_avg):,}/day</strong> — latest is <strong>{"above" if _dd_latest["impressions"] > _dd_avg else "below"} average</strong> by {abs(_dd_latest_vs_avg):.1f}%.' if not np.isnan(_dd_avg) else ""}
              Peak in period: <strong>{int(_dd_peak_r['impressions']):,}</strong> on {_dd_peak_r['date'].strftime('%d %b')}.
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — KEYWORD INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:

    if kw_df.empty:
        st.info("Keyword data not loaded — ensure data/20*.csv files exist.")
    else:
        from classifier import CATEGORY_COLORS

        # ── Data prep ─────────────────────────────────────────────────────────
        _kw_all_months = sorted(kw_df["month"].unique())
        _kw_lm  = _kw_all_months[-1] if _kw_all_months else latest_month
        _kw_pm  = _kw_all_months[-2] if len(_kw_all_months) >= 2 else None
        _kw_ym  = next((m for m in reversed(_kw_all_months[:-1])
                        if m[:4] == str(int(_kw_lm[:4]) - 1) and m[5:] == _kw_lm[5:]), None)
        _kw_lbl = month_label(_kw_lm)

        def cat_sum(df):
            return df.groupby("category")["impressions"].sum() if not df.empty else pd.Series(dtype=float)

        # Monthly keyword totals with MoM + YoY
        _kw_mon = (kw_df.groupby("month")["impressions"].sum()
                   .reset_index().sort_values("month").reset_index(drop=True))
        _kw_mon["mom_pct"] = _kw_mon["impressions"].pct_change() * 100
        def _yoy_kw(row):
            ym = f"{int(row['month'][:4])-1}{row['month'][4:]}"
            ref = _kw_mon[_kw_mon["month"] == ym]
            return pct_ch(row["impressions"], ref.iloc[0]["impressions"]) if not ref.empty else float("nan")
        _kw_mon["yoy_pct"] = _kw_mon.apply(_yoy_kw, axis=1)

        _kw_lm_row   = _kw_mon[_kw_mon["month"] == _kw_lm]
        _kw_total_imp = float(_kw_lm_row["impressions"].iloc[0]) if not _kw_lm_row.empty else 0.0
        _kw_mom_val  = float(_kw_lm_row["mom_pct"].iloc[0]) if not _kw_lm_row.empty else float("nan")
        _kw_yoy_val  = float(_kw_lm_row["yoy_pct"].iloc[0]) if not _kw_lm_row.empty else float("nan")

        _kw_lat_df  = kw_df[kw_df["month"] == _kw_lm].copy()
        _kw_prev_df = kw_df[kw_df["month"] == _kw_pm].copy() if _kw_pm else pd.DataFrame()
        _kw_yoy_df  = kw_df[kw_df["month"] == _kw_ym].copy() if _kw_ym else pd.DataFrame()

        ct_curr = cat_sum(_kw_lat_df);  ct_prev = cat_sum(_kw_prev_df);  ct_yoy = cat_sum(_kw_yoy_df)
        total_kw = float(ct_curr.sum())
        _kw_top_cat = ct_curr.idxmax() if not ct_curr.empty else "N/A"
        _kw_top_pct = (ct_curr.max() / total_kw * 100) if total_kw > 0 else 0.0

        # ── Hero KPI strip ────────────────────────────────────────────────────
        st.markdown(f'<div class="c24-banner" style="margin-bottom:0"><div style="display:flex;align-items:center;gap:12px"><span style="font-size:28px">🔑</span><div><div style="font-size:20px;font-weight:900;color:white">Keywords Volume</div><div style="font-size:12px;color:rgba(255,255,255,.65)">Brand keyword impressions by category · Google Search Console</div></div></div></div>', unsafe_allow_html=True)

        _kw_mom_bg = "linear-gradient(135deg,#00C951 0%,#00A844 100%)" if _v(_kw_mom_val) and _kw_mom_val > 0 else "linear-gradient(135deg,#FB2C36 0%,#C5001C 100%)"
        _kw_yoy_bg = "linear-gradient(135deg,#1D1160 0%,#4736FE 100%)" if _v(_kw_yoy_val) and _kw_yoy_val > 0 else "linear-gradient(135deg,#020618 0%,#4736FE 100%)"
        _kw_ms = (f"{'▲' if _kw_mom_val > 0 else '▼'}{abs(_kw_mom_val):.1f}%") if _v(_kw_mom_val) else "—"
        _kw_ys = (f"{'▲' if _kw_yoy_val > 0 else '▼'}{abs(_kw_yoy_val):.1f}%") if _v(_kw_yoy_val) else "—"
        st.markdown(f'<div class="summary-metrics"><div class="sm-item" style="background:linear-gradient(135deg,{C24_BLUE} 0%,{C24_BLUE_MED} 60%,#1A0A8F 100%)"><div class="sm-lbl">🔑 Total Keyword Volume · {_kw_lbl}</div><div class="sm-val">{fmt_lakh(_kw_total_imp)}</div><div class="sm-sub">Google Search impressions for Cars24 brand keywords</div></div><div class="sm-item" style="background:{_kw_mom_bg}"><div class="sm-lbl">{"📈" if _v(_kw_mom_val) and _kw_mom_val > 0 else "📉"} Month-on-Month</div><div class="sm-val">{_kw_ms}</div><div class="sm-sub">vs {month_label(_kw_pm) if _kw_pm else "prev month"}</div></div><div class="sm-item" style="background:{_kw_yoy_bg}"><div class="sm-lbl">🗓️ Year-on-Year</div><div class="sm-val">{_kw_ys}</div><div class="sm-sub">vs {month_label(_kw_ym) if _kw_ym else "same month last year"}</div></div><div class="sm-item" style="background:linear-gradient(135deg,#1D1160 0%,{C24_BLUE} 100%)"><div class="sm-lbl">🏷️ Top Category</div><div class="sm-val" style="font-size:22px">{_kw_top_cat}</div><div class="sm-sub">{_kw_top_pct:.0f}% of total keyword volume</div></div></div>', unsafe_allow_html=True)

        # ── Section 1: Keyword Volume Table ───────────────────────────────────
        _kv_hd, _kv_fl = st.columns([4, 1])
        with _kv_hd:
            st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,{C24_BLUE} 0%,{C24_BLUE_MED} 100%)"><span class="sec-banner-icon">📊</span><div><div class="sec-banner-title">Monthly Keyword Volume</div><div class="sec-banner-sub">Total brand keyword impressions per month with MoM and YoY growth</div></div></div>', unsafe_allow_html=True)
            st.markdown('<div class="sec-desc">Month-by-month total brand keyword impressions from GSC. Growth above 10% MoM typically signals a campaign effect or seasonal uplift. Consistent YoY growth signals improving brand health.</div>', unsafe_allow_html=True)
        with _kv_fl:
            _kv_opts = [f"Current — {_kw_lbl}", "Last 3 months", "Last 6 months", "Last 12 months", "All time", "Custom range"]
            _kv_keys = ["current", "3m", "6m", "12m", "all", "custom"]
            _kv_per  = st.selectbox("Period", _kv_opts, index=4, key="kw_vol_per", label_visibility="collapsed")
        _kv_key = _kv_keys[_kv_opts.index(_kv_per)]
        _kw_all_desc = sorted(_kw_all_months, reverse=True)
        if _kv_key == "custom":
            _kvc1, _kvc2 = st.columns(2)
            with _kvc1:
                _kv_from = st.date_input("From month", value=pd.Timestamp(_kw_all_months[0]), key="kw_vol_from", min_value=pd.Timestamp(_kw_all_months[0]), max_value=pd.Timestamp(_kw_lm))
            with _kvc2:
                _kv_to = st.date_input("To month", value=pd.Timestamp(_kw_lm), key="kw_vol_to", min_value=pd.Timestamp(_kw_all_months[0]), max_value=pd.Timestamp(_kw_lm))
            _kv_from_m = pd.Timestamp(_kv_from).strftime("%Y-%m"); _kv_to_m = pd.Timestamp(_kv_to).strftime("%Y-%m")
            _kv_tbl = _kw_mon[_kw_mon["month"].between(_kv_from_m, _kv_to_m)].sort_values("month", ascending=False)
        else:
            _kv_n = {"current": 1, "3m": 3, "6m": 6, "12m": 12, "all": len(_kw_all_months)}.get(_kv_key, 1)
            _kv_tbl = _kw_mon.sort_values("month", ascending=False).head(_kv_n)

        _kv_rows = ""
        for _, _kr in _kv_tbl.iterrows():
            _is_latest_kv = _kr["month"] == _kw_lm
            _kv_rcls = "tbl-latest" if _is_latest_kv else ("tbl-up" if _v(_kr["mom_pct"]) and _kr["mom_pct"] > 0 else "tbl-down" if _v(_kr["mom_pct"]) and _kr["mom_pct"] < 0 else "")
            _kv_tag  = "<span style='background:#4736FE;color:white;font-size:9px;padding:2px 6px;border-radius:8px;font-weight:700;margin-left:6px'>LATEST</span>" if _is_latest_kv else ""
            _kv_rows += f'<tr class="{_kv_rcls}"><td><strong>{month_label(_kr["month"])}</strong>{_kv_tag}</td><td style="font-weight:800;font-size:14px">{fmt_lakh(_kr["impressions"])}</td><td>{grc(_kr["mom_pct"])}</td><td>{grc(_kr["yoy_pct"])}</td></tr>'
        st.markdown(f'<div class="tbl-card"><div class="scroll-tbl"><table class="pt"><thead><tr><th>Month</th><th>Keyword Volume</th><th>MoM Δ</th><th>YoY Δ</th></tr></thead><tbody>{_kv_rows}</tbody></table></div></div>', unsafe_allow_html=True)

        if _v(_kw_mom_val) or _v(_kw_yoy_val):
            _kv_insight = f"<strong>{_kw_lbl}:</strong> {fmt_lakh(_kw_total_imp)} total keyword impressions"
            if _v(_kw_mom_val): _kv_insight += f" · {'▲' if _kw_mom_val > 0 else '▼'} <strong>{abs(_kw_mom_val):.1f}% MoM</strong>"
            if _v(_kw_yoy_val): _kv_insight += f" · <strong>{abs(_kw_yoy_val):.1f}% YoY</strong>"
            st.markdown(ibox(_kv_insight + "."), unsafe_allow_html=True)

        # ── Section 2: Category Distribution & Volume ─────────────────────────
        st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#1D1160 0%,{C24_BLUE} 100%)"><span class="sec-banner-icon">🥧</span><div><div class="sec-banner-title">Category Distribution & Volume</div><div class="sec-banner-sub">Keyword volume by brand category with MoM, YoY and share shift</div></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-desc">How Cars24\'s keyword universe breaks down by intent. <strong>Cars24</strong> = core brand recall. <strong>Cars24 Cities</strong> = location searches. <strong>Cars24 Buy/Sell</strong> = high-intent transactional queries.</div>', unsafe_allow_html=True)

        _cd_per_opts = [f"Current — {_kw_lbl}", "Last 3 months", "Last 6 months", "Last 12 months", "All time"] + [month_label(m) for m in _kw_all_desc[1:]]
        _cd_sp, _cd_dp = st.columns([3, 1])
        with _cd_dp:
            _cd_per = st.selectbox("Period", _cd_per_opts, index=0, key="cat_dist_per", label_visibility="collapsed")

        if _cd_per.startswith("Current"):
            _cd_months = [_kw_lm]; _cd_prev_months = [_kw_pm] if _kw_pm else []; _cd_yoy_months = [_kw_ym] if _kw_ym else []
        elif _cd_per == "All time":
            _cd_months = _kw_all_months[:]; _cd_prev_months = []; _cd_yoy_months = []
        elif _cd_per in {"Last 3 months", "Last 6 months", "Last 12 months"}:
            _cd_n = {"Last 3 months": 3, "Last 6 months": 6, "Last 12 months": 12}[_cd_per]
            _cd_months = _kw_all_months[-_cd_n:]
            _cd_prev_months = _kw_all_months[max(0, len(_kw_all_months) - 2 * _cd_n):len(_kw_all_months) - _cd_n]
            _cd_yoy_months = [f"{int(m[:4])-1}{m[4:]}" for m in _cd_months]
        else:
            _cd_sel_m = next((m for m in _kw_all_months if month_label(m) == _cd_per), _kw_lm)
            _cd_idx = _kw_all_months.index(_cd_sel_m)
            _cd_months = [_cd_sel_m]; _cd_prev_months = [_kw_all_months[_cd_idx - 1]] if _cd_idx > 0 else []; _cd_yoy_months = [m for m in _kw_all_months if m[:4] == str(int(_cd_sel_m[:4]) - 1) and m[5:] == _cd_sel_m[5:]]

        ct_cd  = cat_sum(kw_df[kw_df["month"].isin(_cd_months)])
        ct_cdp = cat_sum(kw_df[kw_df["month"].isin(_cd_prev_months)]) if _cd_prev_months else pd.Series(dtype=float)
        ct_cdy = cat_sum(kw_df[kw_df["month"].isin(_cd_yoy_months)]) if _cd_yoy_months else pd.Series(dtype=float)
        total_cd = float(ct_cd.sum())
        _cd_prev_tot = float(ct_cdp.sum()) if not ct_cdp.empty else 0.0
        _cd_yoy_tot  = float(ct_cdy.sum()) if not ct_cdy.empty else 0.0

        if not ct_cd.empty and total_cd > 0:
            _cp_sorted = ct_cd.sort_values(ascending=False)
            fig_dn = go.Figure(go.Pie(
                labels=_cp_sorted.index, values=_cp_sorted.values, hole=0.55,
                marker_colors=[CATEGORY_COLORS.get(c, "#888") for c in _cp_sorted.index],
                textinfo="none",
                hovertemplate="<b>%{label}</b><br>%{value:,} impressions · %{percent}<extra></extra>",
            ))
            fig_dn.update_layout(**std_layout(340, margin=dict(t=10, b=10, l=10, r=10), showlegend=True,
                legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center", font=dict(size=10)),
                annotations=[dict(text=f"<b>{fmt_lakh(total_cd)}</b>", x=0.5, y=0.5, font_size=16, showarrow=False, font_color=C24_BLACK)]))
            st.plotly_chart(fig_dn, use_container_width=True)

            _cd_rows = ""
            _cd_mom_hdr = "Vol MoM" if _cd_per.startswith("Current") else "Vol Δ"
            for _ccat in sorted(ct_cd.index.union(ct_cdp.index if not ct_cdp.empty else pd.Index([])), key=lambda c: ct_cd.get(c, 0), reverse=True):
                _cv = ct_cd.get(_ccat, 0); _cpv = ct_cdp.get(_ccat, 0) if not ct_cdp.empty else 0; _cyv = ct_cdy.get(_ccat, 0) if not ct_cdy.empty else 0
                _cm = pct_ch(_cv, _cpv); _cy = pct_ch(_cv, _cyv)
                _csh = _cv / total_cd * 100 if total_cd > 0 else 0
                _cshp = _cpv / _cd_prev_tot * 100 if _cd_prev_tot > 0 else 0.0
                _cshy = _cyv / _cd_yoy_tot * 100 if _cd_yoy_tot > 0 else float("nan")
                _smom = _csh - _cshp; _syoy = (_csh - _cshy) if _v(_cshy) else float("nan")
                _cc_color = CATEGORY_COLORS.get(_ccat, "#888")
                _cd_rows += f'<tr><td><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:{_cc_color};margin-right:7px;vertical-align:middle"></span><strong>{_ccat}</strong></td><td style="font-weight:700">{fmt_lakh(_cv)}</td><td>{grc(_cm)}</td><td style="color:#6B7280;font-size:11px">{_csh:.1f}%</td><td>{grc(_smom, is_pp=True)}</td><td>{grc(_syoy, is_pp=True)}</td></tr>'
            st.markdown(f'<div class="tbl-card"><table class="pt"><thead><tr><th>Category</th><th>Volume</th><th>{_cd_mom_hdr}</th><th>Share%</th><th>Share MoM (pp)</th><th>Share YoY (pp)</th></tr></thead><tbody>{_cd_rows}</tbody></table></div>', unsafe_allow_html=True)
            _cd_lead = ct_cd.idxmax()
            _cd_msg = f"<strong>{_cd_lead}</strong> leads at {fmt_lakh(ct_cd[_cd_lead])} ({ct_cd[_cd_lead] / total_cd * 100:.0f}% of total)."
            if not ct_cdp.empty:
                _cd_mv = {c: pct_ch(ct_cd.get(c, 0), ct_cdp.get(c, 0)) for c in ct_cd.index if ct_cdp.get(c, 0) > 0}
                _cd_best = max(_cd_mv, key=lambda c: _cd_mv[c]) if _cd_mv else None
                if _cd_best and material(_cd_mv[_cd_best]):
                    _cd_msg += f" Fastest growing: <strong>{_cd_best}</strong> ({grc(_cd_mv[_cd_best])})."
            st.markdown(ibox(_cd_msg), unsafe_allow_html=True)

        # ── Section 3: Category Trends ────────────────────────────────────────
        st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,{C24_BLUE} 0%,#2818B4 100%)"><span class="sec-banner-icon">📈</span><div><div class="sec-banner-title">Category Trends Over Time</div><div class="sec-banner-sub">How each keyword category has grown — select categories to compare</div></div></div>', unsafe_allow_html=True)
        _ct_pivot = (kw_df.groupby(["month","category"])["impressions"].sum().reset_index()
                     .pivot(index="month", columns="category", values="impressions").fillna(0))
        _ct_base_opts = ["All time", "Last 12 months", "Last 6 months", "Last 3 months"]
        _ct_month_opts = [f"From {month_label(m)}" for m in _kw_all_months[:-1]]
        _ct_sel_row, _ct_per_col = st.columns([3, 1])
        with _ct_sel_row:
            _sel_cats = st.multiselect("Select categories to compare", list(_ct_pivot.columns), default=list(_ct_pivot.columns), key="cat_sel2")
        with _ct_per_col:
            _ct_per = st.selectbox("Period", _ct_base_opts + _ct_month_opts, index=0, key="cat_trend_per", label_visibility="collapsed")
        if _ct_per in _ct_base_opts:
            _ct_n = {"All time": len(_kw_all_months), "Last 12 months": 12, "Last 6 months": 6, "Last 3 months": 3}.get(_ct_per, len(_kw_all_months))
            _ct_filt = _ct_pivot.tail(_ct_n)
        else:
            _ct_from_lbl = _ct_per[5:]
            _ct_from_m = next((m for m in _kw_all_months if month_label(m) == _ct_from_lbl), _kw_all_months[0])
            _ct_filt = _ct_pivot.loc[_ct_pivot.index >= _ct_from_m]
        if _sel_cats:
            fig_ctr = go.Figure()
            for _scat in _sel_cats:
                if _scat in _ct_filt.columns:
                    fig_ctr.add_trace(go.Scatter(
                        x=_ct_filt.index, y=_ct_filt[_scat] / 1e5, name=_scat,
                        mode="lines+markers",
                        line=dict(color=CATEGORY_COLORS.get(_scat, "#888"), width=2.5),
                        marker=dict(size=5, color=CATEGORY_COLORS.get(_scat, "#888"), line=dict(color="white", width=1.5)),
                        hovertemplate=f"<b>{_scat}</b><br>%{{x}}: %{{y:.2f}}L<extra></extra>",
                    ))
            fig_ctr.update_layout(**std_layout(340,
                xaxis=ax(tickangle=-45, tickfont=dict(size=9, color=C24_BLACK)),
                yaxis=ax(tickformat=".1f", ticksuffix="L", showgrid=True),
                legend=dict(orientation="h", y=1.08, x=0, font=dict(size=10)),
            ))
            st.plotly_chart(fig_ctr, use_container_width=True)
        else:
            st.info("Select at least one category above to view trends.")

        # ── Section 4: Share of Total — Heatmap ──────────────────────────────
        st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#020618 0%,#1D1160 100%)"><span class="sec-banner-icon">📐</span><div><div class="sec-banner-title">Share of Total</div><div class="sec-banner-sub">Category share % shifting month by month — spot which are gaining or losing</div></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-desc">Category mix shift tells you if Cars24\'s search identity is evolving. <strong>Rising Cities share</strong> = geographic expansion working. <strong>Rising Buy/Sell share</strong> = capturing more transactional intent. Each row is shaded against its own range — darker = relatively higher share.</div>', unsafe_allow_html=True)

        _hm_months = _kw_all_months[-18:] if len(_kw_all_months) > 18 else _kw_all_months[:]
        _hm_share = {}
        for _hm_m in _hm_months:
            _hm_mdf = kw_df[kw_df["month"] == _hm_m]
            if not _hm_mdf.empty:
                _hm_tot = float(_hm_mdf["impressions"].sum())
                for _hm_cat_k, _hm_imp_v in _hm_mdf.groupby("category")["impressions"].sum().items():
                    if _hm_cat_k not in _hm_share:
                        _hm_share[_hm_cat_k] = {}
                    _hm_share[_hm_cat_k][_hm_m] = _hm_imp_v / _hm_tot * 100 if _hm_tot > 0 else 0.0

        _hm_cats = sorted(_hm_share.keys(), key=lambda c: _hm_share.get(c, {}).get(_kw_lm, 0), reverse=True)
        _hm_hdr_cells = "".join(f'<th style="font-size:9px;text-align:center;white-space:nowrap;padding:4px 3px;font-weight:600;color:#6B7280">{month_label(m)}</th>' for m in _hm_months)
        _hm_hdr = f'<thead><tr><th style="text-align:left;padding:6px 10px;font-weight:700;min-width:160px">Category</th>{_hm_hdr_cells}</tr></thead>'
        _hm_body = ""
        for _hm_cat in _hm_cats:
            _hm_vals = [_hm_share.get(_hm_cat, {}).get(m, 0) for m in _hm_months]
            if not any(v > 0 for v in _hm_vals):
                continue
            _hm_rmax = max(_hm_vals) if _hm_vals else 1
            _hm_rmin = min(v for v in _hm_vals if v > 0) if any(v > 0 for v in _hm_vals) else 0
            _hm_raw_c = CATEGORY_COLORS.get(_hm_cat, "#4736FE"); _hm_chex = _hm_raw_c.lstrip("#")
            _hm_cr = int(_hm_chex[0:2], 16); _hm_cg = int(_hm_chex[2:4], 16); _hm_cb2 = int(_hm_chex[4:6], 16)
            _hm_dot = f'<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:{_hm_raw_c};margin-right:5px;vertical-align:middle"></span>'
            _hm_cells = f'<td style="font-weight:600;font-size:11px;white-space:nowrap;padding:6px 10px">{_hm_dot}{_hm_cat}</td>'
            for _hm_mi, _hm_m2 in enumerate(_hm_months):
                _hm_v = _hm_vals[_hm_mi]
                _hm_inty = (_hm_v - _hm_rmin) / (_hm_rmax - _hm_rmin) if _hm_rmax > _hm_rmin else 0.0
                _hm_bg = f"rgba({_hm_cr},{_hm_cg},{_hm_cb2},{_hm_inty:.2f})"
                _hm_txt = "white" if _hm_inty > 0.55 else "#020618"
                _hm_fw = "700" if _hm_inty > 0.8 else ("400" if _hm_v == 0 else "500")
                _hm_disp = f"{_hm_v:.1f}%" if _hm_v > 0 else "—"
                _hm_cells += f'<td style="text-align:center;background:{_hm_bg};color:{_hm_txt};padding:5px 3px;font-size:10px;font-weight:{_hm_fw}">{_hm_disp}</td>'
            _hm_body += f"<tr>{_hm_cells}</tr>"

        st.markdown(f'<div class="tbl-card" style="overflow-x:auto"><table style="border-collapse:collapse;width:100%;min-width:700px">{_hm_hdr}<tbody>{_hm_body}</tbody></table></div>', unsafe_allow_html=True)

        # ── Section 4b: Absolute Volume by Category — heatmap ─────────────────
        st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,{C24_BLUE} 0%,#1D1160 100%)"><span class="sec-banner-icon">📦</span><div><div class="sec-banner-title">Absolute Volume by Category</div><div class="sec-banner-sub">Raw impressions per category per month — each row shaded against its own range</div></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-desc">Absolute monthly impressions by keyword category. Unlike the share view, this shows whether each category is growing or shrinking in real terms. Each row is shaded against its own min/max — darker = relatively higher volume for that category.</div>', unsafe_allow_html=True)

        _av_months = _kw_all_months[-18:] if len(_kw_all_months) > 18 else _kw_all_months[:]
        _av_vol = {}
        for _av_m in _av_months:
            _av_mdf = kw_df[kw_df["month"] == _av_m]
            if not _av_mdf.empty:
                for _av_cat_k, _av_imp_v in _av_mdf.groupby("category")["impressions"].sum().items():
                    if _av_cat_k not in _av_vol:
                        _av_vol[_av_cat_k] = {}
                    _av_vol[_av_cat_k][_av_m] = float(_av_imp_v)

        _av_cats = sorted(_av_vol.keys(), key=lambda c: _av_vol.get(c, {}).get(_kw_lm, 0), reverse=True)
        _av_hdr_cells = "".join(f'<th style="font-size:9px;text-align:center;white-space:nowrap;padding:4px 3px;font-weight:600;color:#6B7280">{month_label(m)}</th>' for m in _av_months)
        _av_hdr = f'<thead><tr><th style="text-align:left;padding:6px 10px;font-weight:700;min-width:160px">Category</th>{_av_hdr_cells}<th style="font-size:9px;text-align:center;white-space:nowrap;padding:4px 6px;font-weight:600;color:#6B7280">MoM Δ</th></tr></thead>'
        _av_body = ""
        for _av_cat in _av_cats:
            _av_vals = [_av_vol.get(_av_cat, {}).get(m, 0.0) for m in _av_months]
            if not any(v > 0 for v in _av_vals):
                continue
            _av_rmax = max(_av_vals) if _av_vals else 1
            _av_rmin = min(v for v in _av_vals if v > 0) if any(v > 0 for v in _av_vals) else 0
            _av_raw_c = CATEGORY_COLORS.get(_av_cat, "#4736FE"); _av_chex = _av_raw_c.lstrip("#")
            _av_cr = int(_av_chex[0:2], 16); _av_cg = int(_av_chex[2:4], 16); _av_cb = int(_av_chex[4:6], 16)
            _av_dot = f'<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:{_av_raw_c};margin-right:5px;vertical-align:middle"></span>'
            _av_cells = f'<td style="font-weight:600;font-size:11px;white-space:nowrap;padding:6px 10px">{_av_dot}{_av_cat}</td>'
            for _av_mi, _av_m2 in enumerate(_av_months):
                _av_v = _av_vals[_av_mi]
                _av_inty = (_av_v - _av_rmin) / (_av_rmax - _av_rmin) if _av_rmax > _av_rmin else 0.0
                _av_bg = f"rgba({_av_cr},{_av_cg},{_av_cb},{_av_inty:.2f})"
                _av_txt = "white" if _av_inty > 0.55 else "#020618"
                _av_fw = "700" if _av_inty > 0.8 else ("400" if _av_v == 0 else "500")
                _av_disp = f"{_av_v/1e5:.2f}L" if _av_v > 0 else "—"
                _av_cells += f'<td style="text-align:center;background:{_av_bg};color:{_av_txt};padding:5px 3px;font-size:10px;font-weight:{_av_fw}">{_av_disp}</td>'
            # MoM delta column: last vs second-to-last month
            _av_last = _av_vol.get(_av_cat, {}).get(_av_months[-1], 0.0)
            _av_prev = _av_vol.get(_av_cat, {}).get(_av_months[-2], 0.0) if len(_av_months) >= 2 else 0.0
            _av_mom_val = pct_ch(_av_last, _av_prev) if _av_prev > 0 else float("nan")
            _av_mom_disp = grc(_av_mom_val) if _v(_av_mom_val) else '<span style="color:#6B7280">—</span>'
            _av_cells += f'<td style="text-align:center;padding:5px 6px;font-size:10px;white-space:nowrap">{_av_mom_disp}</td>'
            _av_body += f"<tr>{_av_cells}</tr>"

        st.markdown(f'<div class="tbl-card" style="overflow-x:auto"><table style="border-collapse:collapse;width:100%;min-width:700px">{_av_hdr}<tbody>{_av_body}</tbody></table></div>', unsafe_allow_html=True)

        # ── Section 5: City Performance (top / bottom layout) ────────────────
        _ci_h, _ci_m_col, _ci_s_col = st.columns([3, 1, 1])
        with _ci_h:
            st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#1D1160 0%,{C24_BLUE} 100%)"><span class="sec-banner-icon">🏙️</span><div><div class="sec-banner-title">City Performance</div><div class="sec-banner-sub">Top cities by keyword impressions — MoM and YoY growth</div></div></div>', unsafe_allow_html=True)
        with _ci_m_col:
            _ci_city_months = sorted(city_df["month"].unique()) if not city_df.empty else _kw_all_months
            _ci_opts = [f"Current — {month_label(_ci_city_months[-1])}"] + [month_label(m) for m in reversed(_ci_city_months[:-1])]
            _ci_per  = st.selectbox("Month", _ci_opts, index=0, key="city_month2", label_visibility="collapsed")
        with _ci_s_col:
            _ci_sort = st.selectbox("Sort", ["Volume", "MoM Growth", "YoY Growth"], index=0, key="city_sort2", label_visibility="collapsed")

        _ci_sel_m = _ci_city_months[-1] if _ci_per.startswith("Current") else next((m for m in _ci_city_months if month_label(m) == _ci_per), _ci_city_months[-1])
        _ci_idx = _ci_city_months.index(_ci_sel_m) if _ci_sel_m in _ci_city_months else len(_ci_city_months) - 1
        _ci_pm  = _ci_city_months[_ci_idx - 1] if _ci_idx > 0 else None
        _ci_ym  = next((m for m in _ci_city_months if m[:4] == str(int(_ci_sel_m[:4]) - 1) and m[5:] == _ci_sel_m[5:]), None)

        if not city_df.empty:
            st.markdown(f'<div class="sec-desc">Cities showing strong MoM growth indicate active campaign influence or seasonal demand. Consistent YoY growth in Tier 2 cities signals footprint expansion.</div>', unsafe_allow_html=True)
            _ci_cc = city_df[city_df["month"] == _ci_sel_m].copy()
            _ci_cp = city_df[city_df["month"] == _ci_pm].copy() if _ci_pm else pd.DataFrame()
            _ci_cy = city_df[city_df["month"] == _ci_ym].copy() if _ci_ym else pd.DataFrame()
            if not _ci_cc.empty:
                for _src, _cname in [(_ci_cp, "prev_imp"), (_ci_cy, "yoy_imp")]:
                    _ci_cc = _ci_cc.merge(_src[["city","impressions"]].rename(columns={"impressions":_cname}), on="city", how="left") if not _src.empty else _ci_cc.assign(**{_cname: float("nan")})
                _ci_cc["mom_pct"] = _ci_cc.apply(lambda r: pct_ch(r["impressions"], r.get("prev_imp")), axis=1)
                _ci_cc["yoy_pct"] = _ci_cc.apply(lambda r: pct_ch(r["impressions"], r.get("yoy_imp")), axis=1)
                if _ci_sort == "MoM Growth":
                    _ci_cc = _ci_cc.sort_values("mom_pct", ascending=False)
                elif _ci_sort == "YoY Growth":
                    _ci_cc = _ci_cc.sort_values("yoy_pct", ascending=False)
                else:
                    _ci_cc = _ci_cc.sort_values("impressions", ascending=False)
                _ci_cc = _ci_cc.reset_index(drop=True)

                _ci_rows = ""
                for _, _cr in _ci_cc.head(30).iterrows():
                    _ci_rcls = "tbl-up" if _v(_cr.get("mom_pct")) and _cr.get("mom_pct") > 0 else "tbl-down" if _v(_cr.get("mom_pct")) and _cr.get("mom_pct") < 0 else ""
                    _ci_rows += f'<tr class="{_ci_rcls}"><td><strong>{_cr["city"]}</strong></td><td>{_cr["impressions"]:,}</td><td>{grc(_cr.get("mom_pct"))}</td><td>{grc(_cr.get("yoy_pct"))}</td></tr>'
                st.markdown(f'<div class="tbl-card"><div class="scroll-tbl"><table class="pt"><thead><tr><th>City</th><th>Impressions</th><th>MoM</th><th>YoY</th></tr></thead><tbody>{_ci_rows}</tbody></table></div></div>', unsafe_allow_html=True)
                _t20 = _ci_cc.sort_values("impressions", ascending=False).head(20)
                fig_cb = go.Figure(go.Bar(
                    y=_t20["city"], x=_t20["impressions"], orientation="h",
                    marker_color=[C24_BLUE if i == 0 else "#B8B5FF" for i in range(len(_t20))],
                    text=_t20["impressions"].apply(lambda v: f"{v/1000:.0f}K"),
                    textposition="outside", textfont=dict(size=9, color=C24_BLACK),
                    hovertemplate="<b>%{y}</b><br>%{x:,}<extra></extra>",
                ))
                fig_cb.update_layout(**std_layout(480, margin=dict(t=20, b=20, l=10, r=80), showlegend=False,
                    xaxis=ax(tickformat=",", showgrid=True), yaxis=ax(autorange="reversed")))
                st.plotly_chart(fig_cb, use_container_width=True)

                _ci_by_vol = _ci_cc.sort_values("impressions", ascending=False)
                _ci_by_mom = _ci_cc.dropna(subset=["mom_pct"]).sort_values("mom_pct", ascending=False)
                if not _ci_by_mom.empty:
                    _tv_r = _ci_by_vol.iloc[0]; _fc_r = _ci_by_mom.iloc[0]
                    st.markdown(ibox(f"Top city: <strong>{_tv_r['city']}</strong> ({_tv_r['impressions']:,} · {grc(_tv_r.get('mom_pct'))} MoM). Fastest growing: <strong>{_fc_r['city']}</strong> ({grc(_fc_r['mom_pct'])} MoM · {grc(_fc_r.get('yoy_pct'))} YoY)."), unsafe_allow_html=True)

        # ── Section 6: City Concentration ─────────────────────────────────────
        _cc_hd, _cc_p_col = st.columns([4, 1])
        with _cc_hd:
            st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,{C24_BLUE} 0%,#2818B4 100%)"><span class="sec-banner-icon">🗺️</span><div><div class="sec-banner-title">City Concentration</div><div class="sec-banner-sub">Top-5 cities\' share of total impressions — how concentrated demand is</div></div></div>', unsafe_allow_html=True)
            st.markdown('<div class="sec-desc"><strong>High concentration</strong> = metro-skewed demand. <strong>Falling concentration</strong> = Cars24 expanding to Tier 2/3 — a healthy long-term signal.</div>', unsafe_allow_html=True)
        with _cc_p_col:
            _cc_per = st.selectbox("Period", ["All time", "Last 90 days", "Last 60 days", "Last 30 days"], index=0, key="city_conc_per", label_visibility="collapsed")

        if not city_df.empty:
            _cc_city_months_all = sorted(city_df["month"].unique())
            _cc_n = {"Last 30 days": 1, "Last 60 days": 2, "Last 90 days": 3}.get(_cc_per, len(_cc_city_months_all))
            _cc_months = _cc_city_months_all[-_cc_n:]
            _cc_prev_months = _cc_city_months_all[max(0, len(_cc_city_months_all) - 2 * _cc_n):len(_cc_city_months_all) - _cc_n] if _cc_n < len(_cc_city_months_all) else []
            _cc_df_sel  = city_df[city_df["month"].isin(_cc_months)]
            _cc_df_prev = city_df[city_df["month"].isin(_cc_prev_months)] if _cc_prev_months else pd.DataFrame()
            if not _cc_df_sel.empty:
                _cc_agg   = _cc_df_sel.groupby("city")["impressions"].sum()
                _tot_city = float(_cc_agg.sum())
                _top5     = _cc_agg.nlargest(5).reset_index()
                _top5_share = _top5["impressions"].sum() / _tot_city * 100 if _tot_city > 0 else 0.0
                _prev_conc_v = None
                if not _cc_df_prev.empty:
                    _prev_agg = _cc_df_prev.groupby("city")["impressions"].sum()
                    _prev_tot = float(_prev_agg.sum())
                    _prev_conc_v = _prev_agg.nlargest(5).sum() / _prev_tot * 100 if _prev_tot > 0 else None
                _conc_shift = pp_ch(_top5_share, _prev_conc_v)
                _conc_dir   = ("🔴 Rising — demand becoming more concentrated" if _conc_shift and _conc_shift > 0 else "🟢 Falling — footprint expanding to more cities" if _conc_shift and _conc_shift < 0 else "→ Stable")
                _conc_clr   = "#FB2C36" if _conc_shift and _conc_shift > 0 else "#00C951" if _conc_shift and _conc_shift < 0 else "#6B7280"
                conc_cols = st.columns([2, 1, 1, 1, 1, 1])
                conc_cols[0].markdown(f'<div class="kpi-card" style="background:linear-gradient(135deg,rgba(71,54,254,.08),rgba(71,54,254,.02));border:1.5px solid rgba(71,54,254,.2)"><div class="kpi-lbl">🗺️ Top-5 Concentration</div><div class="kpi-val" style="font-size:32px;color:#020618">{_top5_share:.1f}%</div><div class="kpi-sub" style="font-size:11px">{grc(_conc_shift, is_pp=True) if _conc_shift else "—"} vs prior period</div><div style="font-size:10px;color:{_conc_clr};font-weight:700;margin-top:6px">{_conc_dir}</div></div>', unsafe_allow_html=True)
                _city_cc_palette = [C24_BLUE, "#1D1160", "#4736FE", "#7B73FF", "#B8B5FF"]
                for _cc2i, _cc2row in _top5.iterrows():
                    _sh2 = _cc2row["impressions"] / _tot_city * 100
                    _cc2_col = _city_cc_palette[_cc2i]
                    conc_cols[_cc2i + 1].markdown(f'<div class="kpi-card" style="border-top:3px solid {_cc2_col}"><div class="kpi-lbl">#{_cc2i+1} {_cc2row["city"]}</div><div class="kpi-val" style="font-size:22px;color:{_cc2_col}">{_sh2:.1f}%</div><div class="kpi-sub">{_cc2row["impressions"]:,}</div></div>', unsafe_allow_html=True)

        # ── Section 7: Top 10 Keywords by Volume ──────────────────────────────
        _tk_hd, _tk_fl = st.columns([4, 1])
        with _tk_hd:
            st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#020618 0%,#1D1160 100%)"><span class="sec-banner-icon">🔍</span><div><div class="sec-banner-title">Top 10 Keywords by Volume</div><div class="sec-banner-sub">Highest-impression individual keywords driving Cars24 brand search</div></div></div>', unsafe_allow_html=True)
            st.markdown('<div class="sec-desc">The exact search terms users type when looking for Cars24. Dominance of short-form brand queries (e.g. "cars24") signals strong aided recall. Rising city-specific keywords indicate local market penetration.</div>', unsafe_allow_html=True)
        with _tk_fl:
            _tk_opts = [f"Current — {_kw_lbl}"] + [month_label(m) for m in _kw_all_desc[1:]] + ["All time"]
            _tk_per  = st.selectbox("Period", _tk_opts, index=0, key="top_kw_per", label_visibility="collapsed")

        if _tk_per == "All time":
            _tk_base = kw_df.groupby("keyword").agg(impressions=("impressions","sum"), category=("category","first")).reset_index()
            _tk_df = _tk_base.sort_values("impressions", ascending=False)
        elif _tk_per.startswith("Current"):
            _tk_df = _kw_lat_df.sort_values("impressions", ascending=False)
        else:
            _tk_m  = next((m for m in _kw_all_months if month_label(m) == _tk_per), _kw_lm)
            _tk_df = kw_df[kw_df["month"] == _tk_m].sort_values("impressions", ascending=False)

        _top10 = _tk_df.head(10)
        _tk_c1, _tk_c2 = st.columns(2)
        with _tk_c1:
            _tk_items = []
            for _, _tr in _top10.head(5).iterrows():
                _tcat = _tr.get("category",""); _tcol = CATEGORY_COLORS.get(_tcat,"#888")
                _tk_items.append((_tr["keyword"], f'<span class="badge" style="background:{_tcol}22;color:{_tcol}">{_tcat}</span>', f'{_tr["impressions"]/1000:.0f}K', C24_BLUE))
            st.markdown(rank_list(_tk_items, title="Top 5 Keywords", badge="impressions", accent=C24_BLUE), unsafe_allow_html=True)
        with _tk_c2:
            _tk_items2 = []
            for _, _tr in _top10.iloc[5:10].iterrows():
                _tcat = _tr.get("category",""); _tcol = CATEGORY_COLORS.get(_tcat,"#888")
                _tk_items2.append((_tr["keyword"], f'<span class="badge" style="background:{_tcol}22;color:{_tcol}">{_tcat}</span>', f'{_tr["impressions"]/1000:.0f}K', "#8B7FFF"))
            if _tk_items2:
                st.markdown(rank_list(_tk_items2, title="Keywords 6–10", badge="impressions", accent="#8B7FFF"), unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SHARE OF SEARCHES (BSOS)
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    try:
        _bm3 = bsos_pan_m.copy() if not bsos_pan_m.empty else bsos_m.copy() if not bsos_m.empty else pd.DataFrame()
        _bd3 = bsos_pan_d.copy() if not bsos_pan_d.empty else bsos_d.copy() if not bsos_d.empty else pd.DataFrame()
        _bw3 = bsos_pan_w.copy() if not bsos_pan_w.empty else bsos_w.copy() if not bsos_w.empty else pd.DataFrame()

        if _bm3.empty and _bd3.empty:
            st.info("BSOS data not available.")
        else:
            def _mv(row, col):
                if row is None: return None
                v = row.get(col) if hasattr(row,"get") else (row[col] if col in row.index else None)
                return float(v) if v is not None and not (isinstance(v,float) and np.isnan(v)) else None

            # table-header display: wraps long names so they don't stretch columns
            def _bthdr(b):
                return {"MFC": "Mahindra<br>First Choice",
                        "MTV": "Maruti<br>True Value",
                        "OLX": "OLX Auto",
                        "CarWale": "CarWale",
                        "Cardekho": "CarDekho",
                        "Spinny": "Spinny",
                        "Cars24": "Cars24"}.get(b, b)

            _m3_last = _bm3.iloc[-1] if not _bm3.empty else None
            _m3_prev = _bm3.iloc[-2] if len(_bm3) >= 2 else None
            _m3_lbl  = month_label(_m3_last["month"]) if _m3_last is not None else "Latest"
            _m3_c24  = _mv(_m3_last,"Cars24"); _m3_c24p = _mv(_m3_prev,"Cars24")
            _m3_cw   = _mv(_m3_last,"CarWale"); _m3_cd = _mv(_m3_last,"Cardekho")
            _m3_mfc  = _mv(_m3_last,"MFC");     _m3_mtv = _mv(_m3_last,"MTV")
            _sp3_rows = _bm3[_bm3["Spinny"].notna()] if not _bm3.empty and "Spinny" in _bm3.columns else pd.DataFrame()
            _sp3_last = _sp3_rows.iloc[-1] if not _sp3_rows.empty else None
            _sp3_prev = _sp3_rows.iloc[-2] if len(_sp3_rows) >= 2 else None
            _m3_sp   = _mv(_sp3_last,"Spinny"); _m3_sp_lbl = month_label(_sp3_last["month"]) if _sp3_last is not None else "N/A"
            _m3_mom  = pp_ch(_m3_c24, _m3_c24p)
            _vs_sp   = (_m3_c24 - _m3_sp)  if _m3_c24 is not None and _m3_sp is not None else None
            _vs_cw   = (_m3_c24 - _m3_cw)  if _m3_c24 is not None and _m3_cw is not None else None
            _vs_cd   = (_m3_c24 - _m3_cd)  if _m3_c24 is not None and _m3_cd is not None else None

            # rank among brands
            _t3_know = {b: _mv(_m3_last,b) for b in ["Cars24","CarWale","Cardekho","MFC","MTV"] if _mv(_m3_last,b) is not None}
            if _m3_sp is not None: _t3_know["Spinny"] = _m3_sp
            _t3_rank = sorted(_t3_know.items(), key=lambda x: x[1], reverse=True)
            _t3_c24r = next((i+1 for i,(b,_) in enumerate(_t3_rank) if b=="Cars24"), None)

            # ── Hero banner ────────────────────────────────────────────────────
            _c24_int = int(round(_m3_c24)) if _m3_c24 else 0
            _mom_sign = f"{grc(_m3_mom, is_pp=True)} vs last month" if _v(_m3_mom) else ""
            st.markdown(f'''<div style="background:linear-gradient(135deg,#020618 0%,#1D1160 100%);
              padding:20px 26px;border-radius:14px;margin-bottom:16px">
              <div style="font-size:11px;font-weight:600;color:rgba(255,255,255,.45);
                letter-spacing:1.2px;text-transform:uppercase;margin-bottom:6px">
                Cars24 · Share of Searches · All-India · {_m3_lbl}
              </div>
              <div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap">
                <div style="font-size:52px;font-weight:900;color:#fff;line-height:1">
                  {f"{_m3_c24:.1f}%" if _m3_c24 else "—"}
                </div>
                <div style="font-size:15px;color:rgba(255,255,255,.7)">{_mom_sign}</div>
              </div>
              <div style="font-size:12px;color:rgba(255,255,255,.45);margin-top:8px">
                Out of every 100 people searching for a used car online,
                <strong style="color:rgba(255,255,255,.8)">{_c24_int}</strong>
                searched for Cars24 · Brandstack BSOS data · Spinny last available: {_m3_sp_lbl}
              </div>
            </div>''', unsafe_allow_html=True)

            # ── 4 KPI cards ────────────────────────────────────────────────────
            _k1, _k2, _k3, _k4 = st.columns(4)
            _k1.markdown(f'''<div class="kpi-card" style="border-top-color:{C24_BLUE}">
              <div class="kpi-lbl">Cars24 SoS · {_m3_lbl}</div>
              <div class="kpi-val" style="color:{C24_BLUE}">{f"{_m3_c24:.1f}%" if _m3_c24 else "—"}</div>
              <div class="kpi-sub">{grc(_m3_mom, is_pp=True)} vs last month</div>
            </div>''', unsafe_allow_html=True)
            _k2.markdown(f'''<div class="kpi-card" style="border-top-color:{C24_ORANGE}">
              <div class="kpi-lbl">Our Rank · {_m3_lbl}</div>
              <div class="kpi-val" style="color:{C24_ORANGE}">#{_t3_c24r if _t3_c24r else "—"} of {len(_t3_rank)}</div>
              <div class="kpi-sub">Leader: {bdisplay(_t3_rank[0][0])} {_t3_rank[0][1]:.1f}%</div>
            </div>''', unsafe_allow_html=True)
            _sp_lead = "Cars24 leads ✅" if _vs_sp and _vs_sp > 0 else ("Spinny leads ⚠️" if _vs_sp and _vs_sp < 0 else "Tied")
            _k3.markdown(f'''<div class="kpi-card" style="border-top-color:{SPINNY_COLOR}">
              <div class="kpi-lbl">vs Spinny · {_m3_sp_lbl}</div>
              <div class="kpi-val" style="color:{C24_GREEN if _vs_sp and _vs_sp > 0 else SPINNY_COLOR}">{f"{_vs_sp:+.1f} pp" if _vs_sp is not None else "—"}</div>
              <div class="kpi-sub">{_sp_lead}</div>
            </div>''', unsafe_allow_html=True)
            _cw_lead = "Cars24 leads ✅" if _vs_cw and _vs_cw > 0 else ("CarWale leads ⚠️" if _vs_cw and _vs_cw < 0 else "Tied")
            _k4.markdown(f'''<div class="kpi-card" style="border-top-color:{CARWALE_COLOR}">
              <div class="kpi-lbl">vs CarWale · {_m3_lbl}</div>
              <div class="kpi-val" style="color:{C24_GREEN if _vs_cw and _vs_cw > 0 else CARWALE_COLOR}">{f"{_vs_cw:+.1f} pp" if _vs_cw is not None else "—"}</div>
              <div class="kpi-sub">{_cw_lead}</div>
            </div>''', unsafe_allow_html=True)

            # insight
            _t3_ins = f"Cars24 SoS: <strong>{_m3_c24:.1f}%</strong> ({_m3_lbl})"
            if _t3_c24r: _t3_ins += f" — ranked <strong>#{_t3_c24r}</strong> of {len(_t3_rank)} brands"
            if _vs_cw is not None: _t3_ins += f". Gap vs CarWale: <strong>{_vs_cw:+.1f} pp</strong>"
            if _vs_cd is not None: _t3_ins += f". vs CarDekho: <strong>{_vs_cd:+.1f} pp</strong>"
            if _vs_sp is not None: _t3_ins += f". vs Spinny ({_m3_sp_lbl}): <strong>{_vs_sp:+.1f} pp</strong>"
            st.markdown(ibox(_t3_ins, "🏆"), unsafe_allow_html=True)

            # ── Section 1: All-India SoS Trend ─────────────────────────────────
            st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#1D1160 0%,{C24_BLUE} 100%);padding:14px 22px;border-radius:12px;margin-bottom:8px"><div style="font-size:16px;font-weight:700;color:#fff">All-India Share of Searches — Trend</div><div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:2px">How Cars24\'s search share has moved over time vs competitors · Monthly = default</div></div>', unsafe_allow_html=True)

            _tc1, _tc2, _tc3, _tc4 = st.columns([2, 3, 2, 2])
            with _tc1:
                _t3_gran = st.selectbox("Granularity", ["Monthly","Daily","Weekly"], index=0, key="t3_gran", label_visibility="collapsed")
            with _tc2:
                if _t3_gran == "Monthly":
                    _t3_per_opts = ["All time","Last 12 months","Last 6 months","Last 3 months","Custom range"]
                elif _t3_gran == "Daily":
                    _t3_per_opts = ["All time","Last 180 days","Last 90 days","Last 30 days","Custom range"]
                else:
                    _t3_per_opts = ["All time","Last 26 weeks","Last 12 weeks","Last 6 weeks","Custom range"]
                _t3_per = st.selectbox("Period", _t3_per_opts, index=0, key="t3_per", label_visibility="collapsed")

            _t3_custom = _t3_per == "Custom range"
            _t3_from = _t3_to = None
            if _t3_custom:
                _t3_src_min = _bd3["date"].min() if not _bd3.empty else pd.Timestamp("2025-05-01")
                _t3_src_max = _bd3["date"].max() if not _bd3.empty else pd.Timestamp("2026-12-31")
                with _tc3:
                    _t3_from = st.date_input("From", value=(_t3_src_max - pd.Timedelta(days=89)).date(), min_value=_t3_src_min.date(), max_value=_t3_src_max.date(), key="t3_from", label_visibility="collapsed")
                with _tc4:
                    _t3_to   = st.date_input("To", value=_t3_src_max.date(), min_value=_t3_src_min.date(), max_value=_t3_src_max.date(), key="t3_to", label_visibility="collapsed")

            if _t3_gran == "Daily" and not _bd3.empty:
                _t3_src = _bd3.copy(); _t3_xcol = "date"
                if _t3_custom and _t3_from and _t3_to:
                    _t3_src = _t3_src[(_t3_src["date"].dt.date >= _t3_from) & (_t3_src["date"].dt.date <= _t3_to)]
                else:
                    _t3_n = {"Last 180 days":180,"Last 90 days":90,"Last 30 days":30}.get(_t3_per, len(_t3_src))
                    _t3_src = _t3_src.tail(_t3_n)
                _t3_b_ord = ["Cars24","CarWale","Cardekho","MFC","MTV"]
            elif _t3_gran == "Weekly" and not _bw3.empty:
                _t3_src = _bw3.copy(); _t3_xcol = "week"
                if not _t3_custom:
                    _t3_n = {"Last 26 weeks":26,"Last 12 weeks":12,"Last 6 weeks":6}.get(_t3_per, len(_t3_src))
                    _t3_src = _t3_src.tail(_t3_n)
                _t3_b_ord = ["Cars24","CarWale","Cardekho","MFC","MTV"]
            else:
                _t3_src = _bm3.copy(); _t3_xcol = "month"
                if _t3_custom and _t3_from and _t3_to:
                    _t3_src = _t3_src[(_t3_src["month"] >= str(_t3_from)[:7]) & (_t3_src["month"] <= str(_t3_to)[:7])]
                else:
                    _t3_n = {"Last 12 months":12,"Last 6 months":6,"Last 3 months":3}.get(_t3_per, len(_t3_src))
                    _t3_src = _t3_src.tail(_t3_n)
                _t3_b_ord = ["Cars24","Spinny","CarWale","Cardekho","MFC","MTV"]

            fig_t3 = go.Figure()
            for _br in [b for b in _t3_b_ord if b in _t3_src.columns]:
                _lw = 2.8 if _br == "Cars24" else (2.0 if _br == "Spinny" else 1.4)
                _ms = 5 if _br in ("Cars24","Spinny") else 2
                fig_t3.add_trace(go.Scatter(
                    x=_t3_src[_t3_xcol], y=_t3_src[_br],
                    name=bdisplay(_br),
                    mode="lines+markers" if _t3_gran != "Daily" else "lines",
                    line=dict(color=BRAND_COLORS.get(_br,"#888"), width=_lw),
                    marker=dict(size=_ms),
                    connectgaps=True,
                    hovertemplate=f"<b>{bdisplay(_br)}</b>: %{{y:.1f}}%<extra></extra>"
                ))
            _t3_xax = ax(tickangle=-45, tickfont=dict(size=9, color=C24_BLACK), showgrid=False)
            if _t3_gran == "Daily": _t3_xax["tickformat"] = "%d %b"
            fig_t3.update_layout(**std_layout(340,
                xaxis=_t3_xax,
                yaxis=ax(ticksuffix="%", showgrid=True, range=[0,45]),
                legend=dict(orientation="h", y=1.06, x=0, font=dict(size=10)),
                margin=dict(t=24, b=48, l=48, r=16)
            ))
            st.plotly_chart(fig_t3, use_container_width=True)

            # ── Section 2: Competitor Table (MoM / WoW / DoD) ─────────────────
            st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,{C24_BLUE} 0%,#2818B4 100%);padding:14px 22px;border-radius:12px;margin-bottom:8px"><div style="font-size:16px;font-weight:700;color:#fff">Competitor Share of Searches — Detail Table</div><div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:2px">Every brand\'s search share side by side · Pick Month / Week / Day view · Cars24 highlighted in blue</div></div>', unsafe_allow_html=True)

            _tb1, _tb2, _tb3 = st.columns([2, 3, 3])
            with _tb1:
                _tb_gran = st.selectbox("View", ["Month-on-Month","Week-on-Week","Day-on-Day"], index=0, key="tb_gran", label_visibility="collapsed")
            with _tb2:
                if _tb_gran == "Month-on-Month":
                    _tb_per_base = ["All time","Custom range"] + [month_label(m) for m in sorted(_bm3["month"].unique(), reverse=True)[:18]]
                elif _tb_gran == "Week-on-Week":
                    _tb_per_base = ["All time","Last 4 weeks","Last 8 weeks","Last 12 weeks","Last 26 weeks","Custom range"]
                else:
                    _tb_per_base = ["All time","Last 7 days","Last 14 days","Last 30 days","Last 60 days","Custom range"]
                _tb_per = st.selectbox("Period", _tb_per_base, index=0, key="tb_per", label_visibility="collapsed")
            with _tb3:
                _comp_pool = [b for b in ["Spinny","CarWale","Cardekho","MFC","MTV"] if not _bm3.empty and b in _bm3.columns]
                _tb_comps = st.multiselect("Competitors to show", options=_comp_pool, default=_comp_pool,
                                           format_func=bdisplay, key="tb_comps")
                if not _tb_comps: _tb_comps = _comp_pool

            _tb_custom = _tb_per == "Custom range"
            _tb_from = _tb_to = None
            if _tb_custom:
                _tbc1, _tbc2 = st.columns(2)
                _tb_min = _bd3["date"].min() if not _bd3.empty else pd.Timestamp("2025-05-01")
                _tb_max = _bd3["date"].max() if not _bd3.empty else pd.Timestamp("2026-12-31")
                with _tbc1:
                    _tb_from = st.date_input("From date", value=(_tb_max - pd.Timedelta(days=89)).date(), min_value=_tb_min.date(), max_value=_tb_max.date(), key="tb_from", label_visibility="collapsed")
                with _tbc2:
                    _tb_to   = st.date_input("To date", value=_tb_max.date(), min_value=_tb_min.date(), max_value=_tb_max.date(), key="tb_to", label_visibility="collapsed")

            _has_spinny_col = "Spinny" in (_bm3.columns if hasattr(_bm3, 'columns') else [])
            _tb_delta_lbl = {"Month-on-Month": "MoM Δ", "Week-on-Week": "WoW Δ", "Day-on-Day": "DoD Δ"}.get(_tb_gran, "Δ")
            _tb_c24_hdr = (f'<th style="color:{C24_BLUE};background:#EEF0FF;padding:6px 10px">Cars24</th>'
                           f'<th style="color:{C24_BLUE};font-size:10px;background:#EEF0FF;padding:6px 8px">{_tb_delta_lbl}</th>')
            _tb_comp_hdrs = "".join([
                f'<th style="color:{BRAND_COLORS.get(b,C24_TEXTGREY)};padding:6px 10px;white-space:nowrap">{_bthdr(b)}</th>'
                for b in _tb_comps
            ])
            _tb_ratio_hdr = '<th style="color:#888;font-size:10px;padding:6px 8px">Cars24<br>÷ Spinny</th>' if _has_spinny_col else ""
            _tb_rows = ""

            def _build_tb_row(period_label, c24_v, comp_vals, spinny_v, prev_c24, prev_spinny):
                _c24m = pp_ch(c24_v, prev_c24)
                _row  = f'<td style="padding:6px 10px"><strong>{period_label}</strong></td>'
                _row += f'<td style="color:{C24_BLUE};font-weight:700;background:#F5F4FF;padding:6px 10px">{f"{c24_v:.1f}%" if c24_v is not None else "—"}</td>'
                _row += f'<td style="font-size:11px;background:#F5F4FF;padding:6px 8px">{grc(_c24m, is_pp=True) if _v(_c24m) else "—"}</td>'
                for _tb_b, _bv in comp_vals.items():
                    _row += f'<td style="color:{BRAND_COLORS.get(_tb_b,C24_TEXTGREY)};padding:6px 10px">{f"{_bv:.1f}%" if _bv is not None else "—"}</td>'
                if _has_spinny_col:
                    _rat_c = (c24_v / spinny_v) if (c24_v is not None and spinny_v and spinny_v > 0) else None
                    _rat_p = (prev_c24 / prev_spinny) if (prev_c24 is not None and prev_spinny and prev_spinny > 0) else None
                    _rat_mom = pp_ch(_rat_c, _rat_p) if (_rat_c is not None and _rat_p is not None) else float("nan")
                    _rat_disp = f"{_rat_c:.2f}x" if _rat_c is not None else "—"
                    _rat_delta = f" <span style='font-size:9px'>{grc(_rat_mom,is_pp=True)}</span>" if _v(_rat_mom) else ""
                    _row += f'<td style="color:#888;font-size:11px;padding:6px 8px">{_rat_disp}{_rat_delta}</td>'
                return _row

            _tb_tbl_css = "border-collapse:collapse;width:100%;font-size:12px"
            _tb_hdr_css = "background:#EEF0FF"

            if _tb_gran == "Month-on-Month":
                _tb_data = _bm3.sort_values("month", ascending=False).reset_index(drop=True)
                if _tb_custom and _tb_from and _tb_to:
                    _tb_data = _bm3[(_bm3["month"] >= str(_tb_from)[:7]) & (_bm3["month"] <= str(_tb_to)[:7])].sort_values("month", ascending=False).reset_index(drop=True)
                elif _tb_per not in ("All time","Custom range"):
                    _m_sel = next((m for m in _bm3["month"].unique() if month_label(m) == _tb_per), None)
                    if _m_sel: _tb_data = _bm3[_bm3["month"] == _m_sel].sort_values("month", ascending=False).reset_index(drop=True)
                for _ti, (_, _tr) in enumerate(_tb_data.iterrows()):
                    _tp = _tb_data.iloc[_ti+1] if _ti+1 < len(_tb_data) else None
                    _cv = {b: _mv(_tr, b) for b in _tb_comps}
                    _tb_rows += f"<tr>{_build_tb_row(month_label(_tr['month']), _mv(_tr,'Cars24'), _cv, _mv(_tr,'Spinny'), _mv(_tp,'Cars24') if _tp is not None else None, _mv(_tp,'Spinny') if _tp is not None else None)}</tr>"
                st.markdown(f'<div class="tbl-card"><div class="scroll-tbl" style="max-height:420px"><table style="{_tb_tbl_css}"><thead style="{_tb_hdr_css}"><tr><th style="padding:8px 10px">Month</th>{_tb_c24_hdr}{_tb_comp_hdrs}{_tb_ratio_hdr}</tr></thead><tbody>{_tb_rows}</tbody></table></div></div>', unsafe_allow_html=True)

            elif _tb_gran == "Week-on-Week":
                _tb_data = _bw3.copy() if not _bw3.empty else pd.DataFrame()
                if not _tb_data.empty and not _tb_custom:
                    _wn = {"Last 4 weeks":4,"Last 8 weeks":8,"Last 12 weeks":12,"Last 26 weeks":26}.get(_tb_per, len(_tb_data))
                    _tb_data = _tb_data.tail(_wn)
                if not _tb_data.empty:
                    _tb_data = _tb_data.iloc[::-1].reset_index(drop=True)
                    _has_sp_w = "Spinny" in _tb_data.columns
                    for _ti, (_, _tr) in enumerate(_tb_data.iterrows()):
                        _tp = _tb_data.iloc[_ti+1] if _ti+1 < len(_tb_data) else None
                        _cv = {b: (_mv(_tr, b) if b in _tb_data.columns else None) for b in _tb_comps}
                        _tb_rows += f"<tr>{_build_tb_row(_tr['week'], _mv(_tr,'Cars24'), _cv, _mv(_tr,'Spinny') if _has_sp_w else None, _mv(_tp,'Cars24') if _tp is not None else None, _mv(_tp,'Spinny') if _tp is not None and _has_sp_w else None)}</tr>"
                    _sp_wh = '<th style="color:#888;font-size:10px;padding:6px 8px">Cars24<br>÷ Spinny</th>' if _has_sp_w else ""
                    st.markdown(f'<div class="tbl-card"><div class="scroll-tbl" style="max-height:420px"><table style="{_tb_tbl_css}"><thead style="{_tb_hdr_css}"><tr><th style="padding:8px 10px">Week</th>{_tb_c24_hdr}{_tb_comp_hdrs}{_sp_wh}</tr></thead><tbody>{_tb_rows}</tbody></table></div></div>', unsafe_allow_html=True)
                else:
                    st.info("Weekly data not available.")

            else:  # Day-on-Day
                _tb_data = _bd3.copy() if not _bd3.empty else pd.DataFrame()
                if not _tb_data.empty:
                    if _tb_custom and _tb_from and _tb_to:
                        _tb_data = _tb_data[(_tb_data["date"].dt.date >= _tb_from) & (_tb_data["date"].dt.date <= _tb_to)]
                    else:
                        _dn = {"Last 7 days":7,"Last 14 days":14,"Last 30 days":30,"Last 60 days":60}.get(_tb_per, 30)
                        _tb_data = _tb_data.tail(_dn)
                    _tb_data = _tb_data.iloc[::-1].reset_index(drop=True)
                    _has_sp_d = "Spinny" in _tb_data.columns
                    for _ti, (_, _tr) in enumerate(_tb_data.iterrows()):
                        _tp = _tb_data.iloc[_ti+1] if _ti+1 < len(_tb_data) else None
                        _cv = {b: (_mv(_tr, b) if b in _tb_data.columns else None) for b in _tb_comps}
                        _tb_rows += f"<tr>{_build_tb_row(_tr['date'].strftime('%d %b %Y'), _mv(_tr,'Cars24'), _cv, _mv(_tr,'Spinny') if _has_sp_d else None, _mv(_tp,'Cars24') if _tp is not None else None, _mv(_tp,'Spinny') if _tp is not None and _has_sp_d else None)}</tr>"
                    _sp_dh = '<th style="color:#888;font-size:10px;padding:6px 8px">Cars24<br>÷ Spinny</th>' if _has_sp_d else ""
                    st.markdown(f'<div class="tbl-card"><div class="scroll-tbl" style="max-height:420px"><table style="{_tb_tbl_css}"><thead style="{_tb_hdr_css}"><tr><th style="padding:8px 10px">Date</th>{_tb_c24_hdr}{_tb_comp_hdrs}{_sp_dh}</tr></thead><tbody>{_tb_rows}</tbody></table></div></div>', unsafe_allow_html=True)
                else:
                    st.info("Daily data not available.")

            # ── Section 3: Cars24 by City — Latest Snapshot ────────────────────
            if not bsos_cd.empty:
                _all_cities = sorted(bsos_cd["city"].unique())
                _cd_brands_avail = [b for b in ["Cars24","Spinny","CarWale","Cardekho","MFC","MTV","OLX"] if b in bsos_cd.columns]

                # latest full month & previous month for city data
                _all_city_months = sorted(bsos_cd["date"].dt.to_period("M").astype(str).unique())
                _city_cur_m  = _all_city_months[-1] if _all_city_months else None
                _city_prev_m = _all_city_months[-2] if len(_all_city_months) >= 2 else None
                _city_cur_lbl  = month_label(_city_cur_m)  if _city_cur_m  else "Latest"
                _city_prev_lbl = month_label(_city_prev_m) if _city_prev_m else "Prev"

                def _city_month_avg(month_str):
                    if not month_str: return {}
                    _s = bsos_cd[bsos_cd["date"].dt.to_period("M").astype(str) == month_str]
                    return _s.groupby("city")[_cd_brands_avail].mean().to_dict("index")

                _cur_avgs  = _city_month_avg(_city_cur_m)
                _prev_avgs = _city_month_avg(_city_prev_m)

                st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#020618 0%,#1D1160 100%);padding:14px 22px;border-radius:12px;margin-bottom:8px"><div style="font-size:16px;font-weight:700;color:#fff">Cars24 Share of Searches — By City</div><div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:2px">Snapshot for {_city_cur_lbl} · All {len(_all_cities)} cities · Sorted by Cars24% high → low · Green = Cars24 leads that competitor</div></div>', unsafe_allow_html=True)

                _cbc_rows = ""
                _cbc_sorted = sorted(
                    _all_cities,
                    key=lambda c: (_cur_avgs.get(c,{}).get("Cars24") or 0),
                    reverse=True
                )
                for _cty in _cbc_sorted:
                    _ca  = _cur_avgs.get(_cty, {})
                    _pa  = _prev_avgs.get(_cty, {})
                    _c24_v    = _ca.get("Cars24");    _c24_prev_v = _pa.get("Cars24")
                    _sp_v     = _ca.get("Spinny");    _cw_v  = _ca.get("CarWale")
                    _cd_v     = _ca.get("Cardekho");  _mfc_v = _ca.get("MFC"); _mtv_v = _ca.get("MTV")
                    _c24_mom  = pp_ch(_c24_v, _c24_prev_v)
                    _vs_sp_c  = (_c24_v - _sp_v)  if _c24_v is not None and _sp_v  is not None else None
                    _vs_cw_c  = (_c24_v - _cw_v)  if _c24_v is not None and _cw_v  is not None else None
                    _vs_cd_c  = (_c24_v - _cd_v)  if _c24_v is not None and _cd_v  is not None else None
                    _vs_mfc_c = (_c24_v - _mfc_v) if _c24_v is not None and _mfc_v is not None else None
                    _vs_mtv_c = (_c24_v - _mtv_v) if _c24_v is not None and _mtv_v is not None else None
                    # rank
                    _crank_vals = {b: v for b,v in _ca.items() if v is not None and b in _cd_brands_avail}
                    _crank_ord  = sorted(_crank_vals.items(), key=lambda x: x[1], reverse=True)
                    _c24_r      = next((i+1 for i,(b,_) in enumerate(_crank_ord) if b=="Cars24"), "—")
                    _rank_col   = C24_GREEN if isinstance(_c24_r,int) and _c24_r <= 2 else (C24_ORANGE if isinstance(_c24_r,int) and _c24_r == 3 else C24_RED_FB)
                    def _gap_td(v):
                        if v is None: return '<td style="padding:5px 8px;color:#9CA3AF">—</td>'
                        _c = C24_GREEN if v > 0 else C24_RED_FB
                        return f'<td style="padding:5px 8px;color:{_c};font-weight:600">{v:+.1f}</td>'
                    _cbc_rows += f'''<tr>
                      <td style="padding:5px 10px"><strong>{_cty}</strong></td>
                      <td style="padding:5px 10px;color:{C24_BLUE};font-weight:700">{f"{_c24_v:.1f}%" if _c24_v is not None else "—"}</td>
                      <td style="padding:5px 8px;font-size:11px">{grc(_c24_mom,is_pp=True) if _v(_c24_mom) else "—"}</td>
                      <td style="padding:5px 8px;font-weight:700;color:{_rank_col}">#{_c24_r}</td>
                      {_gap_td(_vs_sp_c)}{_gap_td(_vs_cw_c)}{_gap_td(_vs_cd_c)}{_gap_td(_vs_mfc_c)}{_gap_td(_vs_mtv_c)}
                    </tr>'''
                _cbc_hdr = (f'<th style="padding:8px 10px">City</th>'
                            f'<th style="padding:8px 10px;color:{C24_BLUE};background:#EEF0FF">Cars24 %</th>'
                            f'<th style="padding:8px 8px;color:{C24_BLUE};background:#EEF0FF;font-size:10px">MoM Δ</th>'
                            f'<th style="padding:8px 8px;font-size:10px">Rank</th>'
                            f'<th style="padding:8px 8px;color:{SPINNY_COLOR};font-size:10px">vs<br>Spinny</th>'
                            f'<th style="padding:8px 8px;color:{CARWALE_COLOR};font-size:10px">vs<br>CarWale</th>'
                            f'<th style="padding:8px 8px;color:{DEKHO_COLOR};font-size:10px">vs<br>CarDekho</th>'
                            f'<th style="padding:8px 8px;color:{MFC_COLOR};font-size:10px">vs<br>Mahindra<br>First Choice</th>'
                            f'<th style="padding:8px 8px;color:{MTV_COLOR};font-size:10px">vs<br>Maruti<br>True Value</th>')
                st.markdown(f'<div class="tbl-card"><div style="font-size:10px;color:#6B7280;margin-bottom:4px">Gap columns = Cars24 % minus that competitor % · positive (green) = Cars24 higher · negative (red) = Cars24 lower</div><div class="scroll-tbl" style="max-height:420px"><table style="border-collapse:collapse;width:100%;font-size:12px"><thead style="background:#F5F4FF;position:sticky;top:0"><tr>{_cbc_hdr}</tr></thead><tbody>{_cbc_rows}</tbody></table></div></div>', unsafe_allow_html=True)

                # ── Section 4: Cars24 Growth by City (last 6 months) ──────────
                st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#1D1160 0%,{C24_BLUE} 100%);padding:14px 22px;border-radius:12px;margin-top:16px;margin-bottom:8px"><div style="font-size:16px;font-weight:700;color:#fff">Cars24 Share of Searches — City Growth</div><div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:2px">How each city\'s Cars24 SoS% has moved month by month · Read left = oldest · right = latest</div></div>', unsafe_allow_html=True)

                _growth_months = _all_city_months[-6:] if len(_all_city_months) >= 6 else _all_city_months
                _growth_lbls   = [month_label(m) for m in _growth_months]

                # build pivot: city × month → Cars24 avg
                _growth_data = {}
                for _cty in _all_cities:
                    _growth_data[_cty] = {}
                    for _gm in _growth_months:
                        _gmdf = bsos_cd[(bsos_cd["city"] == _cty) & (bsos_cd["date"].dt.to_period("M").astype(str) == _gm)]
                        _v_gm = float(_gmdf["Cars24"].mean()) if not _gmdf.empty and pd.notna(_gmdf["Cars24"].mean()) else None
                        _growth_data[_cty][_gm] = _v_gm

                # sort by latest month Cars24 desc
                _growth_sorted = sorted(_all_cities, key=lambda c: (_growth_data[c].get(_growth_months[-1]) or 0), reverse=True)

                _gr_rows = ""
                for _cty in _growth_sorted:
                    _vals = [_growth_data[_cty].get(m) for m in _growth_months]
                    _latest_v = _vals[-1]; _prev_v = _vals[-2] if len(_vals) >= 2 else None
                    _gr_mom = pp_ch(_latest_v, _prev_v)
                    # direction: count up vs down months
                    _diffs = [(_vals[i+1] - _vals[i]) for i in range(len(_vals)-1) if _vals[i] is not None and _vals[i+1] is not None]
                    _up_count = sum(1 for d in _diffs if d > 0.1)
                    _dn_count = sum(1 for d in _diffs if d < -0.1)
                    _trend_txt = f"▲{_up_count}" if _up_count > _dn_count else (f"▼{_dn_count}" if _dn_count > _up_count else "→")
                    _trend_col = C24_GREEN if _up_count > _dn_count else (C24_RED_FB if _dn_count > _up_count else C24_TEXTGREY)
                    _cells = ""
                    for _vi, _gv in enumerate(_vals):
                        # color: green if higher than first val, red if lower
                        _base = _vals[0]
                        if _gv is None:
                            _cells += '<td style="padding:5px 10px;color:#9CA3AF;text-align:right">—</td>'
                        else:
                            _vc = C24_BLUE if _vi == len(_vals)-1 else ("#374151" if _base is None else (C24_GREEN if _gv > _base + 0.2 else (C24_RED_FB if _gv < _base - 0.2 else "#374151")))
                            _fw = "700" if _vi == len(_vals)-1 else "400"
                            _cells += f'<td style="padding:5px 10px;color:{_vc};font-weight:{_fw};text-align:right">{_gv:.1f}%</td>'
                    _gr_rows += f'''<tr>
                      <td style="padding:5px 10px"><strong>{_cty}</strong></td>
                      {_cells}
                      <td style="padding:5px 8px;font-size:11px">{grc(_gr_mom,is_pp=True) if _v(_gr_mom) else "—"}</td>
                      <td style="padding:5px 8px;font-weight:700;color:{_trend_col};font-size:11px">{_trend_txt}</td>
                    </tr>'''
                _gr_month_hdrs = "".join([f'<th style="padding:8px 10px;color:#374151;text-align:right">{lbl}</th>' for lbl in _growth_lbls])
                _gr_hdr = (f'<th style="padding:8px 10px">City</th>'
                           f'{_gr_month_hdrs}'
                           f'<th style="padding:8px 8px;font-size:10px;color:{C24_BLUE}">Latest<br>MoM Δ</th>'
                           f'<th style="padding:8px 8px;font-size:10px">Trend</th>')
                st.markdown(f'<div class="tbl-card"><div style="font-size:10px;color:#6B7280;margin-bottom:4px">Latest month in <strong style="color:{C24_BLUE}">blue</strong> · Green = higher than first month shown · Red = lower · Sorted by latest month Cars24% high → low</div><div class="scroll-tbl" style="max-height:460px"><table style="border-collapse:collapse;width:100%;font-size:12px"><thead style="background:#F5F4FF;position:sticky;top:0"><tr>{_gr_hdr}</tr></thead><tbody>{_gr_rows}</tbody></table></div></div>', unsafe_allow_html=True)

                # ── Section 5: City Deep-Dive ──────────────────────────────────
                st.markdown(f'<div class="sec-banner" style="background:linear-gradient(135deg,#020618 0%,#1D1160 100%);padding:14px 22px;border-radius:12px;margin-top:16px;margin-bottom:8px"><div style="font-size:16px;font-weight:700;color:#fff">City Deep-Dive</div><div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:2px">Pick any city and view Cars24 vs all competitors month by month · Green highlighted rows = Cars24 #1 that month</div></div>', unsafe_allow_html=True)

                _dd1, _dd2 = st.columns([2, 2])
                with _dd1:
                    _cp_city = st.selectbox("Select city", _all_cities, key="cp_city")
                with _dd2:
                    _cp_gran = st.selectbox("View by", ["Month","Week","Day"], index=0, key="cp_gran")

                _cpdf = bsos_cd[bsos_cd["city"] == _cp_city].copy()
                _cp_has_spinny = "Spinny" in _cpdf.columns
                _cp_comp_cols  = [b for b in ["Spinny","CarWale","Cardekho","MFC","MTV"] if b in _cpdf.columns]
                _cp_rows = ""

                # compact header with line breaks for long names
                _dd_c24_hdr = f'<th style="color:{C24_BLUE};background:#EEF0FF;padding:6px 10px">Cars24 %</th><th style="color:{C24_BLUE};background:#EEF0FF;font-size:10px;padding:6px 8px">Δ</th>'
                _dd_comp_hdrs = "".join([f'<th style="color:{BRAND_COLORS.get(b,C24_TEXTGREY)};padding:6px 8px;white-space:nowrap">{_bthdr(b)}</th>' for b in _cp_comp_cols])
                _dd_ratio_hdr = '<th style="color:#888;font-size:10px;padding:6px 8px">Cars24<br>÷ Spinny</th>' if _cp_has_spinny else ""

                def _dd_row(period, c24, comp_vals, spinny_v, prev_c24, is_leader):
                    _c24m = pp_ch(c24, prev_c24)
                    _row_bg = "background:#F0FFF4;" if is_leader else ""
                    _row = f'<td style="padding:5px 10px;{_row_bg}"><strong>{period}</strong></td>'
                    _row += f'<td style="padding:5px 10px;color:{C24_BLUE};font-weight:700;background:#F5F4FF">{f"{c24:.1f}%" if c24 is not None else "—"}</td>'
                    _row += f'<td style="padding:5px 8px;font-size:11px;background:#F5F4FF">{grc(_c24m,is_pp=True) if _v(_c24m) else "—"}</td>'
                    for _cb, _cbv in comp_vals.items():
                        _row += f'<td style="padding:5px 8px;color:{BRAND_COLORS.get(_cb,C24_TEXTGREY)}">{f"{_cbv:.1f}%" if _cbv is not None else "—"}</td>'
                    if _cp_has_spinny:
                        _rat = (c24 / spinny_v) if (c24 is not None and spinny_v and spinny_v > 0) else None
                        _row += f'<td style="padding:5px 8px;color:#888;font-size:11px">{f"{_rat:.2f}x" if _rat is not None else "—"}</td>'
                    return _row

                if _cp_gran == "Month":
                    _cpdf["_p"] = _cpdf["date"].dt.to_period("M").astype(str)
                    _cp_pivot = _cpdf.groupby("_p")[_cd_brands_avail].mean().reset_index().sort_values("_p", ascending=False).head(14).reset_index(drop=True)
                    for _ci, (_, _cr) in enumerate(_cp_pivot.iterrows()):
                        _cnxt = _cp_pivot.iloc[_ci+1] if _ci+1 < len(_cp_pivot) else None
                        _cc24 = _mv(_cr,"Cars24")
                        _comp_vs = {b: _mv(_cr,b) for b in _cp_comp_cols}
                        _all_vs = {**{"Cars24":_cc24}, **{b:v for b,v in _comp_vs.items() if v is not None}}
                        _is_leader = _cc24 is not None and _cc24 == max(_all_vs.values()) if _all_vs else False
                        _cp_rows += f"<tr>{_dd_row(month_label(str(_cr['_p'])), _cc24, _comp_vs, _mv(_cr,'Spinny') if _cp_has_spinny else None, _mv(_cnxt,'Cars24') if _cnxt is not None else None, _is_leader)}</tr>"
                    _period_hdr = "Month"
                elif _cp_gran == "Week":
                    _cpdf["_ws"] = _cpdf["date"] - pd.to_timedelta(_cpdf["date"].dt.dayofweek, unit="d")
                    _cpdf["_we"] = _cpdf["_ws"] + pd.Timedelta(days=6)
                    _cpdf["_p"] = _cpdf.apply(lambda r: f"{r['_ws'].strftime('%d %b')} – {r['_we'].strftime('%d %b %Y')}", axis=1)
                    _cp_pivot = _cpdf.groupby(["_ws","_p"])[_cd_brands_avail].mean().reset_index().sort_values("_ws", ascending=False).head(16).reset_index(drop=True)
                    for _ci, (_, _cr) in enumerate(_cp_pivot.iterrows()):
                        _cnxt = _cp_pivot.iloc[_ci+1] if _ci+1 < len(_cp_pivot) else None
                        _cc24 = _mv(_cr,"Cars24")
                        _comp_vs = {b: (_mv(_cr,b) if b in _cp_pivot.columns else None) for b in _cp_comp_cols}
                        _all_vs = {"Cars24":_cc24, **{b:v for b,v in _comp_vs.items() if v is not None}}
                        _is_leader = _cc24 is not None and bool(_cc24 == max(_all_vs.values())) if _all_vs else False
                        _cp_rows += f"<tr>{_dd_row(_cr['_p'], _cc24, _comp_vs, _mv(_cr,'Spinny') if _cp_has_spinny else None, _mv(_cnxt,'Cars24') if _cnxt is not None else None, _is_leader)}</tr>"
                    _period_hdr = "Week"
                else:  # Day
                    _cp_pivot = _cpdf.sort_values("date", ascending=False).head(30).reset_index(drop=True)
                    for _ci, (_, _cr) in enumerate(_cp_pivot.iterrows()):
                        _cnxt = _cp_pivot.iloc[_ci+1] if _ci+1 < len(_cp_pivot) else None
                        _cc24 = _mv(_cr,"Cars24")
                        _comp_vs = {b: (_mv(_cr,b) if b in _cp_pivot.columns else None) for b in _cp_comp_cols}
                        _all_vs = {"Cars24":_cc24, **{b:v for b,v in _comp_vs.items() if v is not None}}
                        _is_leader = _cc24 is not None and bool(_cc24 == max(_all_vs.values())) if _all_vs else False
                        _cp_rows += f"<tr>{_dd_row(_cr['date'].strftime('%d %b %Y'), _cc24, _comp_vs, _mv(_cr,'Spinny') if _cp_has_spinny else None, _mv(_cnxt,'Cars24') if _cnxt is not None else None, _is_leader)}</tr>"
                    _period_hdr = "Date"

                st.markdown(f'<div class="tbl-card"><div style="font-size:10px;color:#6B7280;margin-bottom:4px">{_cp_city} · Light green rows = Cars24 ranked #1 that period among all competitors</div><div class="scroll-tbl" style="max-height:400px"><table style="border-collapse:collapse;width:100%;font-size:12px"><thead style="background:#F5F4FF;position:sticky;top:0"><tr><th style="padding:8px 10px">{_period_hdr}</th>{_dd_c24_hdr}{_dd_comp_hdrs}{_dd_ratio_hdr}</tr></thead><tbody>{_cp_rows}</tbody></table></div></div>', unsafe_allow_html=True)

                # ── City trend chart ───────────────────────────────────────────
                _cd_line = bsos_cd[bsos_cd["city"] == _cp_city].copy()
                _cd_b_line = [b for b in _cd_brands_avail if _cd_line[b].notna().any()]
                fig_cline = go.Figure()
                for _blc in _cd_b_line:
                    _lw_c = 2.5 if _blc == "Cars24" else (1.8 if _blc == "Spinny" else 1.2)
                    fig_cline.add_trace(go.Scatter(
                        x=_cd_line["date"], y=_cd_line[_blc],
                        name=bdisplay(_blc), mode="lines",
                        line=dict(color=BRAND_COLORS.get(_blc,"#888"), width=_lw_c),
                        hovertemplate=f"<b>{bdisplay(_blc)}</b>: %{{y:.1f}}%<extra></extra>"
                    ))
                fig_cline.update_layout(**std_layout(260,
                    xaxis=ax(tickangle=-45, tickfont=dict(size=9, color=C24_BLACK), showgrid=False, tickformat="%d %b"),
                    yaxis=ax(ticksuffix="%", showgrid=True),
                    legend=dict(orientation="h", y=1.06, x=0, font=dict(size=10)),
                    margin=dict(t=24, b=40, l=48, r=16),
                    title_text=f"{_cp_city} — Daily SoS Trend",
                    title_font=dict(size=13, color=C24_BLACK)
                ))
                st.plotly_chart(fig_cline, use_container_width=True)

    except Exception as e3:
        import traceback; st.error(f"BSOS error: {e3}"); st.code(traceback.format_exc())


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — GOOGLE INDEXED (Brandstack — indexed 0–100 style)
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    try:
        st.markdown(f"""<div class="ibox">
          <strong>Google Brandstack BSOS</strong> — provided by Google AM (Vimal Gupta).
          Uses a <strong>used-car focused keyword universe</strong>, so numbers differ from the BSOS tool above.
          All values here are percentage-based SoS (not 0–100 index). C24 shows ~21–24% vs 16–20% in Tab 3
          because this set includes more used-car specific searches.
          Data: <strong>May 2025–Mar 2026</strong>. Trends are directionally consistent with Tab 3.
        </div>""", unsafe_allow_html=True)

        if not bsos_gm.empty:
            _gml = bsos_gm.iloc[-1]; _gpl = bsos_gm.iloc[-2] if len(bsos_gm) >= 2 else None
            gc24 = float(_gml["Cars24"]); gsp = float(_gml.get("Spinny",0)); gcw = float(_gml.get("CarWale",0))
            gc24m = pp_ch(gc24, float(_gpl["Cars24"])) if _gpl is not None else float("nan")
            grat  = gc24/gsp*100 if gsp > 0 else float("nan")

            st.markdown(sec("Google BSOS Snapshot", f"Latest — {month_label(_gml['month'])}"), unsafe_allow_html=True)

            g1,g2,g3,g4 = st.columns(4)
            g1.markdown(f"""<div class="kpi-card" style="border-top-color:{C24_BLUE}">
              <div class="kpi-lbl">Cars24 (Google universe)</div>
              <div class="kpi-val" style="color:{C24_BLUE}">{gc24:.1f}%</div>
              <div class="kpi-sub">{grc(gc24m, is_pp=True)} MoM
                {sparkline_svg(list(bsos_gm["Cars24"]), color=C24_BLUE)}</div>
            </div>""", unsafe_allow_html=True)
            g2.markdown(f"""<div class="kpi-card" style="border-top-color:{SPINNY_COLOR}">
              <div class="kpi-lbl">Spinny (Google universe)</div>
              <div class="kpi-val" style="color:{SPINNY_COLOR}">{gsp:.1f}%</div>
              <div class="kpi-sub">Used-car focused set
                {sparkline_svg(list(bsos_gm["Spinny"]) if "Spinny" in bsos_gm.columns else [], color=SPINNY_COLOR)}</div>
            </div>""", unsafe_allow_html=True)
            _grat_ac = C24_GREEN if grat >= 100 else C24_ORANGE
            g3.markdown(f"""<div class="kpi-card" style="border-top-color:{_grat_ac}">
              <div class="kpi-lbl">C24 ÷ Spinny</div>
              <div class="kpi-val" style="color:{_grat_ac}">{grat:.0f}%</div>
              <div class="kpi-sub">Google universe only</div>
            </div>""", unsafe_allow_html=True)
            g4.markdown(f"""<div class="kpi-card">
              <div class="kpi-lbl">CarWale (Google)</div>
              <div class="kpi-val" style="font-size:22px;color:{CARWALE_COLOR}">{gcw:.1f}%</div>
              <div class="kpi-sub">C24 gap: {gc24-gcw:+.1f}pp</div>
            </div>""", unsafe_allow_html=True)

            # Monthly table + chart
            st.markdown(sec("Monthly Averages", "Google Brandstack — May 2025 to Mar 2026"), unsafe_allow_html=True)

            col_gmt, col_gmc = st.columns([1, 2])
            with col_gmt:
                _gmd = bsos_gm.sort_values("month", ascending=False).reset_index(drop=True)
                # Mark peak
                _g_peak_idx = bsos_gm["Cars24"].idxmax()
                _g_peak_month = bsos_gm.loc[_g_peak_idx, "month"]
                gmr = ""
                for i, (_, r) in enumerate(_gmd.iterrows()):
                    pr5 = _gmd.iloc[i+1] if i+1<len(_gmd) else None
                    mm5 = pp_ch(float(r["Cars24"]), float(pr5["Cars24"])) if pr5 else float("nan")
                    sp5 = float(r.get("Spinny",0)); rt5 = r["Cars24"]/sp5*100 if sp5>0 else float("nan")
                    peak_flag = " ⭐" if r["month"] == _g_peak_month else ""
                    gmr += f"""<tr>
                      <td><strong>{month_label(r['month'])}{peak_flag}</strong></td>
                      <td style="color:{C24_BLUE};font-weight:700">{r['Cars24']:.1f}%</td>
                      <td style="color:{SPINNY_COLOR}">{sp5:.1f}%</td>
                      <td>{r.get('CarWale',0):.1f}%</td><td>{r.get('Cardekho',0):.1f}%</td>
                      <td>{grc(mm5, is_pp=True)}</td>
                      <td style="font-weight:700">{rt5:.0f}%</td>
                    </tr>"""
                st.markdown(f"""<div class="scroll-tbl"><table class="pt"><thead><tr>
                  <th>Month</th><th>C24</th><th>Spinny</th><th>CW</th><th>CD</th><th>MoM</th><th>C24÷Sp</th>
                </tr></thead><tbody>{gmr}</tbody></table></div>""", unsafe_allow_html=True)

            with col_gmc:
                fig_gm = go.Figure()
                for br in ["Cars24","Spinny","CarWale","Cardekho"]:
                    if br in bsos_gm.columns:
                        fig_gm.add_trace(go.Scatter(
                            x=bsos_gm["month"], y=bsos_gm[br], name=br, mode="lines+markers",
                            line=dict(color=BRAND_COLORS.get(br,"#888"),
                                      width=2.5 if br in ("Cars24","Spinny") else 1.5),
                            marker=dict(size=5),
                            hovertemplate=f"<b>{br}</b> %{{x}}: %{{y:.1f}}%<extra></extra>",
                        ))
                # Mark Google peak
                _g_peak_val = bsos_gm.loc[_g_peak_idx, "Cars24"]
                fig_gm.add_trace(go.Scatter(
                    x=[_g_peak_month], y=[_g_peak_val], name="Peak",
                    mode="markers+text", marker=dict(color=C24_MINT, size=10, symbol="star"),
                    text=[f"Peak {_g_peak_val:.1f}%"],
                    textposition="top center", textfont=dict(color=C24_MINT_DK, size=10),
                    hoverinfo="skip",
                ))
                fig_gm.update_layout(**std_layout(320,
                    xaxis=ax(tickangle=-30),
                    yaxis=ax(tickformat=".1f", ticksuffix="%", showgrid=True),
                    legend=dict(orientation="h", y=1.06, x=0, font=dict(size=10)),
                ))
                st.plotly_chart(fig_gm, use_container_width=True)

            if material(gc24m, 0.5):
                st.markdown(ibox(
                    f"Google Brandstack: C24 at <strong>{gc24:.1f}%</strong> "
                    f"({grc(gc24m, is_pp=True)} MoM). "
                    f"C24÷Spinny ratio: <strong>{grat:.0f}%</strong>. "
                    f"Peak C24 in this universe: <strong>{_g_peak_val:.1f}%</strong> ({month_label(_g_peak_month)})."
                ), unsafe_allow_html=True)

        # Daily all-India
        if not bsos_d.empty:
            st.markdown(sec("Daily All-India", f"BSOS daily (May 2025 – {bsos_d['date'].max().strftime('%d %b %Y')})"), unsafe_allow_html=True)
            _gs4 = st.selectbox("View", ["Cars24 & Spinny","All competitors"], key="g4_sel")
            _bg4 = ["Cars24","Spinny"] if _gs4 == "Cars24 & Spinny" else ["Cars24","Spinny","CarWale","Cardekho","MFC"]
            fig_gd = go.Figure()
            for br in _bg4:
                if br in bsos_d.columns:
                    fig_gd.add_trace(go.Scatter(
                        x=bsos_d["date"], y=bsos_d[br], name=br, mode="lines",
                        line=dict(color=BRAND_COLORS.get(br,"#888"),
                                  width=2 if br in ("Cars24","Spinny") else 1),
                        hovertemplate=f"<b>{br}</b> %{{x|%d %b %Y}}: %{{y:.1f}}%<extra></extra>",
                    ))
            fig_gd.update_layout(**std_layout(320,
                xaxis=ax(tickangle=-45, tickfont=dict(size=9, color=C24_BLACK)),
                yaxis=ax(tickformat=".1f", ticksuffix="%", showgrid=True),
                legend=dict(orientation="h", y=1.06, x=0, font=dict(size=10)),
            ))
            st.plotly_chart(fig_gd, use_container_width=True)

        # City-level
        if not bsos_cd.empty:
            st.markdown(sec("City-Level BSOS", "Ahmedabad daily BSOS"), unsafe_allow_html=True)
            _cities_avail = bsos_cd["city"].unique().tolist()
            _city_sel = st.selectbox("City", _cities_avail, key="city4_sel") if len(_cities_avail) > 1 else _cities_avail[0]
            _ahm = bsos_cd[bsos_cd["city"] == _city_sel].copy()
            if not _ahm.empty:
                col_ah1, col_ah2 = st.columns([1, 2])
                _ahm["month"] = _ahm["date"].dt.to_period("M").astype(str)
                _ahm_m = _ahm.groupby("month")[["Cars24","Spinny","CarWale"]].mean().round(2).reset_index()
                _ahm_m["C24_Sp"] = (_ahm_m["Cars24"] / _ahm_m["Spinny"] * 100).round(1)

                with col_ah1:
                    ah_rows = "".join(
                        f"<tr><td><strong>{month_label(r['month'])}</strong></td>"
                        f"<td style='color:{C24_BLUE};font-weight:700'>{r['Cars24']:.1f}%</td>"
                        f"<td style='color:{SPINNY_COLOR}'>{r['Spinny']:.1f}%</td>"
                        f"<td>{r['CarWale']:.1f}%</td>"
                        f"<td style='font-weight:700'>{r['C24_Sp']:.0f}%</td></tr>"
                        for _, r in _ahm_m.sort_values("month", ascending=False).iterrows()
                    )
                    st.markdown(f"""<div class="scroll-tbl"><table class="pt"><thead><tr>
                      <th>Month</th><th>C24</th><th>Spinny</th><th>CW</th><th>C24÷Sp</th>
                    </tr></thead><tbody>{ah_rows}</tbody></table></div>""", unsafe_allow_html=True)

                with col_ah2:
                    fig_ahm = go.Figure()
                    for br in ["Cars24","Spinny","CarWale"]:
                        if br in _ahm.columns:
                            fig_ahm.add_trace(go.Scatter(
                                x=_ahm["date"], y=_ahm[br], name=br, mode="lines",
                                line=dict(color=BRAND_COLORS.get(br,"#888"),
                                          width=2 if br in ("Cars24","Spinny") else 1.5),
                                hovertemplate=f"<b>{br}</b> %{{x|%d %b}}: %{{y:.1f}}%<extra></extra>",
                            ))
                    fig_ahm.update_layout(**std_layout(280,
                        xaxis=ax(tickangle=-45, tickfont=dict(size=9, color=C24_BLACK)),
                        yaxis=ax(tickformat=".1f", ticksuffix="%", showgrid=True),
                        legend=dict(orientation="h", y=1.06, x=0, font=dict(size=11)),
                    ))
                    st.plotly_chart(fig_ahm, use_container_width=True)

    except Exception as e4:
        import traceback; st.error(f"Google BSOS error: {e4}"); st.code(traceback.format_exc())


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — GSC × INDEXED CROSSCHECK
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    try:
        # Merge GSC monthly totals with Google Brandstack monthly averages
        if not totals_df.empty and not bsos_gm.empty:
            _gsc5 = totals_df.copy()
            _gsc5["imp_lakh"] = _gsc5["total_impressions"] / 1e5

            # Use Google Brandstack Cars24 SoS % as the "indexed" measure
            # (Tab 5 spec: ignore rounded, use Index only — bsos_google_monthly = Google indexed SoS)
            _m5 = _gsc5.merge(
                bsos_gm[["month","Cars24"]].rename(columns={"Cars24": "g_idx"}),
                on="month", how="inner"
            ).dropna(subset=["g_idx"]).sort_values("month").reset_index(drop=True)

            # ── Pearson correlation ──────────────────────────────────────────
            _x = _m5["imp_lakh"].values; _y = _m5["g_idx"].values
            if len(_x) >= 3:
                _xm = _x - _x.mean(); _ym = _y - _y.mean()
                _denom = np.sqrt((_xm**2).sum() * (_ym**2).sum())
                _r = (_xm * _ym).sum() / _denom if _denom > 0 else float("nan")
            else:
                _r = float("nan")

            # Direction match count
            _x_diff = np.diff(_x); _y_diff = np.diff(_y)
            _dir_match = int((np.sign(_x_diff) == np.sign(_y_diff)).sum())
            _dir_total = len(_x_diff)

            # Peak alignment
            _peak_gsc_m = _m5.loc[_m5["imp_lakh"].idxmax(), "month"]
            _peak_idx_m = _m5.loc[_m5["g_idx"].idxmax(), "month"]
            _peaks_aligned = _peak_gsc_m == _peak_idx_m

            # Verdict insight
            _r_str = f"r={_r:.2f}" if not np.isnan(_r) else "r=—"
            _dir_str = f"{_dir_match}/{_dir_total} direction matches"
            if _peaks_aligned:
                _peak_str = f"Both peak in {month_label(_peak_gsc_m)}."
            else:
                _peak_str = (f"GSC peaks {month_label(_peak_gsc_m)}, "
                             f"Google peaks {month_label(_peak_idx_m)} — divergent peaks, likely different keyword sets.")
            _verdict = (f"Correlation: <strong>{_r_str}</strong> · {_dir_str} · {_peak_str} "
                        f"These are <strong>complementary signals</strong> — GSC measures actual clicks, "
                        f"Google Brandstack uses a different (used-car focused) keyword universe.")

            st.markdown(sec("GSC × Google Indexed", "Overlap window crosscheck — use Index only, ignore Rounded"), unsafe_allow_html=True)

            # Metric cards
            m1, m2, m3 = st.columns(3)
            m1.markdown(f"""<div class="kpi-card">
              <div class="kpi-lbl">Pearson Correlation (r)</div>
              <div class="kpi-val" style="font-size:36px;color:{C24_BLUE if not np.isnan(_r) and _r > 0.7 else C24_TEXTGREY}">{_r:.2f}</div>
              <div class="kpi-sub">Over {len(_m5)}-month overlap window</div>
            </div>""", unsafe_allow_html=True)
            m2.markdown(f"""<div class="kpi-card">
              <div class="kpi-lbl">Direction Matches</div>
              <div class="kpi-val" style="font-size:36px">{_dir_match}/{_dir_total}</div>
              <div class="kpi-sub">{_dir_match/_dir_total*100:.0f}% of MoM moves in same direction</div>
            </div>""", unsafe_allow_html=True)
            m3.markdown(f"""<div class="kpi-card">
              <div class="kpi-lbl">Peak Alignment</div>
              <div class="kpi-val" style="font-size:20px;color:{''+C24_GREEN if _peaks_aligned else C24_ORANGE+''}">{
                'Aligned' if _peaks_aligned else 'Diverged'}</div>
              <div class="kpi-sub">GSC: {month_label(_peak_gsc_m)} · Google: {month_label(_peak_idx_m)}</div>
            </div>""", unsafe_allow_html=True)

            st.markdown(ibox(_verdict, "📊"), unsafe_allow_html=True)

            # ── Dual-axis chart ──────────────────────────────────────────────
            st.markdown(sec("Dual-Axis Overlay", "GSC impressions (bars) vs Google Brandstack SoS % (line)"), unsafe_allow_html=True)

            fig_x = go.Figure()
            fig_x.add_trace(go.Bar(
                x=_m5["month"], y=_m5["imp_lakh"], name="GSC Impressions (L)", yaxis="y",
                marker_color="#B8B5FF", opacity=0.8,
                hovertemplate="<b>%{x}</b><br>GSC: %{y:.2f}L<extra></extra>",
            ))
            fig_x.add_trace(go.Scatter(
                x=_m5["month"], y=_m5["g_idx"], name="Google Brandstack SoS %", yaxis="y2",
                mode="lines+markers", line=dict(color=C24_BLUE, width=2.5), marker=dict(size=5),
                hovertemplate="<b>%{x}</b><br>Google SoS: %{y:.1f}%<extra></extra>",
            ))
            # Mark peaks
            _gsc_pk_v = _m5.loc[_m5["imp_lakh"].idxmax(), "imp_lakh"]
            _gsc_pk_m = _m5.loc[_m5["imp_lakh"].idxmax(), "month"]
            fig_x.add_trace(go.Scatter(
                x=[_gsc_pk_m], y=[_gsc_pk_v], yaxis="y", name="GSC peak",
                mode="markers", marker=dict(color=C24_MINT, size=10, symbol="star"),
                hoverinfo="skip",
            ))
            fig_x.update_layout(**std_layout(400,
                xaxis=ax(tickangle=-45, tickfont=dict(size=9, color=C24_BLACK)),
                yaxis=dict(**ax(), title="GSC Impressions (L)", tickformat=".1f", ticksuffix="L",
                           showgrid=True, side="left"),
                yaxis2=dict(**ax(), title="Google SoS %", tickformat=".1f", ticksuffix="%",
                            overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", y=1.06, x=0, font=dict(size=11)),
                barmode="group",
            ))
            st.plotly_chart(fig_x, use_container_width=True)

            # ── Side-by-side table ───────────────────────────────────────────
            st.markdown(sec("Month-by-Month Detail", "GSC impressions vs Google SoS — side by side"), unsafe_allow_html=True)

            _m5d = _m5.sort_values("month", ascending=False).reset_index(drop=True)
            x_rows = ""
            for i, (_, r) in enumerate(_m5d.iterrows()):
                pr6 = _m5d.iloc[i+1] if i+1 < len(_m5d) else None
                mi6 = pct_ch(r["imp_lakh"], pr6["imp_lakh"]) if pr6 is not None else float("nan")
                ms6 = pp_ch(r["g_idx"], pr6["g_idx"]) if pr6 is not None else float("nan")
                if not np.isnan(mi6) and not np.isnan(ms6):
                    sig = ("Both up" if mi6>0 and ms6>0
                           else "Impr up / SoS flat" if mi6>0 and ms6<=0
                           else "Share gain" if mi6<=0 and ms6>0
                           else "Both down")
                    sig_color = (C24_GREEN if sig=="Both up" else
                                 C24_TEXTGREY if sig=="Impr up / SoS flat" else
                                 C24_BLUE if sig=="Share gain" else C24_RED_FB)
                else:
                    sig, sig_color = "—", C24_TEXTGREY
                x_rows += f"""<tr>
                  <td><strong>{month_label(r['month'])}</strong></td>
                  <td style="font-weight:700">{r['imp_lakh']:.2f}L</td>
                  <td>{grc(mi6)}</td>
                  <td style="color:{C24_BLUE};font-weight:700">{r['g_idx']:.1f}%</td>
                  <td>{grc(ms6, is_pp=True)}</td>
                  <td style="font-size:11px;color:{sig_color};font-weight:600">{sig}</td>
                </tr>"""

            st.markdown(f"""<div class="scroll-tbl"><table class="pt"><thead><tr>
              <th>Month</th><th>GSC Imp</th><th>GSC MoM</th><th>Google SoS</th><th>SoS MoM</th><th>Signal</th>
            </tr></thead><tbody>{x_rows}</tbody></table></div>""", unsafe_allow_html=True)

        else:
            st.info("GSC or Google Brandstack data not available for crosscheck.")

    except Exception as e5:
        import traceback; st.error(f"Crosscheck error: {e5}"); st.code(traceback.format_exc())


# ═══════════════════════════════════════════════════════════════════════════════
# AUSTRALIA TAB
# ═══════════════════════════════════════════════════════════════════════════════
with _ctry_au:
    _au_tab_imp, _au_tab_bsos, _au_tab_city = st.tabs([
        "📊  Search Impressions", "🆚  Share of Searches", "🏙  City Level"
    ])
    _placeholder_style = "background:#F5F4FF;border-radius:12px;padding:32px 28px;text-align:center;color:#6B7280;border:2px dashed #C7C4FF;margin:12px 0"
    _placeholder_icon  = '<div style="font-size:40px;margin-bottom:12px">📂</div>'
    _placeholder_title = lambda t: f'<div style="font-size:18px;font-weight:700;color:#374151;margin-bottom:8px">{t}</div>'
    _placeholder_body  = lambda b: f'<div style="font-size:13px;line-height:1.7">{b}</div>'

    with _au_tab_imp:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("Australia · Search Impressions")}'
            f'{_placeholder_body("Share AU GSC data (Google Search Console export) to populate this section.<br>Metrics: monthly impressions, MoM growth, category breakdown, top keywords.")}'
            '</div>', unsafe_allow_html=True)

    with _au_tab_bsos:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("Australia · Share of Searches (BSOS)")}'
            f'{_placeholder_body("Share AU Brandstack BSOS data — monthly &amp; weekly — to populate.<br>Metrics: Cars24 SoS%, vs Carsales, vs Drive, MoM trend.")}'
            '</div>', unsafe_allow_html=True)

    with _au_tab_city:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("Australia · City Level")}'
            f'{_placeholder_body("Share AU city-level BSOS data (Sydney, Melbourne, Brisbane, etc.) to populate.")}'
            '</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# UAE TAB
# ═══════════════════════════════════════════════════════════════════════════════
with _ctry_uae:
    _uae_tab_imp, _uae_tab_bsos, _uae_tab_city = st.tabs([
        "📊  Search Impressions", "🆚  Share of Searches", "🏙  City Level"
    ])

    with _uae_tab_imp:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("UAE · Search Impressions")}'
            f'{_placeholder_body("Share UAE GSC data to populate.<br>Metrics: monthly impressions, MoM growth, category breakdown.")}'
            '</div>', unsafe_allow_html=True)

    with _uae_tab_bsos:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("UAE · Share of Searches (BSOS)")}'
            f'{_placeholder_body("Share UAE Brandstack BSOS data to populate.<br>Metrics: Cars24 SoS%, vs Dubizzle, vs Dubicars, MoM trend.")}'
            '</div>', unsafe_allow_html=True)

    with _uae_tab_city:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("UAE · City Level")}'
            f'{_placeholder_body("Share UAE city-level BSOS data (Dubai, Abu Dhabi, Sharjah, etc.) to populate.")}'
            '</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# YOUTUBE TAB  (country sub-tabs → channel sub-tabs within each)
# ═══════════════════════════════════════════════════════════════════════════════
with _ctry_yt:
    _yt_in, _yt_au, _yt_uae = st.tabs(["🇮🇳  India", "🇦🇺  Australia", "🇦🇪  UAE"])

    _yt_metrics = "Subscribers (MoM growth), Monthly Views, Watch Time, Avg Views/Video, Engagement Rate (Likes+Comments÷Views)"

    def _yt_placeholder(channel, metrics):
        return (f'<div style="{_placeholder_style}">{_placeholder_icon}'
                f'{_placeholder_title(f"YouTube · {channel}")}'
                f'{_placeholder_body(f"Share {channel} YouTube analytics export to populate.<br><strong>Metrics needed:</strong> {metrics}")}'
                '</div>')

    _yt_data_note = f'''<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-top:8px;border:1px solid #E3E1FF">
      <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:8px">📋 What data to share</div>
      <ul style="font-size:12px;color:#6B7280;line-height:2;margin:0;padding-left:18px">
        <li>YouTube Studio → Analytics → Export CSV (monthly)</li>
        <li>Columns needed: Month, Subscribers, Views, Watch time, Avg view duration, Impressions, CTR, Likes, Comments</li>
        <li>Date range: Jan 2024 onwards preferred</li>
      </ul>
    </div>'''

    with _yt_in:
        _yt_in_c24, _yt_in_insider, _yt_in_tbhp = st.tabs([
            "🎬  Cars24", "🎙  Cars24 Insider", "🏎  TeamBHP"
        ])
        with _yt_in_c24:
            st.markdown(_yt_placeholder("Cars24 India", _yt_metrics), unsafe_allow_html=True)
            st.markdown(_yt_data_note, unsafe_allow_html=True)
        with _yt_in_insider:
            st.markdown(_yt_placeholder("Cars24 Insider", _yt_metrics), unsafe_allow_html=True)
            st.markdown(_yt_data_note, unsafe_allow_html=True)
        with _yt_in_tbhp:
            st.markdown(_yt_placeholder("TeamBHP", _yt_metrics), unsafe_allow_html=True)
            st.markdown(_yt_data_note, unsafe_allow_html=True)

    with _yt_au:
        st.markdown(_yt_placeholder("Cars24 Australia", _yt_metrics), unsafe_allow_html=True)
        st.markdown(_yt_data_note, unsafe_allow_html=True)

    with _yt_uae:
        st.markdown(_yt_placeholder("Cars24 UAE", _yt_metrics), unsafe_allow_html=True)
        st.markdown(_yt_data_note, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# INSTAGRAM TAB  (country sub-tabs → account sub-tabs within each)
# ═══════════════════════════════════════════════════════════════════════════════
with _ctry_ig:
    _ig_in, _ig_au, _ig_uae = st.tabs(["🇮🇳  India", "🇦🇺  Australia", "🇦🇪  UAE"])

    _ig_metrics = "Followers (MoM growth), Monthly Reach, Impressions, Posts Count, Avg Engagement Rate, Story Views"

    def _ig_placeholder(account, metrics):
        return (f'<div style="{_placeholder_style}">{_placeholder_icon}'
                f'{_placeholder_title(f"Instagram · {account}")}'
                f'{_placeholder_body(f"Share {account} Instagram analytics export to populate.<br><strong>Metrics needed:</strong> {metrics}")}'
                '</div>')

    _ig_data_note = f'''<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-top:8px;border:1px solid #E3E1FF">
      <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:8px">📋 What data to share</div>
      <ul style="font-size:12px;color:#6B7280;line-height:2;margin:0;padding-left:18px">
        <li>Instagram Insights → Export (or Meta Business Suite)</li>
        <li>Columns: Month, Followers, Reach, Impressions, Posts, Likes, Comments, Saves, Story Views</li>
        <li>Date range: Jan 2024 onwards preferred</li>
      </ul>
    </div>'''

    with _ig_in:
        _ig_in_c24, _ig_in_tbhp = st.tabs(["📷  Cars24", "📷  TeamBHP"])
        with _ig_in_c24:
            st.markdown(_ig_placeholder("Cars24 India", _ig_metrics), unsafe_allow_html=True)
            st.markdown(_ig_data_note, unsafe_allow_html=True)
        with _ig_in_tbhp:
            st.markdown(_ig_placeholder("TeamBHP", _ig_metrics), unsafe_allow_html=True)
            st.markdown(_ig_data_note, unsafe_allow_html=True)

    with _ig_au:
        st.markdown(_ig_placeholder("Cars24 Australia", _ig_metrics), unsafe_allow_html=True)
        st.markdown(_ig_data_note, unsafe_allow_html=True)

    with _ig_uae:
        st.markdown(_ig_placeholder("Cars24 UAE", _ig_metrics), unsafe_allow_html=True)
        st.markdown(_ig_data_note, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# INFLUENCERS TAB
# ═══════════════════════════════════════════════════════════════════════════════
with _ctry_inf:
    _inf_tab_overview, _inf_tab_yt, _inf_tab_ig = st.tabs([
        "📊  Overview", "▶  YouTube Collabs", "📸  Instagram Collabs"
    ])

    with _inf_tab_overview:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("Influencer Campaign Tracker")}'
            f'{_placeholder_body("Share influencer campaign data to populate.<br><strong>Metrics needed:</strong> Influencer name, Platform, Video/Post URL, Views/Reach, Likes, Comments, CPV (Cost Per View), Budget, Campaign month, Category (Auto / Lifestyle / Finance etc.)")}'
            '</div>', unsafe_allow_html=True)
        st.markdown(f'''<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-top:8px;border:1px solid #E3E1FF">
          <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:8px">📋 Columns to include in your data sheet</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 24px;font-size:12px;color:#6B7280;line-height:2">
            <div>• Month</div><div>• Influencer Name</div>
            <div>• Platform (YouTube / Instagram / Twitter)</div><div>• Content Type (Dedicated / Integration / Story)</div>
            <div>• Views / Reach</div><div>• Likes</div>
            <div>• Comments</div><div>• Shares / Saves</div>
            <div>• Budget (₹)</div><div>• CPV (Cost Per View)</div>
            <div>• Category</div><div>• Video/Post link</div>
          </div>
        </div>''', unsafe_allow_html=True)

    with _inf_tab_yt:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("YouTube Influencer Campaigns")}'
            f'{_placeholder_body("Share YouTube influencer data to populate.<br>Views, CPV, Watch Time, Engagement by influencer and campaign month.")}'
            '</div>', unsafe_allow_html=True)

    with _inf_tab_ig:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("Instagram Influencer Campaigns")}'
            f'{_placeholder_body("Share Instagram influencer data to populate.<br>Reach, CPR (Cost Per Reach), Saves, Story Views by influencer and campaign month.")}'
            '</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN TAB
# ═══════════════════════════════════════════════════════════════════════════════
with _ctry_li:
    _li_tabs = st.tabs([
        "🏢  Cars24 India", "🏢  Cars24 Australia", "🏢  Cars24 UAE",
        "🎓  Cars24 Careers", "📦  Combined View"
    ])
    _li_c24_in, _li_c24_au, _li_c24_uae, _li_careers, _li_combined = _li_tabs

    _li_metrics = "Followers (MoM growth), Impressions, Unique Visitors, Post Engagements, Engagement Rate, Top Posts"

    def _li_placeholder(page):
        return (f'<div style="{_placeholder_style}">{_placeholder_icon}'
                f'{_placeholder_title(f"LinkedIn · {page}")}'
                f'{_placeholder_body(f"Share {page} LinkedIn Page analytics to populate.<br><strong>Metrics needed:</strong> {_li_metrics}")}'
                '</div>')

    with _li_c24_in:
        st.markdown(_li_placeholder("Cars24 India"), unsafe_allow_html=True)
        st.markdown(f'''<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-top:8px;border:1px solid #E3E1FF">
          <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:8px">📋 What data to share</div>
          <ul style="font-size:12px;color:#6B7280;line-height:2;margin:0;padding-left:18px">
            <li>LinkedIn Page Admin → Analytics → Followers → Export</li>
            <li>LinkedIn Page Admin → Analytics → Content → Export</li>
            <li>Columns: Month, Followers, New Followers, Impressions, Unique Visitors, Engagement Rate</li>
            <li>Date range: Jan 2024 onwards preferred</li>
          </ul>
        </div>''', unsafe_allow_html=True)

    with _li_c24_au:
        st.markdown(_li_placeholder("Cars24 Australia"), unsafe_allow_html=True)

    with _li_c24_uae:
        st.markdown(_li_placeholder("Cars24 UAE"), unsafe_allow_html=True)

    with _li_careers:
        st.markdown(_li_placeholder("Cars24 Careers"), unsafe_allow_html=True)

    with _li_combined:
        st.markdown(f'<div style="{_placeholder_style}">{_placeholder_icon}'
            f'{_placeholder_title("LinkedIn · All Pages Combined")}'
            f'{_placeholder_body("Once data is shared for individual pages above, this view will show a combined dashboard — total followers across all Cars24 LinkedIn pages, best performing content, and cross-page growth trends.")}'
            '</div>', unsafe_allow_html=True)
