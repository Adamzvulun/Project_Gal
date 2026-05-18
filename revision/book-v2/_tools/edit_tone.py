"""Tone-fix attribution sentences (PLAN §4a).

Adds a one-sentence attribution after §3.3, §7.1, and §7.2 H3 headings
so the algorithms are clearly framed as *implemented*, not *invented*.
This is the cheapest, lowest-risk fix for the "developed by student"
critique — no replacement of existing phrasing, just an inserted
paragraph that resets the framing.
"""
from __future__ import annotations

from runs_builder import build_paragraph


ATTRIBUTION_33 = (
    "אלגוריתמים אלה הוגדרו במקור על ידי Bram Cohen ב-2003 כחלק מ-"
    "BEP-3, ומשמשים כברירת מחדל בכל לקוח BitTorrent רציני (libtorrent, "
    "qBittorrent, Transmission, mainline). הפרויקט הזה **מממש** "
    "אותם, לא ממציא אותם מחדש; הדיון בהמשך מתמקד בבחירות המימוש "
    "ובפערים מתועדים מול הפרודקשן."
)

ATTRIBUTION_71 = (
    "rarest-first הוא חלק סטנדרטי של BEP-3 ומיושם בכל לקוח "
    "BitTorrent מודרני. התיאור הבא מתמקד בבחירות המימוש בפרויקט "
    "(`piece_manager.py:279-317`) ובמה שמומש או הושאר במכוון מחוץ "
    "לתחום — לא בשאלה האם rarest-first הוא רעיון מקורי."
)

ATTRIBUTION_72 = (
    "Tit-for-tat (choke/unchoke) הוא חלק סטנדרטי של BEP-3, הוצג "
    "ב-Cohen 2003, ומיושם ברוב מימושי הפרודקשן. התיאור הבא מתמקד "
    "בבחירות המימוש בפרויקט (`download_manager.py:_tit_for_tat_unchoke`) "
    "ובהרחבות הסטנדרטיות שנוספו: sliding window, snubbing, ומצב "
    "seeding — כל אחד מהם מתואר בסעיף נפרד בהמשך."
)


INSERT_AFTER = {
    78: ATTRIBUTION_33,    # H3 §3.3 — insert as first body paragraph
    174: ATTRIBUTION_71,   # H3 §7.1
    197: ATTRIBUTION_72,   # H3 §7.2
}


def apply(body, snapshot, W):
    for idx, prose in INSERT_AFTER.items():
        snapshot[idx].addnext(build_paragraph(prose))
