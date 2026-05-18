"""Humanize chapter §2 (תקציר / מבוא), body idx 345–375.

Replaces the prose of selected body paragraphs with humanized
versions. Headings and blank paragraphs are left alone. Inline code,
BEP-N references, §N section refs, numeric measurements, and citation
strings are preserved character-for-character.

Run from repo root:
    python3 revision/book-v2/_tools/humanize_ch02.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from docx_patcher import patch_docx, verify_non_document_identical  # noqa: E402
from runs_builder import replace_paragraph_text  # noqa: E402

DOCX = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


# idx -> humanized prose. Light-markdown: **bold**, `code`.
EDITS: dict[int, str] = {
    347: (
        "בעבודת הגמר הזו תכננתי ובניתי מערכת שיתוף קבצים מבוזרת בסגנון "
        "BitTorrent, שמממשת את פרוטוקול BitTorrent (BEP-3) משכבת התעבורה "
        "ועד לממשק המשתמש. המערכת נחלקת לשני רכיבים עצמאיים. מנוע רשת "
        "ב-Python מטפל בכל לוגיקת ה-P2P — פענוח Bencode, תקשורת tracker, "
        "חיבורי TCP ל-peers, בחירת pieces ואלגוריתמי choke/unchoke, "
        "אימות SHA-1 וניהול מצב. ממשק משתמש גרפי ב-Java Swing מתקשר איתו "
        "דרך REST API מקומי."
    ),
    348: (
        "הבעיה האלגוריתמית המרכזית היא לבחור piece ולבחור peer תחת אילוצי "
        "הרשת והפרוטוקול. מימשתי את שני האלגוריתמים הקלאסיים: rarest-first "
        "לבחירת piece, ו-Tit-for-Tat + Optimistic Unchoke לבחירת peer. "
        "כדי שאוכל להשוות מספרית, הוספתי גם baselines פשוטים (random, "
        "round-robin)."
    ),
    349: (
        "בסך הכל המערכת מסתכמת בכ-5,360 שורות פרודקשן (3,718 Python + "
        "1,641 Java), 212 unit tests, וניסוי E2E עם peer-mock ב-pytest. "
        "בדקתי אותה על Linux (Ubuntu 22.04) ועל Windows 10. את הביצועים "
        "האלגוריתמיים מדדתי ב-§24 — ב-swarm סינתטי מקומי, הורדה של 1 MB "
        "מסתיימת בכ-30 מילי-שניות עם 4 peers. המדידה מתמקדת באלגוריתם "
        "בחירת ה-pieces (rarest-first מול random), לא ב-throughput "
        "במגה-בייט בשניה ב-swarm ציבורי."
    ),
    351: (
        "שיתוף קבצים מבוזר עבר כמה גלגולים מאז סוף שנות ה-90. Napster "
        "(1999) הראה לראשונה שאפשר לעבוד P2P; Gnutella ו-Kazaa (2000–2003) "
        "ניסו לוותר על השרת המרכזי בכלל; ואז הגיע BitTorrent של Bram "
        "Cohen (2001) ופתר את השאלה שאף אחד לא הצליח לפתור לפניו — איך "
        "מתמרצים peers לתרום upload bandwidth כשאין מנגנון אכיפה. הפתרון "
        "של Cohen, Tit-for-Tat, הפך מאז לסטנדרט דה-פקטו, ועד היום "
        "BitTorrent הוא הפרוטוקול הדומיננטי לשיתוף קבצים פתוח."
    ),
    352: (
        "בחרתי לפתח את המערכת כי רציתי להבין מבפנים איך פרוטוקול P2P שלם "
        "עובד — לא רק לקרוא מאמרים עליו, אלא לממש אותו שורה אחרי שורה. "
        "בקריאה ראשונה הפרוטוקול נראה פשוט (BEP-3 הוא 30 עמודי טקסט), "
        "אבל בפועל הוא נוגע בכל מה שלמדתי: רשתות (TCP בלי HTTP), "
        "קריפטוגרפיה (SHA-1), אלגוריתמים (rarest-first, Tit-for-Tat), "
        "קונקורנציה (asyncio + thread pool) ואבטחה (אימות peer-by-peer)."
    ),
    354: (
        "התחלתי בקריאת ה-BEPs הרשמיים — BEP-3 (הפרוטוקול הליבה), BEP-23 "
        "(compact peer list), ו-BEP-5 (DHT, גם אם בסוף לא מימשתי אותו "
        "בפרויקט). משם עברתי למאמר של Cohen מ-2003, ולמאמר של Legout et "
        "al. מ-2006 שניתח אמפירית את הביצועים של rarest-first ושל choke "
        "algorithms."
    ),
    355: (
        "אחרי המאמרים פתחתי את הקוד של שלושה לקוחות פתוחים: qBittorrent "
        "(C++/Qt), Transmission (C) ו-libtorrent (C++). זה עזר לי להפריד "
        "בין דרישות הפרוטוקול לבין החלטות תכנון של המימוש הספציפי."
    ),
    359: (
        "שלושה מאמרים שימשו עוגן לעבודה: Cohen (2003) “Incentives Build "
        "Robustness in BitTorrent”, שממנו לקוח האלגוריתם המקורי של "
        "Tit-for-Tat; Legout et al. (IMC 2006) “Rarest First and Choke "
        "Algorithms Are Enough”, שמראה אמפירית ש-rarest-first יעיל פי "
        "1.5–2 מ-random; ו-Qiu & Srikant (SIGCOMM 2004) “Modeling and "
        "Performance Analysis of BitTorrent-Like P2P Networks”, שמציע "
        "מודל מתמטי לביצועי swarm. הרשימה המלאה בפרק 27."
    ),
    362: (
        "הבעיה האלגוריתמית המרכזית: איך לתאם הורדה של קובץ גדול מ-N peers "
        "בו-זמנית, כך שתהיה מהירה, חסכונית ב-bandwidth ועמידה ל-peers "
        "זדוניים או נופלים. היא מתחלקת לשלוש תתי-בעיות — איזה piece לבקש "
        "(rarest-first מול random), למי לפתוח choke (Tit-for-Tat מול "
        "round- robin), ואיך לאמת את התוכן (SHA-1 per piece)."
    ),
    364: (
        "בחרתי ב-BitTorrent כי הוא מאגד בתוכו את ארבעת התחומים שהכי "
        "מעניינים אותי: רשתות תקשורת (TCP, HTTP), אלגוריתמים (rarest-first, "
        "choke logic, תורת המשחקים), מערכות הפעלה (asyncio, thread pool) "
        "ואבטחת מידע (אימות SHA-1, מערכת מוניטין). פרויקט אחד שמרכז את "
        "כל מה שלמדתי בשנתיים האחרונות."
    ),
    366: (
        "רציתי להבין איך מערכת מבוזרת עובדת באמת, ולא רק לקרוא עליה. "
        "אחרי שנתיים של לימוד תאורטי של פרוטוקולים, חיפשתי הזדמנות לכתוב "
        "אחד שלם בעצמי, עם כל הפינות הלא נעימות — מה קורה כש-peer זדוני "
        "שולח SHA-1 שגוי, מה קורה כשה-event loop נחנק, ואיך מסדרים את "
        "זה בקוד."
    ),
    368: (
        "הפרויקט הוא בראש ובראשונה חינוכי, ואין לו שאיפה להתחרות "
        "ב-qBittorrent על features. אבל כן יש לו ערך אחד שלא קל למצוא "
        "בלקוחות מסחריים: אפשר להריץ איתו את אותו קובץ פעמיים, עם שני "
        "אלגוריתמים שונים (rarest-first מול random), ולמדוד את ההפרש "
        "בביצועים בצורה מבוקרת."
    ),
    370: "בדרך השוויתי לשלוש חלופות:",
    371: (
        "Client-server מרכזי (HTTP/CDN). פשוט, אבל יקר — כל המשתמשים "
        "נופלים על אותו שרת."
    ),
    372: (
        "Cloud distribution (S3, BunnyCDN). עובד טוב, אבל דורש תשלום "
        "per-bandwidth."
    ),
    373: (
        "P2P (BitTorrent). מתאים למטרה האקדמית של הפרויקט, ומחלק את "
        "העומס בין כל המשתתפים."
    ),
    374: "בחרתי בחלופה 3. הניתוח המלא בפרק 8.",
}


# Tokens we MUST preserve in every paragraph that we edit. Per-paragraph
# preserved tokens are the union of: backtick `code`, BEP-\d+, §\d+(\.\d+)?,
# פרק \d+, numeric literals followed by units (MB, KB, %, שניות, מילי-שניות,
# בייט, peers, unit tests), plus a small allowlist of named tokens
# (citation strings, algorithm names, languages).
NAMED_KEEP = (
    "BitTorrent", "Bencode", "tracker", "TCP", "Python", "Java", "Swing",
    "REST", "API", "rarest-first", "Tit-for-Tat", "Optimistic Unchoke",
    "choke", "unchoke", "random", "round-robin", "round- robin",
    "SHA-1", "Linux", "Ubuntu", "Windows", "pytest", "peer-mock",
    "throughput", "swarm", "Napster", "Gnutella", "Kazaa", "Bram",
    "Cohen", "P2P", "HTTP", "Legout", "et al.", "IMC", "Qiu", "Srikant",
    "SIGCOMM", "asyncio", "thread pool", "DHT", "compact peer list",
    "C++/Qt", "qBittorrent", "Transmission", "libtorrent",
    "“Incentives Build Robustness in BitTorrent”",
    "“Rarest First and Choke Algorithms Are Enough”",
    "“Modeling and Performance Analysis of BitTorrent-Like P2P Networks”",
    "BEP-3", "BEP-23", "BEP-5", "§24",
    "5,360", "3,718", "1,641", "212",
    "22.04", "1 MB", "30 מילי-שניות", "4 peers",
    "2003", "2006", "2004", "2001", "1999", "2000–2003",
    "1.5–2", "per-bandwidth",
    "S3", "BunnyCDN", "HTTP/CDN", "CDN",
    "פרק 27", "פרק 8", "peer-by-peer",
)


def text_of_p(p) -> str:
    return "".join((t.text or "") for t in p.iter(f"{{{W}}}t"))


def assert_preserved(old: str, new: str, idx: int) -> None:
    missing: list[str] = []
    for tok in NAMED_KEEP:
        if tok in old and tok not in new:
            missing.append(tok)
    # numeric tokens — find any \d+ in old that disappeared in new
    old_nums = set(re.findall(r"\d+(?:[.,]\d+)?", old))
    new_nums = set(re.findall(r"\d+(?:[.,]\d+)?", new))
    for n in old_nums - new_nums:
        missing.append(f"number:{n}")
    if missing:
        raise SystemExit(
            f"idx {idx}: token preservation failed; missing in new text: {missing}\n"
            f"  old: {old}\n  new: {new}"
        )


def edit_fn(root, body, W_ns):
    paras = list(body)
    for idx, new_prose in EDITS.items():
        p = paras[idx]
        if p.tag != f"{{{W_ns}}}p":
            raise SystemExit(f"idx {idx}: not a <w:p>, got {p.tag}")
        if p.find(f".//{{{W_ns}}}drawing") is not None:
            raise SystemExit(f"idx {idx}: image-bearing paragraph; refusing to edit")
        old_text = text_of_p(p)
        assert_preserved(old_text, new_prose, idx)
        replace_paragraph_text(p, new_prose)


def main() -> int:
    if not DOCX.exists():
        print(f"missing {DOCX}", file=sys.stderr)
        return 1
    tmp = DOCX.with_suffix(".docx.new")
    patch_docx(DOCX, tmp, edit_fn)

    # Non-document parts must be byte-identical with the source.
    ok, diffs = verify_non_document_identical(DOCX, tmp)
    if not ok:
        for d in diffs:
            print("  diff:", d)
        tmp.unlink(missing_ok=True)
        raise SystemExit("non-document parts changed; aborting")

    # Atomic replace.
    tmp.replace(DOCX)
    print(f"ok: {len(EDITS)} paragraphs humanized in §2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
