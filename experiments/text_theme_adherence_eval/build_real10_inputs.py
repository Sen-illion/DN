#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

BASELINE_DIR = Path(r"D:\DN-main\experiments\baseline_integration\normalized_runs\doc_yunwu\formal20_first_playable_20260430_complete")
DN_RUN_JSON = Path(r"D:\DN-main\experiments\benchmark\standard_runs\benchmark_v16_pregendepth_d1_turn4_rw60_formal20.json")
OUT_DIR = Path(r"D:\embedding_eval_outputs\real10_inputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_baseline_items() -> dict[str, dict]:
    items = {}
    for p in sorted(BASELINE_DIR.glob("item_*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        bid = data.get("benchmark_id")
        if not bid:
            continue
        theme = data.get("input_bundle", {}).get("original_dn_item", {}).get("theme", "")
        nr = data.get("normalized_response", {})
        # Build a plain text that represents baseline first playable response.
        parts = [
            str(nr.get("scene_setup", "")).strip(),
            str(nr.get("player_state", "")).strip(),
            str(nr.get("narrative_response", "")).strip(),
        ]
        actions = nr.get("candidate_actions", [])
        if isinstance(actions, list) and actions:
            parts.append("选项：" + "；".join(str(x).strip() for x in actions if str(x).strip()))
        nxt = str(nr.get("suggested_next_step", "")).strip()
        if nxt:
            parts.append("下一步：" + nxt)
        text = "\n".join([x for x in parts if x])
        items[bid] = {"id": bid, "theme": theme, "text": text}
    return items


def load_dn_runs() -> tuple[dict[str, dict], list[str]]:
    data = json.loads(DN_RUN_JSON.read_text(encoding="utf-8"))
    runs = data.get("runs", [])
    by_id = {}
    ordered_ids = []
    for r in runs:
        bid = r.get("benchmark_id")
        if not bid:
            continue
        theme = r.get("theme", "")
        turns = r.get("turns", [])
        text = ""
        if turns:
            t1 = turns[0]
            text = (
                t1.get("click", {})
                .get("response_json", {})
                .get("optionData", {})
                .get("scene", "")
            )
            if not text:
                text = (
                    t1.get("click", {})
                    .get("response_json", {})
                    .get("optionData", {})
                    .get("checkpoint_packet", {})
                    .get("recap_text", "")
                )
            if not text:
                text = str(t1.get("previousSceneText", ""))
        by_id[bid] = {"id": bid, "theme": theme, "text": str(text).strip()}
        ordered_ids.append(bid)
    return by_id, ordered_ids


def sort_key(bid: str):
    # DNQBV1_001 -> 1
    try:
        return int(bid.split("_")[-1])
    except Exception:
        return 10**9


def main() -> None:
    baseline = load_baseline_items()
    dn, dn_order = load_dn_runs()

    common_ids = sorted(set(baseline).intersection(dn), key=sort_key)
    selected_ids = common_ids[:10]

    if len(selected_ids) < 10:
        raise RuntimeError(f"Only found {len(selected_ids)} common ids, expected at least 10")

    theme_rows = []
    baseline_rows = []
    dn_rows = []

    for bid in selected_ids:
        theme = baseline[bid]["theme"] or dn[bid]["theme"]
        theme_rows.append({"id": bid, "theme": theme})
        baseline_rows.append({"id": bid, "text": baseline[bid]["text"]})
        dn_rows.append({"id": bid, "text": dn[bid]["text"]})

    theme_df = pd.DataFrame(theme_rows)
    baseline_df = pd.DataFrame(baseline_rows)
    dn_df = pd.DataFrame(dn_rows)

    theme_csv = OUT_DIR / "themes_real10.csv"
    baseline_csv = OUT_DIR / "texts_baseline_real10.csv"
    dn_csv = OUT_DIR / "texts_dn_real10.csv"

    theme_df.to_csv(theme_csv, index=False, encoding="utf-8-sig")
    baseline_df.to_csv(baseline_csv, index=False, encoding="utf-8-sig")
    dn_df.to_csv(dn_csv, index=False, encoding="utf-8-sig")

    selected_set = set(selected_ids)
    neg_candidates = []
    for bid in sorted(dn.keys(), key=sort_key):
        if bid in selected_set:
            continue
        t = str(dn[bid]["theme"]).strip()
        if t and t not in neg_candidates:
            neg_candidates.append(t)
        if len(neg_candidates) >= 5:
            break

    if len(neg_candidates) < 3:
        # fallback from all themes
        for rec in dn.values():
            t = str(rec["theme"]).strip()
            if t and t not in neg_candidates and t not in theme_df["theme"].tolist():
                neg_candidates.append(t)
            if len(neg_candidates) >= 3:
                break

    if len(neg_candidates) < 3:
        raise RuntimeError("Failed to collect at least 3 negative themes")

    neg_file = OUT_DIR / "negative_themes_real10.txt"
    neg_file.write_text("\n".join(neg_candidates), encoding="utf-8")

    meta = {
        "selected_ids": selected_ids,
        "negative_themes": neg_candidates,
        "theme_csv": str(theme_csv),
        "baseline_csv": str(baseline_csv),
        "dn_csv": str(dn_csv),
        "neg_file": str(neg_file),
    }
    (OUT_DIR / "prepare_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
