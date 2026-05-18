"""§11.3 (OS processes / asyncio + Flask) — append honest-hazard paragraph.

The existing §11.3 already describes the threading model precisely.
What's missing per PLAN §4f is the *honest* disclosure of the one
remaining hazard: `_save_state` writes JSON synchronously from within
an async task. Adding one paragraph to call that out.
"""
from __future__ import annotations

from runs_builder import build_paragraph


PARA = (
    "**Hazard ידוע — disclosure.** קריאה אחת כן חוסמת את ה-event "
    "loop ב-hot path במידה תיאורטית: `_save_state` ב-"
    "`download_manager.py:765-794` כותב JSON סינכרונית מתוך "
    "task אסינכרוני (אין `await aiofiles.open` במימוש). על דיסק "
    "מהיר זה ~1ms; על דיסק איטי או network mount זה יכול להגיע "
    "ל-50ms+. ההקלה הקיימת בקוד: `_save_state` נקרא רק על "
    "**state transitions** (start, pause, complete, fail) — אירועים "
    "נדירים בקנה-מידה של פעם בעשרות שניות — ולא בכל handler של "
    "PIECE message. לכן ההשפעה היא ניתנת להזנחה בפועל, אבל "
    "הניהון הנכון לעתיד הוא העברה ל-thread pool דרך "
    "`loop.run_in_executor`, או החלפה ב-`aiofiles`."
)


INSERT_AFTER_IDX = 655  # last paragraph of §11.3 (GUI threads).


def apply(body, snapshot, W):
    anchor = snapshot[INSERT_AFTER_IDX]
    anchor.addnext(build_paragraph(PARA))
