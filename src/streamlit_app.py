#!/usr/bin/env python3
"""
streamlit_app.py
================
OSNR Figure Skating Judge Bias Analysis — Streamlit Web App

Run with:
    streamlit run streamlit_app.py
  or:
    bash run_app.sh

4 pages:
  1. Competitions  — browse all 17 competitions
  2. Event Analysis — 7-tab deep dive for any event
  3. Judge Profiles — cross-event named-judge statistics
  4. System-Wide Stats — distribution of bias z-scores
"""

import os
import sys
import sqlite3
import subprocess
import tempfile

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Path configuration ──────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "figure_skating_ijs_seed.sqlite")

# Import load_event_data from generate_event_report.py
# Safe: parse_args() only called inside main(), guarded by __name__ == '__main__'
sys.path.insert(0, BASE_DIR)
from generate_event_report import load_event_data  # noqa: E402

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="OSNR — Figure Skating Judge Bias",
    page_icon="⛸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Color scheme (matching the Excel workbook) ──────────────────────────────
C_DARK_BLUE  = "#2F4F7F"
C_GREEN      = "#C6EFCE"   # R1 / improved / no flag
C_YELLOW     = "#FFEB9C"   # R0 / Tier 1
C_SALMON     = "#FCE4D6"   # R2 / dropped
C_BLUE_HDR   = "#BDD7EE"   # column headers
C_ORANGE     = "#F4B942"   # Tier 2 OSNR flag
C_RED_TEXT   = "#CC0000"
C_GREEN_TEXT = "#006400"

GOE_COLORS = {
    -5: "#FF0000", -4: "#FF4444", -3: "#FF8888", -2: "#FFBBBB", -1: "#FFDDDD",
     0: "#FFFFFF",
     1: "#DDFFDD",  2: "#BBFFBB",  3: "#88FF88",  4: "#44FF44",  5: "#00CC00",
}

# ── CSS tweaks ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.4rem; }
div[data-testid="stExpander"] > div { padding: 0.5rem 0.75rem; }
</style>
""", unsafe_allow_html=True)


def _scroll(direction):
    """Scroll the main Streamlit content area up or down.

    st.components.v1.html runs in a same-origin iframe, so it can directly
    access window.parent.document — no postMessage dance needed.
    """
    if direction == "top":
        js = "window.parent.document.querySelector('section.stMain').scrollTo({top:0,behavior:'instant'});"
    else:
        js = ("var s=window.parent.document.querySelector('section.stMain');"
              "s.scrollTo({top:s.scrollHeight,behavior:'smooth'});")
    st.components.v1.html(f"<script>{js}</script>", height=0)


# ════════════════════════════════════════════════════════════════════════════
# Cached database query functions
# ════════════════════════════════════════════════════════════════════════════

@st.cache_data
def db_get_system_summary():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM competitions")
    n_comps = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM events")
    n_events = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM entries")
    n_entries = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT judge_id) FROM judges")
    n_judges = cur.fetchone()[0]
    cur.execute("SELECT (SELECT COUNT(*) FROM element_judge_scores) + (SELECT COUNT(*) FROM pcs_judge_scores)")
    n_marks = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pairwise_judge_statistics WHERE is_significant_01=1")
    n_sig01 = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pairwise_judge_statistics WHERE is_significant_001=1")
    n_sig001 = cur.fetchone()[0]
    cur.execute("""SELECT COUNT(DISTINCT event_id) FROM lojo_event_summary
                   WHERE winner_changes > 0""")
    n_wc = cur.fetchone()[0]
    cur.execute("""SELECT COUNT(DISTINCT event_id) FROM lojo_event_summary
                   WHERE podium_changes > 0""")
    n_pc = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(DISTINCT pjs.event_id)
        FROM pairwise_judge_statistics pjs
        JOIN lojo_event_summary les
          ON pjs.event_id = les.event_id
         AND pjs.judge_position = les.judge_position
        WHERE pjs.is_significant_001 = 1
          AND les.podium_changes > 0
    """)
    n_tier2 = cur.fetchone()[0]
    conn.close()
    return dict(n_comps=n_comps, n_events=n_events, n_entries=n_entries,
                n_judges=n_judges, n_marks=n_marks, n_sig01=n_sig01, n_sig001=n_sig001,
                n_winner_changes=n_wc, n_podium_changes=n_pc, n_tier2_events=n_tier2)


@st.cache_data
def db_get_competitions():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.competition_id, c.name, c.location, c.season,
               c.start_date, COUNT(e.event_id) as n_events
        FROM competitions c
        LEFT JOIN events e ON c.competition_id = e.competition_id
        GROUP BY c.competition_id
        ORDER BY c.start_date DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [{"competition_id": r[0], "name": r[1], "location": r[2] or "",
             "season": r[3] or "", "start_date": r[4] or "", "n_events": r[5]}
            for r in rows]


@st.cache_data
def db_get_events(competition_id=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if competition_id:
        cur.execute("""
            SELECT e.event_id, e.discipline, e.segment, c.name,
                   COUNT(en.entry_id) as n_entries
            FROM events e
            JOIN competitions c ON e.competition_id = c.competition_id
            LEFT JOIN entries en ON e.event_id = en.event_id
            WHERE e.competition_id = ?
            GROUP BY e.event_id ORDER BY e.event_id
        """, (competition_id,))
    else:
        cur.execute("""
            SELECT e.event_id, e.discipline, e.segment, c.name,
                   COUNT(en.entry_id) as n_entries
            FROM events e
            JOIN competitions c ON e.competition_id = c.competition_id
            LEFT JOIN entries en ON e.event_id = en.event_id
            GROUP BY e.event_id ORDER BY c.start_date DESC, e.event_id
        """)
    rows = cur.fetchall()
    conn.close()
    return [{"event_id": r[0], "discipline": r[1], "segment": r[2],
             "competition_name": r[3], "n_entries": r[4]}
            for r in rows]


@st.cache_data
def db_load_event(event_id):
    """Wrapper around generate_event_report.load_event_data() with caching."""
    conn = sqlite3.connect(DB_PATH)
    try:
        data = load_event_data(conn, event_id)
    finally:
        conn.close()
    return data


@st.cache_data
def db_get_all_judge_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT jes.judge_name, jes.judge_country,
               COUNT(DISTINCT jes.event_id)           AS n_events,
               ROUND(AVG(jes.bias_z_score),4)          AS avg_z,
               ROUND(MAX(ABS(jes.bias_z_score)),4)      AS max_abs_z,
               ROUND(AVG(jes.mean_goe_deviation),4)     AS avg_goe_dev,
               SUM(jes.outlier_count)                  AS total_outliers,
               ROUND(AVG(jes.correlation_with_panel),4) AS avg_corr,
               ROUND(AVG(jes.home_country_differential),4) AS avg_home_diff
        FROM judge_event_statistics jes
        WHERE jes.num_elements_judged > 0
          AND jes.judge_name IS NOT NULL
          AND jes.judge_name NOT LIKE 'Judge %'
          AND jes.judge_name NOT LIKE 'J%'
        GROUP BY jes.judge_name, jes.judge_country
        HAVING n_events >= 1
        ORDER BY n_events DESC, max_abs_z DESC
    """)
    rows = cur.fetchall()
    conn.close()
    cols = ["Judge Name", "Country", "Events", "Avg Z",
            "Max |Z|", "Avg GOE Dev", "Total Outliers", "Panel Corr.", "Home Diff"]
    return pd.DataFrame(rows, columns=cols)


@st.cache_data
def db_get_zscore_distribution():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT jes.bias_z_score, jes.judge_name, jes.judge_country,
               ev.discipline, ev.segment, c.name, c.season,
               jes.mean_goe_deviation, jes.outlier_count,
               jes.correlation_with_panel
        FROM judge_event_statistics jes
        JOIN events ev ON jes.event_id = ev.event_id
        JOIN competitions c ON ev.competition_id = c.competition_id
        WHERE jes.num_elements_judged > 0
          AND jes.bias_z_score IS NOT NULL
    """)
    rows = cur.fetchall()
    conn.close()
    cols = ["bias_z", "judge_name", "judge_country", "discipline", "segment",
            "competition", "season", "mean_goe_dev", "outlier_count", "corr"]
    return pd.DataFrame(rows, columns=cols)


# ════════════════════════════════════════════════════════════════════════════
# Excel generation helper
# ════════════════════════════════════════════════════════════════════════════

