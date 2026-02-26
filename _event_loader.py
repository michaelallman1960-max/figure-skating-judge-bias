"""
_event_loader.py
================
Compatibility shim: load_event_data extracted from generate_event_report.py (archived).
Used by streamlit_app.py to load per-event data for display.

NOTE: load_event_data queries some v3-era tables (judge_event_statistics,
pairwise_judge_statistics) that may not exist in figure_skating_ijs_v4.sqlite.
Those queries will need updating in the full Streamlit app refactor (post-v2 sweep).
"""


def trimmed_mean(ints, drop=1):
    s = sorted(ints)
    trimmed = s[drop:len(s)-drop]
    return sum(trimmed)/len(trimmed) if trimmed else 0.0


def raw_mean(values):
    return sum(values)/len(values) if values else 0.0


def rank_by_tss(tss_map):
    sorted_items = sorted(tss_map.items(), key=lambda kv: kv[1], reverse=True)
    return {eid: i for i, (eid, _) in enumerate(sorted_items, 1)}


def load_event_data(conn, event_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT e.event_id, e.discipline, e.segment, e.level,
               e.scheduled_datetime_local, e.venue,
               c.name, c.season, c.location
        FROM events e JOIN competitions c ON e.competition_id=c.competition_id
        WHERE e.event_id=?
    """, (event_id,))
    ev = cur.fetchone()
    if not ev:
        raise ValueError(f"No event found with event_id={event_id}")
    event_info = {
        "event_id": ev[0], "discipline": ev[1], "segment": ev[2],
        "level": ev[3], "datetime_local": ev[4], "venue": ev[5],
        "competition_name": ev[6], "season": ev[7], "location": ev[8],
    }
    cur.execute("SELECT label_key,label_value FROM event_labels WHERE event_id=?", (event_id,))
    event_info["labels"] = dict(cur.fetchall())

    cur.execute("""SELECT judge_id,judge_position,judge_name,country_code
        FROM judges WHERE event_id=? ORDER BY judge_position""", (event_id,))
    judges = {}
    judge_id_to_pos = {}
    for jid, jpos, jname, jcc in cur.fetchall():
        judges[jpos] = {"id": jid, "name": jname or "", "country": jcc or ""}
        judge_id_to_pos[jid] = jpos
    judge_positions = sorted(judges.keys())

    # Tier 2 rule: flagged only if podium_changes > 0 AND sig001 > 0
    cur.execute("""
        SELECT les.judge_position, les.judge_name, les.judge_id
        FROM lojo_event_summary les
        JOIN (
            SELECT judge_position, SUM(is_significant_001) AS sig001
            FROM pairwise_judge_statistics
            WHERE event_id = ?
            GROUP BY judge_position
        ) pjs ON les.judge_position = pjs.judge_position
        WHERE les.event_id = ?
          AND les.podium_changes > 0
          AND pjs.sig001 > 0
        ORDER BY les.kendall_tau_distance DESC
        LIMIT 1
    """, (event_id, event_id))
    flagged_row = cur.fetchone()
    flagged_judge_pos = flagged_row[0] if flagged_row else None
    flagged_judge_id  = flagged_row[2] if flagged_row else None
    event_info["flagged_judge_pos"] = flagged_judge_pos
    event_info["flagged_judge_id"]  = flagged_judge_id

    cur.execute("""SELECT entry_id,start_no,team_name,noc,rank,tes,pcs,deductions,tss
        FROM entries WHERE event_id=? ORDER BY rank""", (event_id,))
    entries = []
    for row in cur.fetchall():
        eid, sno, tname, noc, rank, tes, pcs, ded, tss = row
        entries.append({
            "entry_id": eid, "start_no": sno, "team_name": tname,
            "noc": noc or "", "rank": rank,
            "tes_r1": round(tes, 2), "pcs_r1": round(pcs, 2),
            "deductions": ded or 0.0, "tss_r1": round(tss, 2),
        })

    for entry in entries:
        eid = entry["entry_id"]
        cur.execute("""SELECT element_id,element_no,element_code,base_value,panel_goe_points
            FROM elements WHERE entry_id=? ORDER BY element_no""", (eid,))
        elems_raw = cur.fetchall()
        elements = []
        for elem_id, elem_no, elem_code, bv, official_goe in elems_raw:
            cur.execute("""SELECT ejs.judge_id,j.judge_position,ejs.judge_goe_int
                FROM element_judge_scores ejs
                JOIN judges j ON ejs.judge_id=j.judge_id AND j.event_id=?
                WHERE ejs.element_id=? ORDER BY j.judge_position""", (event_id, elem_id))
            goe_by_pos = {}
            for g_jid, g_jpos, g_int in cur.fetchall():
                goe_by_pos[g_jpos] = {"judge_id": g_jid, "goe": g_int}
            all_ints = [goe_by_pos[jp]["goe"] for jp in judge_positions if jp in goe_by_pos]
            r1_trimmed = trimmed_mean(all_ints, drop=1)
            goe_increment = (official_goe / r1_trimmed) if r1_trimmed != 0 else 0.0
            r0_goe = round(raw_mean(all_ints) * goe_increment, 2)
            r1_goe = round(official_goe, 2)
            if flagged_judge_id:
                r2_ints = [goe_by_pos[jp]["goe"] for jp in judge_positions
                           if jp in goe_by_pos and goe_by_pos[jp]["judge_id"] != flagged_judge_id]
                r2_mean = trimmed_mean(r2_ints, drop=1) if len(r2_ints) >= 3 else raw_mean(r2_ints)
                r2_goe  = round(r2_mean * goe_increment, 2)
            else:
                r2_goe = r1_goe
            elements.append({
                "element_no": elem_no, "element_code": elem_code,
                "base_value": round(bv, 2), "goe_by_pos": goe_by_pos,
                "panel_goe_official": round(official_goe, 2),
                "r1_goe": r1_goe, "r1_elem": round(bv + r1_goe, 2),
                "r0_goe": r0_goe, "r0_elem": round(bv + r0_goe, 2),
                "r2_goe": r2_goe, "r2_elem": round(bv + r2_goe, 2),
            })
        entry["elements"] = elements

    for entry in entries:
        eid = entry["entry_id"]
        cur.execute("""SELECT pc.pcs_id,pc.factor FROM pcs_components pc
            WHERE pc.entry_id=? ORDER BY pc.component_name""", (eid,))
        pcs_rows = cur.fetchall()
        total_r0 = total_r2 = 0.0
        for pcs_id, factor in pcs_rows:
            cur.execute("""SELECT pjs.judge_id,pjs.judge_mark FROM pcs_judge_scores pjs
                WHERE pjs.pcs_id=? ORDER BY pjs.judge_id""", (pcs_id,))
            mark_rows = cur.fetchall()
            marks_all = [m for _, m in mark_rows]
            total_r0 += raw_mean(marks_all) * factor
            if flagged_judge_id:
                marks_r2 = [m for jid, m in mark_rows if jid != flagged_judge_id]
                r2_comp  = trimmed_mean(marks_r2, drop=1) if len(marks_r2) >= 3 else raw_mean(marks_r2)
            else:
                r2_comp = trimmed_mean(marks_all, drop=1)
            total_r2 += r2_comp * factor
        entry["pcs_r0"] = round(total_r0, 2)
        entry["pcs_r2"] = round(total_r2, 2)

    for entry in entries:
        ded = entry["deductions"]
        entry["tes_r0"] = round(sum(el["r0_elem"] for el in entry["elements"]), 2)
        entry["tes_r2"] = round(sum(el["r2_elem"] for el in entry["elements"]), 2)
        entry["tss_r0"] = round(entry["tes_r0"] + entry["pcs_r0"] + ded, 2)
        entry["tss_r2"] = round(entry["tes_r2"] + entry["pcs_r2"] + ded, 2)

    r0_ranks = rank_by_tss({e["entry_id"]: e["tss_r0"] for e in entries})
    r2_ranks = rank_by_tss({e["entry_id"]: e["tss_r2"] for e in entries})
    for entry in entries:
        entry["rank_r0"] = r0_ranks[entry["entry_id"]]
        entry["rank_r2"] = r2_ranks[entry["entry_id"]]

    cur.execute("""SELECT judge_id,judge_position,judge_name,n_entries,
               winner_changes,podium_changes,n_rank_inversions,total_pairs,
               kendall_tau_distance,actual_winner_name,cf_winner_name,actual_margin,cf_margin
        FROM lojo_event_summary WHERE event_id=? ORDER BY judge_position""", (event_id,))
    lojo_summary = {}
    for row in cur.fetchall():
        jid, jpos, jname, n_ent, wc, pc, nri, tp, ktd, aw, cfw, am, cfm = row
        lojo_summary[jpos] = {
            "judge_id": jid, "judge_name": jname,
            "winner_changes": wc, "podium_changes": pc,
            "n_rank_inversions": nri, "total_pairs": tp,
            "kendall_tau": ktd, "actual_winner": aw, "cf_winner": cfw,
            "actual_margin": am, "cf_margin": cfm,
        }

    cur.execute("""SELECT ls.judge_position,ls.entry_id,ls.cf_tss,ls.cf_rank,
               ls.official_rank,ls.rank_change
        FROM lojo_scores ls WHERE ls.event_id=? ORDER BY ls.judge_position,ls.official_rank""", (event_id,))
    lojo_scores = {}
    for row in cur.fetchall():
        jpos, eid, cf_tss, cf_rank, off_rank, rchg = row
        if jpos not in lojo_scores:
            lojo_scores[jpos] = {}
        lojo_scores[jpos][eid] = {"cf_tss": cf_tss, "cf_rank": cf_rank,
                                   "official_rank": off_rank, "rank_change": rchg}

    cur.execute("""SELECT judge_id,judge_position,judge_name,judge_country,
               mean_goe_deviation,bias_z_score,correlation_with_panel,outlier_count
        FROM judge_event_statistics WHERE event_id=? ORDER BY judge_position""", (event_id,))
    judge_stats = {}
    for row in cur.fetchall():
        jid, jpos, jname, jcc, mgd, bz, corr, oc = row
        judge_stats[jpos] = {"judge_id": jid, "name": jname, "country": jcc or "",
                              "mean_goe_dev": mgd, "bias_z": bz,
                              "correlation": corr, "outlier_count": oc}

    cur.execute("""SELECT judge_position,judge_id,
               SUM(is_significant_01),SUM(is_significant_001),MAX(bias_statistic)
        FROM pairwise_judge_statistics WHERE event_id=? GROUP BY judge_id ORDER BY judge_position""", (event_id,))
    pairwise_agg = {}
    for row in cur.fetchall():
        jpos, jid, s01, s001, maxb = row
        pairwise_agg[jpos] = {"sig01": s01 or 0, "sig001": s001 or 0, "max_bias": maxb or 0}

    cur.execute("""SELECT p1.judge_position,p1.skater_a_name,p1.skater_b_name,p1.bias_statistic
        FROM pairwise_judge_statistics p1
        WHERE p1.event_id=? AND p1.bias_statistic=(
            SELECT MAX(p2.bias_statistic) FROM pairwise_judge_statistics p2
            WHERE p2.event_id=? AND p2.judge_id=p1.judge_id)
        ORDER BY p1.judge_position""", (event_id, event_id))
    max_bias_rows = {}
    for row in cur.fetchall():
        jpos, sa, sb, bs = row
        if jpos not in max_bias_rows:
            max_bias_rows[jpos] = {"skater_a": sa, "skater_b": sb, "bias": bs}

    cur.execute("""SELECT judge_position,judge_name,judge_country,
               skater_a_name,skater_a_country,skater_a_rank,
               skater_b_name,skater_b_country,skater_b_rank,
               bias_statistic,p_value,is_significant_01,is_significant_001,is_significant_bonferroni,
               mean_deviation_a,mean_deviation_b,differential,num_elements_a,num_elements_b
        FROM pairwise_judge_statistics WHERE event_id=? AND p_value<=0.10
        ORDER BY p_value ASC""", (event_id,))
    pairwise_rows = cur.fetchall()

    cur.execute("""SELECT COUNT(*),SUM(is_significant_01),SUM(is_significant_001),SUM(is_significant_bonferroni)
        FROM pairwise_judge_statistics WHERE event_id=?""", (event_id,))
    pw_totals = cur.fetchone()

    return {
        "event_info": event_info, "judges": judges, "judge_positions": judge_positions,
        "judge_id_to_pos": judge_id_to_pos, "entries": entries,
        "lojo_summary": lojo_summary, "lojo_scores": lojo_scores,
        "judge_stats": judge_stats, "pairwise_agg": pairwise_agg,
        "max_bias_rows": max_bias_rows, "pairwise_rows": pairwise_rows, "pw_totals": pw_totals,
    }
