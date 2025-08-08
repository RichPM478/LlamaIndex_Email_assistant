from ics import Calendar, Event
from datetime import datetime
from typing import List, Dict
import uuid, os

def export_events_to_ics(events: List[Dict], out_path: str = "data/events.ics") -> str:
    c = Calendar()
    for e in events:
        ev = Event()
        ev.name = e.get("title") or "School Event"
        when = e.get("when")
        if isinstance(when, str):
            try:
                when = datetime.fromisoformat(when.replace("Z","+00:00"))
            except Exception:
                when = None
        if when:
            ev.begin = when
        ev.uid = e.get("uid") or str(uuid.uuid4())
        ev.description = e.get("description") or ""
        c.events.add(ev)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(c.serialize_iter())
    return out_path
