"""Attribution framing — single paragraph at the start of book §6.2.

The teacher's critique was that the book frames standard BitTorrent
algorithms as if they were "developed by the student". The book's
existing §6.1 and §6.2 do cite Cohen 2003 historically but do not
state explicitly that this project IMPLEMENTS rather than INVENTS.
This pass adds one framing paragraph immediately after the §6.2 H2
heading, before the existing "אלגוריתמי בחירת piece" content.
"""
from __future__ import annotations

from runs_builder import build_paragraph


PARA = (
    "**הערת מסגרת.** האלגוריתמים שמתוארים בסעיף זה ובהמשך — "
    "rarest-first, choke/unchoke (tit-for-tat), ופרוטוקול pull-based — "
    "הוגדרו על ידי Bram Cohen ב-2003 כחלק מ-BEP-3, ומיושמים בכל "
    "לקוח BitTorrent רציני (libtorrent, qBittorrent, Transmission, "
    "Deluge, mainline). הפרויקט הזה **מממש** אותם, לא ממציא אותם "
    "מחדש; הניתוחים בהמשך (§15.4 ותתי-סעיפיו) מתמקדים בבחירות "
    "המימוש בפועל ובהרחבות סטנדרטיות שנוספו (sliding window, "
    "snubbing, seeding mode) — לא בשאלה האם האלגוריתמים עצמם הם "
    "המצאה מקורית."
)


INSERT_AFTER_IDX = 453  # book §6.2 H2 — pristine source index.


def apply(body, snapshot, W):
    snapshot[INSERT_AFTER_IDX].addnext(build_paragraph(PARA))
