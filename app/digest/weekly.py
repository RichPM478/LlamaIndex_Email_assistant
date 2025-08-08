from datetime import datetime
from typing import Dict, Any, List
import re, dateparser

MONEY_RE = re.compile(r"(£\s?\d+(?:\.\d{1,2})?)", re.I)
DATE_HINTS = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday",
              "tomorrow","today","next","week","by","deadline"]
NEEDS_HINTS = ["bring","wear","payment","pay","permission","sign","submit","return","packed lunch","money"]

def extract_events_and_tasks(text: str, ref_dt: datetime) -> Dict[str, Any]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    events, tasks = [], []
    for ln in lines:
        low = ln.lower()
        has_dateish = any(h in low for h in DATE_HINTS)
        has_needs = any(h in low for h in NEEDS_HINTS)
        money = MONEY_RE.findall(ln)
        when = dateparser.parse(ln, settings={"RELATIVE_BASE": ref_dt, "PREFER_DATES_FROM":"future"})
        if has_dateish and when:
            events.append({"when": when.isoformat(), "line": ln})
        if has_needs or money:
            tasks.append({"what": ln, "money": money})
    return {"events": _dedupe(events), "tasks": _dedupe(tasks)}

def _dedupe(items: List[Dict[str, Any]]):
    seen, out = set(), []
    for it in items:
        k = it.get("line") or it.get("what")
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out
