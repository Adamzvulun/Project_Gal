"""§4h trim — replace unmeasured claims with measured / qualified text.

Two paragraphs in the pristine source contain inflated, unmeasured
claims that the teacher flagged. Both are replaced in-place with
honest qualifications and a pointer to the §24 empirical evaluation
that actually measured something.
"""
from __future__ import annotations

from runs_builder import replace_paragraph_text


PARA_349 = (
    "המערכת ממומשת ב-כ-5,360 שורות פרודקשן (3,718 Python + 1,641 "
    "Java), עם **212 unit tests + ניסוי E2E עם peer-mock** ב-pytest. "
    "היא נבדקה על Linux (Ubuntu 22.04) ועל Windows 10. ביצועים אלגוריתמיים "
    "נמדדו ב-§24: ב-swarm סינתטי מקומי השלמת הורדה של 1 MB ב-כ-30 "
    "מילי-שניות עם 4 peers — מדידה שמתמקדת באלגוריתם בחירת "
    "ה-pieces (rarest-first מול random), לא ב-throughput במגה-בייט "
    "בשניה ב-swarm ציבורי."
)

PARA_579 = (
    "קצב הורדה תיאורטי: עד ניצולת מלאה של ה-bandwidth היוצא של "
    "ה-peers ב-swarm. **המערכת תוכננה לתמוך** ב-50 חיבורי TCP "
    "בו-זמנית (`MAX_CONNECTIONS=50`); הקצב הסופי תלוי ברוחב הפס "
    "של ה-peers ובמצב ה-swarm, ולא נמדד ב-swarm ציבורי. המדידה "
    "האלגוריתמית שכן בוצעה — בחירת pieces ב-swarm מקומי — מתועדת "
    "ב-§24."
)


REPLACEMENTS = {
    349: PARA_349,
    579: PARA_579,
}


def apply(body, snapshot, W):
    for idx, prose in REPLACEMENTS.items():
        replace_paragraph_text(snapshot[idx], prose)