def generate_excel_bytes(event_id) -> bytes | None:
    """Run generate_event_report.py as a subprocess; return .xlsx bytes."""
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp_path = tmp.name
    tmp.close()
    script = os.path.join(BASE_DIR, "generate_event_report.py")
    try:
        result = subprocess.run(
            [sys.executable, script, "--event-id", str(event_id), "--output", tmp_path],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            st.error(f"Excel generation failed:\n```\n{result.stderr}\n```")
            return None
        with open(tmp_path, "rb") as f:
            return f.read()
    except subprocess.TimeoutExpired:
        st.error("Excel generation timed out (>120 s).")
        return None
    except Exception as ex:
        st.error(f"Unexpected error: {ex}")
        return None
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ════════════════════════════════════════════════════════════════════════════
# Sidebar + navigation
# ════════════════════════════════════════════════════════════════════════════

_PAGE_KEYS = {
    "🏆  Competitions":    "competitions",
    "📊  Event Analysis":  "event",
    "👨‍⚖️  Judge Profiles": "judges",
    "📈  System-Wide Stats": "stats",
    "📖  Glossary":        "glossary",
}
_KEY_TO_PAGE = {v: k for k, v in _PAGE_KEYS.items()}


def _set_page(page_label: str):
    """Write the page key to query_params so the browser records a history entry."""
    st.query_params["page"] = _PAGE_KEYS.get(page_label, "competitions")


def render_sidebar():
    st.sidebar.title("⛸ OSNR Analysis")
    st.sidebar.caption("Figure Skating Judge Bias System")
    st.sidebar.divider()

    pages = ["🏆  Competitions", "📊  Event Analysis",
             "👨‍⚖️  Judge Profiles", "📈  System-Wide Stats",
             "📖  Glossary"]

    # Determine active page: prefer goto_page (from Analyze buttons), then
    # query_params (from back/forward), then radio widget.
    if "goto_page" in st.session_state:
        active = st.session_state["goto_page"]   # consumed in main()
    else:
        qp_key = st.query_params.get("page", "competitions")
        active = _KEY_TO_PAGE.get(qp_key, pages[0])

    active_idx = pages.index(active) if active in pages else 0
    page = st.sidebar.radio("Navigate", pages,
                            index=active_idx,
                            label_visibility="collapsed")

    # When the user manually clicks the radio, update query_params
    if page != active and "goto_page" not in st.session_state:
        _set_page(page)

    st.sidebar.divider()
    st.sidebar.subheader("Quick Jump")
    all_events = db_get_events()

    # Abbreviate competition names so discipline/segment are always visible
    _COMP_ABBREV = {
        "Olympic Winter Games": "OWG",
        "ISU World Figure Skating Championships": "Worlds",
        "ISU Grand Prix of Figure Skating Final": "GPF",
        "ISU Four Continents Figure Skating Championships": "4CC",
        "ISU European Figure Skating Championships": "Euros",
    }

    def _abbrev_comp(name):
        for full, short in _COMP_ABBREV.items():
            if full in name:
                # Extract year from name, e.g. "2026" or "2024/25"
                import re
                m = re.search(r'\b(20\d\d)\b', name)
                yr = m.group(1) if m else ""
                return f"{short} {yr}".strip()
        return name[:18]

    # Discipline labels (readable, not abbreviated)
    _DISC = {"Ice Dance": "Ice Dance", "Men Single Skating": "Men's",
             "Women Single Skating": "Ladies'", "Pair Skating": "Pairs"}
    _SEG  = {"Rhythm Dance": "Rhythm Dance", "Free Dance": "Free Dance",
             "Short Program": "Short Program", "Free Skating": "Free Skating"}

    opts = {
        f"{_abbrev_comp(e['competition_name'])} — "
        f"{_DISC.get(e['discipline'], e['discipline'])} "
        f"{_SEG.get(e['segment'], e['segment'])}":
        e["event_id"]
        for e in all_events
    }
    sel_label = st.sidebar.selectbox("Select event", list(opts.keys()),
                                     key="sidebar_quick_event")
    if st.sidebar.button("Analyze →", type="primary"):
        st.session_state["goto_event_id"] = opts[sel_label]
        st.session_state["goto_page"] = "📊  Event Analysis"
        st.session_state["scroll_to_top"] = True
        st.rerun()

    # Back button — shown when user arrived at Event Analysis from Competitions
    if st.session_state.get("came_from_competitions"):
        st.sidebar.divider()
        if st.sidebar.button("← Back to Competitions", use_container_width=True):
            st.session_state.pop("came_from_competitions", None)
            st.session_state["goto_page"] = "🏆  Competitions"
            st.rerun()

    return page


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1: Competitions
# ════════════════════════════════════════════════════════════════════════════

def page_competitions():
    st.title("Competitions")
    st.caption("All competitions in the Outlier Score Normalization and Removal (OSNR) database")

    s = db_get_system_summary()
    # Row 1: dataset scope
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    r1c1.metric("Competitions", s["n_comps"])
    r1c2.metric("Events", s["n_events"])
    r1c3.metric("Entries", f"{s['n_entries']:,}")
    r1c4.metric("Unique Judges", f"{s['n_judges']:,}")
    r1c5.metric("Judge Marks", f"{s['n_marks']:,}")
    # Row 2: OSNR findings
    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
    r2c1.metric("Sig. Pairs (p≤0.01)",    f"{s['n_sig01']:,}")
    r2c2.metric("Sig. Pairs (p≤0.001)",   f"{s['n_sig001']:,}")
    r2c3.metric("Events w/ Winner Changes", s["n_winner_changes"])
    r2c4.metric("Events w/ Podium Changes", s["n_podium_changes"])
    r2c5.metric("Events w/ Tier 2 Flag",    s["n_tier2_events"])

    st.divider()
    comps = db_get_competitions()

    browse_comp_id = st.session_state.get("browse_comp_id")

    for i in range(0, len(comps), 2):
        cols = st.columns(2)
        for j, comp in enumerate(comps[i:i + 2]):
            with cols[j]:
                is_selected = (browse_comp_id == comp["competition_id"])
                with st.container(border=True):
                    st.subheader(comp["name"])
                    loc = comp["location"] or "—"
                    seas = comp["season"] or "—"
                    st.caption(f"📍 {loc}  |  Season: {seas}")
                    col_a, col_b = st.columns([1, 2])
                    col_a.metric("Events", comp["n_events"])
                    btn_label = "▼ Hide Events" if is_selected else "Browse Events →"
                    btn_key = f"browse_btn_{i}_{j}"
                    if col_b.button(
                        btn_label,
                        key=btn_key,
                        type="primary" if is_selected else "secondary",
                    ):
                        cid = comp["competition_id"]
                        if browse_comp_id == cid:
                            st.session_state.pop("browse_comp_id", None)
                        else:
                            st.session_state["browse_comp_id"] = cid
                        st.rerun()

                    # Show events inline inside the card when selected
                    if is_selected:
                        events = db_get_events(comp["competition_id"])
                        st.divider()
                        for ev in events:
                            ea, eb, ec = st.columns([3, 1, 1])
                            ea.write(f"**{ev['discipline']} — {ev['segment']}**")
                            eb.write(f"{ev['n_entries']} entries")
                            if ec.button("Analyze →", key=f"ev_{ev['event_id']}"):
                                st.session_state["goto_event_id"] = ev["event_id"]
                                st.session_state["goto_page"] = "📊  Event Analysis"
                                st.session_state["scroll_to_top"] = True
                                st.session_state["came_from_competitions"] = True
                                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2: Event Analysis — tab renderers
# ════════════════════════════════════════════════════════════════════════════

def _osnr_status(pairwise_agg, lojo_sum, jpos):
    pa = pairwise_agg.get(jpos, {})
    ls = lojo_sum.get(jpos, {})
    pc = ls.get("podium_changes", 0) or 0
    s01  = pa.get("sig01", 0) or 0
    s001 = pa.get("sig001", 0) or 0
    if s001 > 0 and pc > 0:
        return "Tier 2"
    if s01 > 0:
        return "Tier 1"
    return "No flag"


def render_tab_summary(data):
    ev        = data["event_info"]
    judges    = data["judges"]
    jpos_list = data["judge_positions"]
    entries   = data["entries"]
    lojo_sum  = data["lojo_summary"]
    pairwise_agg = data["pairwise_agg"]

    flagged_pos  = ev.get("flagged_judge_pos")
    flagged_name = judges.get(flagged_pos, {}).get("name", "none") if flagged_pos else "none"
    flagged_cc   = judges.get(flagged_pos, {}).get("country", "") if flagged_pos else ""

    col_l, col_r = st.columns([1.3, 1])

    # ── Left: standings ──────────────────────────────────────────────────────
    with col_l:
        st.subheader("Official Standings & Regime Comparison")
        rows = []
        for e in entries:
            d0 = e["rank_r0"] - e["rank"]
            d2 = e["rank_r2"] - e["rank"]
            rows.append({
                "Rank":    e["rank"],
                "Team":    e["team_name"],
                "NOC":     e["noc"],
                "R1 TSS":  e["tss_r1"],
                "R0 TSS":  e["tss_r0"],
                "R0 Δ":    ("—" if d0 == 0 else f"+{abs(d0)}" if d0 < 0 else f"−{d0}"),
                "R2 TSS":  e["tss_r2"],
                "R2 Δ":    ("—" if d2 == 0 else f"+{abs(d2)}" if d2 < 0 else f"−{d2}"),
            })
        df = pd.DataFrame(rows)

        def _hl_rank(row):
            c = {1: f"background-color:{C_YELLOW}",
                 2: "background-color:#F2F2F2",
                 3: f"background-color:{C_SALMON}"}
            return [c.get(row["Rank"], "")] * len(row)

        st.dataframe(df.style.apply(_hl_rank, axis=1),
                     use_container_width=True, hide_index=True)
        if flagged_pos:
            st.info(f"R2 = OSNR-adjusted: **{flagged_pos}** ({flagged_name}, {flagged_cc}) removed")

    # ── Right: panel + LOJO ──────────────────────────────────────────────────
    with col_r:
        st.subheader("Judge Panel — OSNR Status")
        panel_rows = []
        for jpos in jpos_list:
            j = judges.get(jpos, {})
            pa = pairwise_agg.get(jpos, {})
            ls = lojo_sum.get(jpos, {})
            s01  = pa.get("sig01", 0) or 0
            s001 = pa.get("sig001", 0) or 0
            pc   = ls.get("podium_changes", 0) or 0
            status = _osnr_status(pairwise_agg, lojo_sum, jpos)
            panel_rows.append({
                "Pos":         jpos,
                "Name":        j.get("name", ""),
                "Country":     j.get("country", "") or "—",
                "Sig (p≤0.01)": s01,
                "Sig (p≤0.001)": s001,
                "LOJO Δ":      "YES" if pc > 0 else "No",
                "OSNR Status": status,
            })
        df_p = pd.DataFrame(panel_rows)

        def _col_status(val):
            if val == "Tier 2":  return f"background-color:{C_ORANGE};font-weight:bold"
            if val == "Tier 1":  return f"background-color:{C_YELLOW}"
            return f"background-color:{C_GREEN};color:#555"

        def _col_wc(val):
            if val == "YES": return f"color:{C_RED_TEXT};font-weight:bold"
            return "color:#888"

        styled_p = (df_p.style
                    .applymap(_col_status, subset=["OSNR Status"])
                    .applymap(_col_wc, subset=["LOJO Δ"]))
        st.dataframe(styled_p, use_container_width=True, hide_index=True)

        # LOJO winner-change alert
        wc_total = sum(1 for ls in lojo_sum.values() if (ls.get("podium_changes") or 0) > 0)
        if wc_total:
            st.error(f"⚠️ **{wc_total}** judge removal(s) would change a podium position")
        else:
            st.success("✅ No judge removal changes any podium position")
        st.caption(
            "ℹ️ **LOJO Δ** reflects mathematical sensitivity — it shows what would happen "
            "hypothetically if that judge were absent. A 'YES' does **not** mean the judge "
            "was biased or is being removed; it means the result was close enough that this "
            "judge's scores were the swing vote. Judge removal only occurs when LOJO Δ = YES "
            "**and** the judge also has p ≤ 0.001 pairwise significance (Tier 2 flag). "
            "A 'YES' here means any of the top-3 podium positions would change."
        )

        # LOJO highlights
        st.subheader("LOJO Highlights")
        lojo_rows = []
        actual_w = None
        for jpos in jpos_list:
            ls = lojo_sum.get(jpos, {})
            if actual_w is None:
                actual_w = ls.get("actual_winner", "") or ""
            cf_w = ls.get("cf_winner", "") or ""
            tau  = ls.get("kendall_tau", 0) or 0
            pc_j = ls.get("podium_changes", 0) or 0
            lojo_rows.append({
                "Judge":      jpos,
                "Kendall τ":  round(tau, 5),
                "Podium Δ?":  "YES" if pc_j > 0 else "No",
                "CF Winner":  cf_w if cf_w != actual_w else "—",
            })
        df_lj = pd.DataFrame(lojo_rows)
        styled_lj = df_lj.style.applymap(_col_wc, subset=["Podium Δ?"])
        st.dataframe(styled_lj, use_container_width=True, hide_index=True)


def render_tab_raw_scores(data):
    judges    = data["judges"]
    jpos_list = data["judge_positions"]
    entries   = data["entries"]

    st.subheader("Raw Judge GOE Scores")
    st.caption("Individual GOE integers (−5 to +5).  Color: red = low, green = high.")

    rows = []
    for entry in entries:
        for el in entry["elements"]:
            row = {
                "Rank":    entry["rank"],
                "Team":    entry["team_name"],
                "NOC":     entry["noc"],
                "Element": el["element_code"],
                "BV":      el["base_value"],
            }
            for jpos in jpos_list:
                if jpos in el["goe_by_pos"]:
                    row[jpos] = el["goe_by_pos"][jpos]["goe"]
                else:
                    row[jpos] = None
            row["Panel GOE"] = el["panel_goe_official"]
            row["Elem Score"] = el["r1_elem"]
            rows.append(row)

    df = pd.DataFrame(rows)

    def _goe_color(val):
        if pd.isna(val):
            return "background-color:#D3D3D3"
        return f"background-color:{GOE_COLORS.get(int(val), '#FFFFFF')}"

    styled = df.style.applymap(_goe_color, subset=list(jpos_list))
    st.dataframe(styled, use_container_width=True, hide_index=True,
                 height=min(700, len(rows) * 36 + 50))

    st.subheader("Entry Totals (Regime 1 — Official)")
    totals = [{"Rank": e["rank"], "Team": e["team_name"], "NOC": e["noc"],
               "TES": e["tes_r1"], "PCS": e["pcs_r1"], "TSS": e["tss_r1"]}
              for e in entries]
    st.dataframe(pd.DataFrame(totals), use_container_width=True, hide_index=True)


def render_tab_regime_comparison(data):
    ev       = data["event_info"]
    judges   = data["judges"]
    entries  = data["entries"]

    flagged_pos  = ev.get("flagged_judge_pos")
    flagged_name = judges.get(flagged_pos, {}).get("name", "none") if flagged_pos else "none"

    st.subheader("Three-Regime Scoring Comparison")
    cap = (f"R1 = Official (ISU trimmed mean) | R0 = Raw average | "
           f"R2 = OSNR-adjusted ({flagged_pos}/{flagged_name} removed)"
           if flagged_pos else
           "R1 = Official (ISU trimmed mean) | R0 = Raw average "
           "| R2 = same as R1 (no OSNR flag in this event)")
    st.caption(cap)

    # ── Summary table ─────────────────────────────────────────────────────────
    rows = []
    for e in entries:
        d0 = e["rank_r0"] - e["rank"]
        d2 = e["rank_r2"] - e["rank"]
        rows.append({
            "R1 Rank": e["rank"],
            "Team":    e["team_name"],
            "NOC":     e["noc"],
            "R1 TSS":  e["tss_r1"],
            "R0 Rank": e["rank_r0"],
            "R0 TSS":  e["tss_r0"],
            "R0 Δ Rank": d0,
            "R2 Rank": e["rank_r2"],
            "R2 TSS":  e["tss_r2"],
            "R2 Δ Rank": d2,
        })
    df = pd.DataFrame(rows)

    def _delta_color(val):
        if isinstance(val, int):
            if val < 0: return f"color:{C_GREEN_TEXT};font-weight:bold"
            if val > 0: return f"color:{C_RED_TEXT};font-weight:bold"
        return "color:#888"

    styled = df.style.applymap(_delta_color, subset=["R0 Δ Rank", "R2 Δ Rank"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── TSS comparison bar chart ───────────────────────────────────────────────
    st.subheader("TSS by Regime")
    teams = [f"#{e['rank']} {e['team_name'][:20]}" for e in entries]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="R1 Official",     x=teams, y=[e["tss_r1"] for e in entries],
                         marker_color=C_GREEN,  marker_line_color=C_DARK_BLUE, marker_line_width=1))
    fig.add_trace(go.Bar(name="R0 Raw Mean",     x=teams, y=[e["tss_r0"] for e in entries],
                         marker_color=C_YELLOW, marker_line_color=C_DARK_BLUE, marker_line_width=1))
    if flagged_pos:
        fig.add_trace(go.Bar(name="R2 OSNR-Adjusted", x=teams, y=[e["tss_r2"] for e in entries],
                             marker_color=C_SALMON, marker_line_color=C_DARK_BLUE, marker_line_width=1))
    fig.update_layout(barmode="group", height=480, plot_bgcolor="white",
                      xaxis_tickangle=-40, yaxis_title="Total Segment Score",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    # ── Per-entry element details (expandable) ────────────────────────────────
    st.subheader("Element-Level Details")
    for entry in entries:
        with st.expander(f"#{entry['rank']}  {entry['team_name']}  ({entry['noc']})"):
            el_rows = [{
                "Element": el["element_code"],
                "BV":      el["base_value"],
                "GOE R1":  el["r1_goe"],   "Score R1": el["r1_elem"],
                "GOE R0":  el["r0_goe"],   "Score R0": el["r0_elem"],
                "GOE R2":  el["r2_goe"],   "Score R2": el["r2_elem"],
            } for el in entry["elements"]]
            st.dataframe(pd.DataFrame(el_rows), use_container_width=True, hide_index=True)


def render_tab_judge_statistics(data):
    judges       = data["judges"]
    jpos_list    = data["judge_positions"]
    judge_stats  = data["judge_stats"]
    pairwise_agg = data["pairwise_agg"]
    lojo_sum     = data["lojo_summary"]
    max_bias_rows = data.get("max_bias_rows", {})

    st.subheader("Judge Statistics — OSNR Analysis")

    # ── Z-score bar chart ──────────────────────────────────────────────────────
    z_vals   = [judge_stats.get(jp, {}).get("bias_z", 0) or 0 for jp in jpos_list]
    bar_clrs = []
    for jp, z in zip(jpos_list, z_vals):
        status = _osnr_status(pairwise_agg, lojo_sum, jp)
        bar_clrs.append(C_ORANGE if status == "Tier 2" else
                        C_YELLOW if status == "Tier 1" else C_BLUE_HDR)

    fig = go.Figure(go.Bar(
        x=list(jpos_list), y=z_vals,
        marker_color=bar_clrs, marker_line_color=C_DARK_BLUE, marker_line_width=1,
        text=[f"{z:.3f}" for z in z_vals], textposition="outside",
    ))
    fig.add_hline(y=0,    line_dash="solid", line_color=C_DARK_BLUE, line_width=1)
    fig.add_hline(y=1.0,  line_dash="dash",  line_color=C_RED_TEXT,  line_width=1,
                  annotation_text="+1σ", annotation_position="top right")
    fig.add_hline(y=-1.0, line_dash="dash",  line_color=C_RED_TEXT,  line_width=1,
                  annotation_text="−1σ")
    fig.update_layout(height=380, plot_bgcolor="white",
                      xaxis_title="Judge Position", yaxis_title="Bias Z-Score",
                      showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # ── Detailed table ─────────────────────────────────────────────────────────
    rows = []
    for jpos in sorted(jpos_list, key=lambda jp: -(pairwise_agg.get(jp, {}).get("sig01", 0) or 0)):
        j  = judges.get(jpos, {})
        js = judge_stats.get(jpos, {})
        pa = pairwise_agg.get(jpos, {"sig01": 0, "sig001": 0, "max_bias": 0})
        mb = max_bias_rows.get(jpos, {}) or {}
        ls = lojo_sum.get(jpos, {})
        pc = ls.get("podium_changes", 0) or 0
        cf = ls.get("cf_winner", "") or ""
        aw = ls.get("actual_winner", "") or ""
        status = _osnr_status(pairwise_agg, lojo_sum, jpos)
        rows.append({
            "Pos":         jpos,
            "Name":        j.get("name", ""),
            "Country":     j.get("country", "") or "—",
            "Mean GOE Δ":  round(js.get("mean_goe_dev", 0) or 0, 4),
            "Bias Z":      round(js.get("bias_z", 0) or 0, 3),
            "Panel Corr.": round(js.get("correlation", 0) or 0, 3),
            "Sig p≤0.01":  pa.get("sig01", 0) or 0,
            "Sig p≤0.001": pa.get("sig001", 0) or 0,
            "Max B(j)":    round(pa.get("max_bias", 0) or 0, 2),
            "Max B(j) vs": mb.get("skater_b", "") if mb else "",
            "Kendall τ":   round(ls.get("kendall_tau", 0) or 0, 5),
            "Podium Δ?":   "YES" if pc > 0 else "No",
            "CF Winner":   cf if cf != aw else "—",
            "OSNR Status": status,
        })
    df = pd.DataFrame(rows)

    def _col_status(val):
        if val == "Tier 2": return f"background-color:{C_ORANGE};font-weight:bold"
        if val == "Tier 1": return f"background-color:{C_YELLOW}"
        return f"background-color:{C_GREEN};color:#555"

    def _col_wc(val):
        if val == "YES": return f"color:{C_RED_TEXT};font-weight:bold"
        return "color:#888"

    styled = (df.style
              .applymap(_col_status, subset=["OSNR Status"])
              .applymap(_col_wc, subset=["Podium Δ?"]))
    st.dataframe(styled, use_container_width=True, hide_index=True)


def render_tab_pairwise(data):
    jpos_list    = data["judge_positions"]
    pairwise_rows = data["pairwise_rows"]
    pw_totals     = data.get("pw_totals")

    st.subheader("Pairwise B(j) Bias Statistics")

    if pw_totals:
        total, s01, s001, sbon = pw_totals
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pairs Tested",          f"{total:,}")
        c2.metric("Sig (p≤0.01)",          s01 or 0)
        c3.metric("Sig (p≤0.001)",         s001 or 0)
        c4.metric("Bonferroni-Significant", sbon or 0)

    if not pairwise_rows:
        st.info("No pairs with p ≤ 0.10 in this event.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        sig_opts = {"All (p ≤ 0.10)": 0.10, "p ≤ 0.05": 0.05,
                    "p ≤ 0.01  ★★": 0.01, "p ≤ 0.001  ★★★": 0.001}
        sig_sel = st.selectbox("Significance", list(sig_opts.keys()))
    with col2:
        jfilt = st.multiselect("Judge position(s)", list(jpos_list))
    with col3:
        dirfilt = st.selectbox("Direction", ["All", "B(j) > 0 (favors A)", "B(j) < 0 (favors B)"])

    # Build DataFrame
    cols_pw = ["Judge Pos", "Judge Name", "Judge Country",
               "Team A", "NOC A", "Rank A",
               "Team B", "NOC B", "Rank B",
               "B(j)", "p-value", "Sig p≤0.01", "Sig p≤0.001", "Sig Bonferroni",
               "Mean Dev A", "Mean Dev B", "Differential", "Elem A", "Elem B"]
    df = pd.DataFrame(list(pairwise_rows), columns=cols_pw)

    df = df[df["p-value"] <= sig_opts[sig_sel]]
    if jfilt:
        df = df[df["Judge Pos"].isin(jfilt)]
    if dirfilt == "B(j) > 0 (favors A)":
        df = df[df["B(j)"] > 0]
    elif dirfilt == "B(j) < 0 (favors B)":
        df = df[df["B(j)"] < 0]

    def _sig_label(row):
        if row["Sig p≤0.001"]: return "★★★ p≤0.001"
        if row["Sig p≤0.01"]:  return "★★ p≤0.01"
        if row["p-value"] <= 0.05: return "★ p≤0.05"
        return "p≤0.10"

    def _sig_color(val):
        if "★★★" in str(val): return f"background-color:{C_ORANGE}"
        if "★★ " in str(val): return f"background-color:{C_YELLOW}"
        if "★ p" in str(val): return "background-color:#FFFFD0"
        return ""

    df["Sig Level"] = df.apply(_sig_label, axis=1)
    df["Direction"] = df["B(j)"].apply(
        lambda v: "Favors A" if v > 0 else ("Favors B" if v < 0 else "Neutral"))

    display_cols = ["Judge Pos", "Judge Name",
                    "Team A", "Rank A", "Team B", "Rank B",
                    "B(j)", "p-value", "Sig Level", "Direction"]
    df_disp = df[display_cols].sort_values("p-value").reset_index(drop=True)

    styled = df_disp.style.applymap(_sig_color, subset=["Sig Level"])
    st.dataframe(styled, use_container_width=True, hide_index=True,
                 height=min(600, len(df_disp) * 36 + 50))
    st.caption(
        "B(j) = mean GOE deviation for Team A minus mean deviation for Team B. "
        "Positive = judge scores Team A higher relative to panel consensus."
    )


def render_tab_lojo(data):
    ev        = data["event_info"]
    judges    = data["judges"]
    jpos_list = data["judge_positions"]
    entries   = data["entries"]
    lojo_sum  = data["lojo_summary"]
    lojo_scores = data["lojo_scores"]

    st.subheader("Leave-One-Judge-Out (LOJO) Counterfactual Rankings")
    st.caption("Green = rank improves when judge removed  |  Red = rank drops  |  White = unchanged")

    # ── Heatmap ───────────────────────────────────────────────────────────────
    team_labels = [f"#{e['rank']} {e['team_name'][:22]}" for e in entries]
    entry_ids   = [e["entry_id"] for e in entries]
    jpos_list_l = list(jpos_list)

    z_vals    = []
    text_vals = []
    for eid in entry_ids:
        row_z, row_t = [], []
        for jpos in jpos_list_l:
            ls_e = lojo_scores.get(jpos, {}).get(eid, {})
            rchg    = ls_e.get("rank_change", 0) or 0
            cf_rank = ls_e.get("cf_rank")
            # negate: improved rank (lower number) = positive z = green
            row_z.append(-rchg)
            if cf_rank is not None:
                sign = "+" if rchg < 0 else ("" if rchg == 0 else "")
                delta_str = ("" if rchg == 0 else
                             f"+{abs(rchg)}" if rchg < 0 else f"−{rchg}")
                row_t.append(f"CF rank: {cf_rank}<br>Δ: {delta_str or '0'}")
            else:
                row_t.append("—")
        z_vals.append(row_z)
        text_vals.append(row_t)

    fig = go.Figure(data=go.Heatmap(
        z=z_vals, x=jpos_list_l, y=team_labels,
        text=text_vals,
        hovertemplate="%{y}<br>Remove %{x}<br>%{text}<extra></extra>",
        colorscale=[[0.0, C_SALMON], [0.5, "#FFFFFF"], [1.0, C_GREEN]],
        zmid=0, showscale=True,
        colorbar=dict(title="Rank Δ",
                      tickvals=[-2, -1, 0, 1, 2],
                      ticktext=["−2 (worse)", "−1", "0", "+1", "+2 (better)"]),
    ))

    # Highlight flagged judge column
    flagged_pos = ev.get("flagged_judge_pos")
    if flagged_pos and flagged_pos in jpos_list_l:
        idx = jpos_list_l.index(flagged_pos)
        fig.add_vline(x=idx - 0.5, line_dash="dash",
                      line_color=C_RED_TEXT, line_width=2,
                      annotation_text="Flagged", annotation_position="top")

    fig.update_layout(
        height=max(380, len(entries) * 26 + 140),
        xaxis_title="Judge Removed",
        yaxis_title="Team (Official Rank)",
        yaxis_autorange="reversed",
        plot_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── LOJO summary table ────────────────────────────────────────────────────
    st.subheader("LOJO Summary per Judge")
    st.caption(
        "ℹ️ **Winner Changes** and **Podium Changes** measure mathematical sensitivity "
        "— how close the result was — not whether a judge was biased. A judge with "
        "Winner Changes > 0 was the swing vote in a tight competition, but is only "
        "flagged for removal if they *also* have p ≤ 0.001 pairwise significance (Tier 2). "
        "Judges with no statistical flag are reported here for completeness."
    )
    lojo_rows = []
    for jpos in jpos_list_l:
        ls  = lojo_sum.get(jpos, {})
        aw  = ls.get("actual_winner", "") or ""
        cfw = ls.get("cf_winner", "") or ""
        lojo_rows.append({
            "Judge":           jpos,
            "Name":            judges.get(jpos, {}).get("name", ""),
            "Kendall τ":       round(ls.get("kendall_tau", 0) or 0, 5),
            "Winner Changes":  ls.get("winner_changes", 0) or 0,
            "Podium Changes":  ls.get("podium_changes", 0) or 0,
            "Rank Inversions": ls.get("n_rank_inversions", 0) or 0,
            "CF Winner":       cfw if cfw != aw else "—",
        })
    df_lj = pd.DataFrame(lojo_rows)

    def _wc_color(val):
        if isinstance(val, int) and val > 0:
            return f"color:{C_RED_TEXT};font-weight:bold"
        return ""

    styled = df_lj.style.applymap(_wc_color, subset=["Winner Changes", "Podium Changes"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


def render_tab_download(event_id, data):
    ev = data["event_info"]
    st.subheader("Download Excel Report")
    st.write(
        f"Generate the full 7-tab OSNR Excel workbook for "
        f"**{ev.get('competition_name', '')} — "
        f"{ev.get('discipline', '')} {ev.get('segment', '')}**."
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("⚙️ Generate Excel", type="primary", key="gen_excel_btn"):
            with st.spinner("Building 7-tab Excel workbook…"):
                excel_bytes = generate_excel_bytes(event_id)
            if excel_bytes:
                st.session_state["excel_bytes"]    = excel_bytes
                st.session_state["excel_event_id"] = event_id
                st.success("Report ready — click Download below.")
            # error messages shown inside generate_excel_bytes()

        if (st.session_state.get("excel_event_id") == event_id
                and "excel_bytes" in st.session_state):
            # Auto-build filename
            dt   = ev.get("datetime_local") or ""
            year = dt[:4] if len(dt) >= 4 else ""
            cn   = ev.get("competition_name", "")
            pfx  = ("OWG" if "Olympic" in cn else "WC" if "World" in cn
                    else "GPF" if "Grand Prix" in cn else "Event")
            dm   = {"Ice Dance": "ID", "Men Single Skating": "MS",
                    "Women Single Skating": "LS", "Pair Skating": "PR"}
            sm   = {"Rhythm Dance": "RD", "Free Dance": "FD",
                    "Short Program": "SP", "Free Skating": "FS"}
            dc   = dm.get(ev.get("discipline", ""), "XX")
            sc   = sm.get(ev.get("segment", ""),    "XX")
            fname = f"{pfx}{year}_{dc}_{sc}_OSNR.xlsx"
            st.download_button(
                "📥 Download Excel",
                data=st.session_state["excel_bytes"],
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_excel_btn",
            )

    with col2:
        st.info(
            "**The Excel report contains 7 tabs:**\n\n"
            "1. **Summary** — Standings, panel, OSNR flags, LOJO highlights  \n"
            "2. **Raw Scores** — Full judge GOE scores, color-coded  \n"
            "3. **Regime Comparison** — R0 / R1 / R2 side-by-side  \n"
            "4. **Judge Statistics** — B(j) counts, LOJO, significance  \n"
            "5. **Pairwise B(j)** — All significant pairs, filterable  \n"
            "6. **LOJO Counterfactual** — Rank heatmap per judge  \n"
            "7. **Legend** — Color codes and methodology notes"
        )


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2: Event Analysis — main
# ════════════════════════════════════════════════════════════════════════════

def page_event_analysis():
    st.title("Event Analysis")
    if st.session_state.pop("scroll_to_top", False):
        _scroll("top")

    # Cascade selectors: competition → event
    comps = db_get_competitions()
    comp_opts = {c["name"]: c["competition_id"] for c in comps}

    # Try to pre-select competition from session state (from goto_event_id)
    goto_id = st.session_state.pop("goto_event_id", None)
    presel_comp_idx = 0
    presel_ev_idx   = 0

    if goto_id is not None:
        all_ev = db_get_events()
        for ev_row in all_ev:
            if ev_row["event_id"] == goto_id:
                # Find which competition this belongs to
                for i, comp in enumerate(comps):
                    evs_for_comp = db_get_events(comp["competition_id"])
                    for j, ev2 in enumerate(evs_for_comp):
                        if ev2["event_id"] == goto_id:
                            presel_comp_idx = i
                            presel_ev_idx   = j
                            break
                break

    comp_name = st.selectbox("Competition", list(comp_opts.keys()),
                             index=presel_comp_idx)
    comp_id   = comp_opts[comp_name]

    events = db_get_events(comp_id)
    if not events:
        st.warning("No events found for this competition.")
        return

    ev_opts = {f"{e['discipline']} — {e['segment']}  ({e['n_entries']} entries)": e["event_id"]
               for e in events}
    ev_label = st.selectbox("Event", list(ev_opts.keys()), index=presel_ev_idx)
    event_id = ev_opts[ev_label]

    # Load data (cached after first call)
    with st.spinner("Loading event data…"):
        data = db_load_event(event_id)

    ev_info = data["event_info"]
    st.caption(
        f"**{ev_info.get('competition_name', '')}** | "
        f"{ev_info.get('discipline', '')} — {ev_info.get('segment', '')} | "
        f"{len(data['entries'])} entries | "
        f"{len(data['judge_positions'])} judges"
    )

    tabs = st.tabs([
        "Summary",
        "Raw Scores",
        "Regime Comparison",
        "Judge Statistics",
        "Pairwise B(j)",
        "LOJO Counterfactual",
        "Download Report",
    ])
    with tabs[0]: render_tab_summary(data)
    with tabs[1]: render_tab_raw_scores(data)
    with tabs[2]: render_tab_regime_comparison(data)
    with tabs[3]: render_tab_judge_statistics(data)
    with tabs[4]: render_tab_pairwise(data)
    with tabs[5]: render_tab_lojo(data)
    with tabs[6]: render_tab_download(event_id, data)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 3: Judge Profiles
# ════════════════════════════════════════════════════════════════════════════

def page_judge_profiles():
    st.title("Judge Profiles")
    st.caption("Cross-event statistics for named judges (anonymised panel positions excluded)")

    df = db_get_all_judge_stats()
    if df.empty:
        st.warning("No named judge data found.")
        return

    col1, col2 = st.columns(2)
    with col1:
        min_ev = st.slider("Minimum events judged", 1, 20, 2)
    with col2:
        cc_filter = st.text_input("Country code filter (e.g. FRA, USA)", "")

    df_f = df[df["Events"] >= min_ev]
    if cc_filter.strip():
        df_f = df_f[df_f["Country"].str.upper().str.contains(cc_filter.upper(), na=False)]

    st.subheader(f"Bias Profile ({len(df_f)} judges)")
    fig = px.scatter(
        df_f, x="Avg Z", y="Max |Z|",
        size="Events", color="Country",
        hover_name="Judge Name",
        hover_data={"Events": True, "Avg Z": ":.3f", "Max |Z|": ":.3f",
                    "Total Outliers": True, "Home Diff": ":.3f"},
        labels={"Avg Z": "Average Bias Z-Score", "Max |Z|": "Peak |Z-Score|"},
        height=520,
    )
    fig.add_vline(x=0,   line_dash="solid", line_color="#aaa")
    fig.add_hline(y=1.0, line_dash="dash",  line_color=C_RED_TEXT,
                  annotation_text="Tier 1 threshold")
    fig.update_layout(plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Judge Statistics Table")
    df_disp = df_f.sort_values("Max |Z|", ascending=False).reset_index(drop=True)

    def _color_z(val):
        if isinstance(val, float):
            if abs(val) >= 1.5: return f"background-color:{C_SALMON};font-weight:bold"
            if abs(val) >= 1.0: return f"background-color:{C_YELLOW}"
        return ""

    styled = df_disp.style.applymap(_color_z, subset=["Avg Z", "Max |Z|"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 4: System-Wide Stats
# ════════════════════════════════════════════════════════════════════════════

def page_system_stats():
    st.title("System-Wide Statistics")
    st.caption("Distribution of bias z-scores across all 1,261 judge-event records")

    df = db_get_zscore_distribution()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records",    f"{len(df):,}")
    c2.metric("Mean Z",     f"{df['bias_z'].mean():.4f}")
    c3.metric("|Z| > 1.0",  int((df["bias_z"].abs() > 1.0).sum()))
    c4.metric("|Z| > 1.5",  int((df["bias_z"].abs() > 1.5).sum()))

    col1, col2, col3 = st.columns(3)
    with col1:
        disc_opts = ["All"] + sorted(df["discipline"].dropna().unique().tolist())
        disc_sel  = st.selectbox("Discipline", disc_opts)
    with col2:
        comp_opts = ["All"] + sorted(df["competition"].dropna().unique().tolist())
        comp_sel  = st.selectbox("Competition", comp_opts)
    with col3:
        seas_opts = ["All"] + sorted(df["season"].dropna().unique().tolist(), reverse=True)
        seas_sel  = st.selectbox("Season", seas_opts)

    df_f = df.copy()
    if disc_sel != "All": df_f = df_f[df_f["discipline"] == disc_sel]
    if comp_sel != "All": df_f = df_f[df_f["competition"] == comp_sel]
    if seas_sel != "All": df_f = df_f[df_f["season"] == seas_sel]

    col_a, col_b = st.columns(2)
    with col_a:
        fig_hist = px.histogram(
            df_f, x="bias_z", nbins=60,
            title="Distribution of Bias Z-Scores",
            labels={"bias_z": "Bias Z-Score"},
            color_discrete_sequence=[C_BLUE_HDR], height=400,
        )
        fig_hist.add_vline(x=0,    line_dash="solid", line_color=C_DARK_BLUE)
        fig_hist.add_vline(x=1.0,  line_dash="dash",  line_color=C_RED_TEXT,
                           annotation_text="+1σ")
        fig_hist.add_vline(x=-1.0, line_dash="dash",  line_color=C_RED_TEXT,
                           annotation_text="−1σ")
        fig_hist.update_layout(plot_bgcolor="white", bargap=0.02)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_b:
        fig_box = px.box(
            df_f, x="discipline", y="bias_z", color="discipline",
            title="Bias Z-Score by Discipline",
            labels={"bias_z": "Bias Z-Score", "discipline": "Discipline"},
            height=400,
        )
        fig_box.add_hline(y=0, line_dash="solid", line_color="#aaa")
        fig_box.update_layout(plot_bgcolor="white", showlegend=False,
                              xaxis_tickangle=-20)
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("Top 50 by |Z-Score|")
    df_top = df_f.copy()
    df_top["abs_z"] = df_top["bias_z"].abs()
    df_top = df_top.sort_values("abs_z", ascending=False).head(50)
    df_disp = df_top[["judge_name", "judge_country", "discipline", "segment",
                       "competition", "bias_z", "mean_goe_dev", "outlier_count"]].copy()
    df_disp.columns = ["Judge", "Country", "Discipline", "Segment",
                        "Competition", "Bias Z", "Mean GOE Dev", "Outliers"]

    def _color_z(val):
        if isinstance(val, float):
            if abs(val) >= 1.5: return f"background-color:{C_SALMON};font-weight:bold"
            if abs(val) >= 1.0: return f"background-color:{C_YELLOW}"
        return ""

    styled = df_disp.style.applymap(_color_z, subset=["Bias Z"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 5: Glossary
# ════════════════════════════════════════════════════════════════════════════

GLOSSARY = [
    # ── Scoring system ──────────────────────────────────────────────────────
    ("IJS",
     "International Judging System",
     "The ISU's current judging framework, introduced after the 2002 Salt Lake City "
     "judging scandal. Replaces the old 6.0 system. Scores are broken into two "
     "components: technical elements (GOE) and program components (PCS), each judged "
     "by a separate panel of nine judges."),

    ("GOE",
     "Grade of Execution",
     "A per-element score awarded by each judge on a scale of −5 to +5 (in integer "
     "steps), reflecting how well a skater executed a specific technical element "
     "(jump, spin, step sequence, lift, etc.). The highest and lowest GOE scores "
     "are trimmed before averaging."),

    ("PCS",
     "Program Component Score",
     "A set of scores (0.25–10.00) awarded by each judge across five components: "
     "Skating Skills, Transitions, Performance, Composition, and Interpretation. "
     "PCS reflects the artistic and overall skating quality of the program. As with "
     "GOE, the highest and lowest scores are trimmed."),

    ("TSS",
     "Total Segment Score",
     "The combined score for a single program segment (Short Program or Free "
     "Skating). TSS = TES (Technical Element Score) + PCS − deductions. A skater's "
     "final competition result is the sum of TSS across all segments."),

    ("TES",
     "Technical Element Score",
     "The sum of base values and GOE adjustments for all technical elements "
     "performed in a segment. Each element has a published base value; the panel-"
     "averaged GOE is added to (or subtracted from) that base value."),

    ("Base Value",
     "Base Value",
     "The predetermined point value assigned by the ISU to each technical element "
     "(e.g., a quad Lutz has a higher base value than a double Lutz). Skaters earn "
     "the base value regardless of execution quality; GOE adjusts upward or downward "
     "from there."),

    ("Trimmed Mean",
     "Trimmed Mean",
     "The averaging method used under IJS. For a nine-judge panel, the highest and "
     "lowest scores are discarded and the remaining seven are averaged. This reduces "
     "the influence of any single extreme score."),

    ("Short Program",
     "Short Program (SP)",
     "The first of two competitive segments in most ISU disciplines. Skaters must "
     "perform a prescribed set of required elements within a time limit (typically "
     "2:40–2:50). Results count toward the final total score."),

    ("Free Skating",
     "Free Skating (FS) / Free Dance",
     "The second competitive segment, also called the Free Dance in ice dance. "
     "Skaters have more freedom in element selection and choreography. Longer than "
     "the Short Program, it carries greater weight in the final standings."),

    ("Rhythm Dance",
     "Rhythm Dance (RD)",
     "The short-program equivalent for ice dance teams. Skaters must incorporate "
     "a required rhythm (e.g., blues, tango) and prescribed pattern dances."),

    ("Discipline",
     "Discipline",
     "The branch of figure skating being competed: Men's Single Skating, Ladies' "
     "(Women's) Single Skating, Pair Skating, or Ice Dance. Each discipline has "
     "its own rules and element requirements."),

    ("Segment",
     "Segment",
     "One of the individual programs within a competition event — either the Short "
     "Program / Rhythm Dance or the Free Skating / Free Dance. Each segment is "
     "judged and scored independently."),

    ("Event",
     "Event",
     "A specific combination of discipline and segment at a given competition "
     "(e.g., 'OWG 2026 — Ice Dance Rhythm Dance'). The OSNR database contains "
     "141 events across 17 competitions."),

    ("Judge Mark",
     "Judge Mark",
     "A single score awarded by one judge for one element or program component. "
     "The database contains 283,774 judge marks in total (200,715 GOE marks + "
     "83,059 PCS marks)."),

    # ── Competition structure ────────────────────────────────────────────────
    ("Competition",
     "Competition",
     "A named ISU-sanctioned event such as the Olympic Winter Games, ISU World "
     "Championships, Grand Prix Final, Four Continents, or European Championships. "
     "The database covers 17 competitions spanning multiple seasons."),

    ("Season",
     "Season",
     "The figure skating competitive year, which runs from approximately July "
     "through April and is identified by two calendar years (e.g., '2024/25')."),

    ("NOC",
     "National Olympic Committee Code",
     "The three-letter country abbreviation assigned to each skater by their "
     "National Olympic Committee (e.g., USA, FRA, JPN). Used to identify "
     "skater nationality in results tables."),

    ("Panel",
     "Judge Panel",
     "The group of nine judges assigned to score an event. Under IJS anonymity "
     "rules, judges are identified only by position (J1–J9) during the event; "
     "names may be released afterward."),

    ("Judge Position",
     "Judge Position (J1–J9)",
     "The seat number assigned to a judge within a panel for a given event. "
     "Positions are assigned randomly and change each event, so the same judge "
     "may sit in different positions across events."),

    # ── OSNR methodology ────────────────────────────────────────────────────
    ("OSNR",
     "Outlier Score Normalization and Removal",
     "The bias-detection and judge-removal methodology at the core of this "
     "database. OSNR identifies judges whose scores deviate systematically from "
     "the rest of the panel, flags the most extreme cases, and recalculates "
     "standings after removing flagged judges."),

    ("Bias Z-Score",
     "Bias Z-Score",
     "A standardized measure of how far a judge's scores deviate from the panel "
     "average across all elements in an event. Calculated as: (judge's mean "
     "deviation) ÷ (standard deviation of panel deviations). A Z-score of 0 means "
     "the judge scored in line with the panel; large positive or negative values "
     "indicate systematic over- or under-scoring."),

    ("Mean GOE Deviation",
     "Mean GOE Deviation",
     "The average difference between a judge's GOE score and the panel trimmed "
     "mean for each element, averaged across all elements the judge scored in an "
     "event. Positive values indicate the judge tends to score higher than peers; "
     "negative values indicate lower scoring."),

    ("Outlier Count",
     "Outlier Count",
     "The number of individual element scores given by a judge that are classified "
     "as statistical outliers relative to the panel on that element. A high outlier "
     "count indicates a judge who frequently diverges from colleagues."),

    ("Panel Correlation",
     "Panel Correlation",
     "The Kendall rank correlation between a judge's element rankings and the "
     "panel-consensus rankings across all elements in an event. Values near +1 "
     "indicate strong agreement with the panel; values near 0 or negative indicate "
     "disagreement in how the judge ranks skaters relative to each other."),

    ("Kendall τ",
     "Kendall's Tau (τ)",
     "A non-parametric rank correlation coefficient ranging from −1 to +1. Used "
     "to measure agreement between a judge's element-by-element rankings and the "
     "panel consensus. τ = +1 means perfect agreement; τ = −1 means perfect "
     "disagreement; τ = 0 means no correlation."),

    ("Home Country Differential",
     "Home Country Differential",
     "The average difference in a judge's scores for skaters from the judge's own "
     "country versus skaters from all other countries. A positive value indicates "
     "the judge scores compatriots higher than peers do; this is a marker of "
     "potential nationalistic bias."),

    # ── Pairwise statistics ──────────────────────────────────────────────────
    ("Pairwise B(j)",
     "Pairwise B(j) Test",
     "A statistical test that compares the scoring pattern of one judge against "
     "every other judge on the panel, one pair at a time. For each judge pair, "
     "it tests whether the two judges systematically differ in how they score "
     "skaters relative to each other. Produces a p-value for each pair."),

    ("Significant Pair (p≤0.01)",
     "Significant Pair (p ≤ 0.01) — Tier 1",
     "A judge pair where the pairwise B(j) test yields a p-value of 0.01 or less, "
     "indicating a statistically significant difference in scoring patterns. "
     "This is the Tier 1 threshold: noteworthy but not by itself sufficient for "
     "judge removal. The database contains 11,039 such pairs."),

    ("Significant Pair (p≤0.001)",
     "Significant Pair (p ≤ 0.001) — Tier 2",
     "A judge pair where the pairwise B(j) test yields a p-value of 0.001 or less, "
     "indicating a highly significant difference in scoring patterns. This is the "
     "Tier 2 threshold: the more stringent criterion used in combination with "
     "outcome metrics (winner changes) to flag judges for removal. The database "
     "contains 1,774 such pairs."),

    # ── LOJO / counterfactual ────────────────────────────────────────────────
    ("LOJO",
     "Leave-One-Judge-Out (LOJO)",
     "A counterfactual simulation that recalculates the event results as if each "
     "judge were removed from the panel, one at a time. By comparing the LOJO "
     "standings to the official standings, we can measure what difference, if any, "
     "each judge's presence made to the outcome."),

    ("R0",
     "R0 — Official Result",
     "The actual, officially published competition result using all nine judges' "
     "scores (after the standard trimmed-mean calculation)."),

    ("R1",
     "R1 — OSNR-Adjusted Result",
     "The recalculated result after applying OSNR normalization. Specifically, this "
     "is the result after removing the one judge identified as the most extreme "
     "outlier (if any) from the panel."),

    ("R2",
     "R2 — Second Removal Result",
     "The recalculated result after a second judge removal. Used to assess whether "
     "a second outlier judge on the same panel also affected the outcome."),

    ("Winner Change",
     "Winner Change",
     "A case where removing a specific judge from the panel (via LOJO simulation) "
     "would hypothetically change which skater finishes first. Important: a Winner "
     "Change indicates the result was close enough that this judge was the swing "
     "vote — it does not by itself indicate bias. Actual judge removal under OSNR "
     "requires a Winner Change AND p ≤ 0.001 pairwise significance (Tier 2 flag). "
     "25 events in the database have at least one judge whose removal would change "
     "the winner."),

    ("Podium Change",
     "Podium Change",
     "A case where removing a judge would change any of the top-three finishers "
     "(gold, silver, or bronze). A broader measure of judge impact than winner "
     "changes alone. 47 events in the database have at least one podium change."),

    ("Counterfactual Standings",
     "Counterfactual Standings",
     "The hypothetical final rankings produced by the LOJO simulation for a "
     "specific judge removal. Shown in the LOJO Counterfactual tab alongside "
     "official standings for direct comparison."),

    # ── Flags and tiers ─────────────────────────────────────────────────────
    ("Tier 1 Flag",
     "Tier 1 Flag",
     "Applied to a judge whose pairwise B(j) test reaches p ≤ 0.01 significance. "
     "Indicates a statistically notable deviation from panel peers, warranting "
     "attention, but not meeting the threshold for removal under OSNR rules."),

    ("Tier 2 Flag",
     "Tier 2 Flag",
     "The most serious OSNR finding. Applied to a judge who simultaneously meets "
     "two criteria: (1) at least one pairwise B(j) result at p ≤ 0.001, AND "
     "(2) their LOJO removal would change the winner. A Tier 2 flag indicates "
     "the judge's presence is both statistically extreme and outcome-determinative. "
     "17 events in the database contain at least one Tier 2-flagged judge."),

    ("OSNR Status",
     "OSNR Status (per judge per event)",
     "A summary classification for each judge in each event: "
     "✅ No flag (judge scored within normal range), "
     "🟡 Tier 1 (p ≤ 0.01 pairwise significance), or "
     "🟠 Tier 2 (p ≤ 0.001 AND winner change — judge flagged for removal)."),

    # ── Regime comparison ────────────────────────────────────────────────────
    ("Regime",
     "Regime",
     "A scoring configuration used in the OSNR analysis. R0 is the official "
     "nine-judge result; R1 is after removing the most extreme judge; R2 is after "
     "removing a second judge. Comparing regimes reveals how sensitive outcomes "
     "are to individual judges."),

    ("Δ (Delta)",
     "Δ — Rank Change",
     "The difference in a skater's finishing position between two regimes. For "
     "example, R0 Δ shows how a skater's rank changes from the official result "
     "when the first judge is removed. A positive Δ means the skater ranked higher "
     "under that regime; negative means lower."),

    # ── Database / system metrics ────────────────────────────────────────────
    ("Unique Judges",
     "Unique Judges",
     "The number of distinct named judges appearing across all events in the "
     "database. The current database contains 1,278 unique judges."),

    ("Entries",
     "Entries",
     "The number of individual skater or team starting spots across all events "
     "in the database (2,637 total). One entry = one skater/team in one event."),

    ("OWG",
     "Olympic Winter Games (OWG)",
     "The Winter Olympic Games, held every four years. Figure skating events at "
     "the OWG carry the highest prestige in the sport. The database includes "
     "events from OWG 2022 (Beijing) and OWG 2026 (Milano Cortina)."),

    ("ISU",
     "International Skating Union (ISU)",
     "The international governing body for figure skating and speed skating, "
     "founded in 1892. The ISU sets the rules for IJS scoring, judge selection, "
     "and competition formats for all events in this database."),

    ("Grand Prix (GP)",
     "ISU Grand Prix of Figure Skating",
     "An annual series of six invitational competitions held in the fall, followed "
     "by the Grand Prix Final (GPF) for the top qualifiers. GP events are among "
     "the most important competitions outside the Olympic and World Championships."),

    ("Worlds",
     "ISU World Figure Skating Championships",
     "The annual world championship event, held each spring. Generally considered "
     "the most prestigious non-Olympic competition. Results determine ISU rankings "
     "and Olympic quota allocations."),

    ("4CC",
     "ISU Four Continents Figure Skating Championships",
     "An annual championship for skaters from the Americas, Africa, Asia, and "
     "Oceania (i.e., non-European countries). The European equivalent is the "
     "ISU European Figure Skating Championships."),

    # ── Table column terms (added from user review) ──────────────────────────

    ("R1 TSS",
     "Regime 1 Total Segment Score (R1 TSS)",
     "The recalculated Total Segment Score for each skater after removing the most "
     "extreme outlier judge from the panel (the first OSNR removal). Shown alongside "
     "R0 TSS in the Official Standings & Regime Comparison table for direct comparison."),

    ("R0 TSS",
     "Regime 0 Total Segment Score — Official (R0 TSS)",
     "The official, published Total Segment Score for each skater, calculated using "
     "all nine judges with the standard trimmed mean. This is the score that "
     "determines the actual competition result. Labelled R0 TSS in standings tables."),

    ("R0 Δ",
     "Regime 0 Rank Change (R0 Δ)",
     "The change in a skater's finishing rank when the first outlier judge is removed "
     "(i.e., comparing R1 standings to the official R0 standings). A positive value "
     "means the skater ranked higher under OSNR; negative means lower. Shown as R0 Δ "
     "in the Regime Comparison table."),

    ("R2 TSS",
     "Regime 2 Total Segment Score (R2 TSS)",
     "The recalculated Total Segment Score after a second judge removal. Used to "
     "assess whether a second outlier on the same panel also affected scores. "
     "Shown alongside R0 TSS and R1 TSS in the standings table."),

    ("R2 Δ",
     "Regime 2 Rank Change (R2 Δ)",
     "The change in a skater's finishing rank when the second outlier judge is also "
     "removed, compared to the official (R0) standings. Shown as R2 Δ in the "
     "Regime Comparison table."),

    ("R0 Rank",
     "Regime 0 Official Rank (R0 Rank)",
     "A skater's finishing position in the official results using all nine judges. "
     "Used as the reference rank in the Regime Comparison table when comparing "
     "outcomes across different judge-removal scenarios."),

    ("R0 Δ Rank",
     "Regime 0 Rank Change (R0 Δ Rank)",
     "The numeric difference between a skater's R1 rank (after first judge removal) "
     "and their official R0 rank. A non-zero value indicates the judge removal "
     "changed that skater's position. Displayed in the Regime Comparison tab."),

    ("R2 Rank",
     "Regime 2 Rank (R2 Rank)",
     "A skater's finishing position after both the first and second outlier judges "
     "have been removed from the panel. Shown in the Regime Comparison table for "
     "comparison with R0 Rank and R1 rank."),

    ("R2 Δ Rank",
     "Regime 2 Rank Change (R2 Δ Rank)",
     "The numeric difference between a skater's R2 rank (after both judge removals) "
     "and their official R0 rank. Indicates the cumulative effect of removing "
     "two outlier judges on that skater's standing."),

    ("LOJO Δ",
     "Leave-One-Judge-Out Result Change (LOJO Δ)",
     "Indicates whether removing a specific judge (via the LOJO simulation) would "
     "hypothetically change the winner. Displayed as YES (highlighted) or No. "
     "Important: LOJO Δ = YES reflects mathematical sensitivity — how close the "
     "result was — not bias. A judge can be the swing vote in a tight competition "
     "without having scored unusually. Actual judge removal under OSNR requires "
     "both LOJO Δ = YES and p ≤ 0.001 pairwise significance (Tier 2 flag). "
     "Shown in the Summary panel's judge table."),

    ("Winner Δ?",
     "Winner Change Flag (Winner Δ?)",
     "A per-judge flag shown in the Judge Statistics tab indicating whether removing "
     "that specific judge from the panel would change who finishes first. Displayed "
     "as YES (highlighted in orange) or No."),

    ("Element",
     "Technical Element (Element)",
     "A single scored technical move in a skating program — for example, a jump, "
     "spin, step sequence, lift, or twizzle. Each element is scored individually "
     "by each judge with a Grade of Execution (GOE). Shown in the Raw Scores table "
     "as the 'Element' column."),

    ("BV",
     "Base Value (BV)",
     "The predetermined point value assigned by the ISU to each technical element "
     "before GOE adjustments. Appears as 'BV' in the Raw Scores table. Higher-"
     "difficulty elements (e.g., a quad jump) have higher base values than "
     "lower-difficulty ones."),

    ("Panel GOE",
     "Panel Grade of Execution Average (Panel GOE)",
     "The trimmed-mean GOE for a given element, calculated across all nine judges "
     "after discarding the highest and lowest scores. Represents the panel's "
     "consensus quality assessment for that element. Shown as 'Panel GOE' in "
     "the Raw Scores table."),

    ("Elem Score",
     "Element Score (Elem Score)",
     "The total score awarded for a single technical element: Base Value + Panel "
     "GOE = Element Score. This is the actual points a skater receives for that "
     "element in the official result. Shown as 'Elem Score' in the Raw Scores table."),

    ("Max B(j)",
     "Maximum Pairwise B(j) Statistic (Max B(j))",
     "The largest absolute B(j) test statistic recorded for a judge across all "
     "pairwise comparisons with other judges in the same event. A higher Max B(j) "
     "indicates greater divergence from at least one other judge. Shown in the "
     "Judge Statistics and LOJO Summary tables."),

    ("Max B(j) vs",
     "Maximum B(j) Opponent (Max B(j) vs)",
     "The name of the skater or judge against whom the maximum B(j) statistic was "
     "recorded. Identifies which specific pairwise comparison produced the most "
     "extreme divergence for a given judge. Shown in the Judge Statistics table."),

    ("CF Winner",
     "Counterfactual Winner (CF Winner)",
     "The skater who would have won the event if a specific judge were removed from "
     "the panel, as determined by the LOJO simulation. When CF Winner differs from "
     "the actual winner, it indicates that judge's presence was outcome-determinative. "
     "Shown in the Summary highlights and LOJO Summary tables."),

    ("p-value",
     "p-value",
     "The probability of observing a test statistic as extreme as the one calculated, "
     "assuming no real difference exists between the two judges being compared. A "
     "smaller p-value indicates stronger evidence of a systematic scoring difference. "
     "Thresholds used in OSNR: p ≤ 0.05 (suggestive), p ≤ 0.01 (Tier 1 flag), "
     "p ≤ 0.001 (Tier 2 flag). Shown as 'p-value' in the Pairwise B(j) table."),

    ("Sig Level",
     "Significance Level (Sig Level)",
     "A categorical label summarising the p-value for a pairwise judge comparison. "
     "Displayed as 'Sig Level' in the Pairwise B(j) table with colour-coding: "
     "★★★ p ≤ 0.001 (most significant), ★★ p ≤ 0.01, ★ p ≤ 0.05, or blank "
     "if not significant. Corresponds to the Tier 1 / Tier 2 flag thresholds."),

    ("Direction",
     "Scoring Direction (Direction)",
     "Indicates which judge in a pairwise comparison scores higher relative to the "
     "other. 'B(j) > 0 (favors A)' means the judge scores Skater A higher than the "
     "comparison judge does; 'B(j) < 0 (favors B)' means the opposite. Used as a "
     "filter and display column in the Pairwise B(j) table."),

    ("Winner Changes",
     "Winner Changes",
     "The count of judges whose individual removal (via LOJO simulation) would "
     "hypothetically change the first-place finisher in an event. This measures "
     "how close the competition was at the top, not how many judges were biased. "
     "A value greater than zero becomes one of the two criteria for a Tier 2 flag "
     "(the other being p ≤ 0.001 pairwise significance). Shown in the LOJO Summary "
     "table and the Competitions page dashboard."),

    ("Podium Changes",
     "Podium Changes",
     "The count of judges whose removal would change any of the top three finishers "
     "(gold, silver, or bronze medalists) in an event. A broader measure of judge "
     "impact than Winner Changes. Shown in the LOJO Summary table and the "
     "Competitions page dashboard."),

    ("Rank Inversions",
     "Rank Inversions",
     "The number of pairs of skaters whose relative ranking would be swapped if a "
     "specific judge were removed from the panel. A higher count indicates the judge "
     "had a more pervasive effect on the ordering of skaters throughout the field, "
     "not just at the top. Shown in the LOJO Summary table."),
]


def page_glossary():
    st.title("Glossary")
    st.caption("Definitions of all terms used in the OSNR Figure Skating Judge Bias analysis system")
    st.divider()

    # Sort all terms alphabetically by abbreviation (case-insensitive)
    sorted_terms = sorted(GLOSSARY, key=lambda t: t[0].lstrip("Δ").strip().upper())

    for abbr, full, defn in sorted_terms:
        if abbr != full:
            label = f"**{abbr}** — {full}"
        else:
            label = f"**{abbr}**"
        with st.expander(label):
            st.write(defn)


# ════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════

def main():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found: `{DB_PATH}`")
        st.stop()

    page = render_sidebar()

    # Handle navigation from "Analyze" buttons (competition page → event analysis).
    # pop() here so render_sidebar() already used it to set active_idx correctly.
    if "goto_page" in st.session_state:
        page = st.session_state.pop("goto_page")
        # Push a new browser history entry so the back button returns here
        _set_page(page)

    if   page == "🏆  Competitions":      page_competitions()
    elif page == "📊  Event Analysis":    page_event_analysis()
    elif page == "👨‍⚖️  Judge Profiles":  page_judge_profiles()
    elif page == "📈  System-Wide Stats": page_system_stats()
    elif page == "📖  Glossary":          page_glossary()


if __name__ == "__main__":
    main()
