# Draft — §25 (מסקנות) + §26 (פיתוחים עתידיים)

Closes Step 3 of `revision/PLAN.md`: the `_load_state` admission is no
longer factually true (code shipped on 4a/4b/4c branches), so the book
must (a) move auto-resume from "didn't work" to "what works", and
(b) remove it from the future-work backlog.

Source body indices (from pristine `docs/ספר פרוייקט אדם זבולון.docx`):

* §25 H1 at 1337, body 1338–1349 (12 insights + "what didn't work")
* §26 H1 at 1350, subsections through 1378

## (A) §25 — insert a new insight paragraph AFTER idx 1348 ("Type hints")

> שחזור מצב הוא יותר מ-JSON dump. הגרסה הראשונה של `_save_state` כתבה
> JSON מינימלי — ב-restart, `_load_state` היה נכשל בלי המידע שדרוש
> לשחזור: `Download.__init__` זקוק ל-`TorrentMetadata` מלא,
> ל-`download_dir`, ולשמות האלגוריתמים. הפתרון: sidecar
> `{id}.torrent` (re-encoded דרך `bencode.encode` קנוני) ושלושה שדות
> חדשים ב-JSON. וחשוב יותר — ה-restore מאמת מחדש כל piece שה-JSON
> מסמן כ-COMPLETED, על ידי קריאת ה-bytes מהדיסק והרצת
> `Piece.verify_hash`. ה-JSON הוא רמז למה שהיה נכון בעת השמירה, לא
> האמת על מה שעל הדיסק עכשיו — הקובץ יכול להשתנות בין הפעלות.
> ראה `Download.from_state_file` ו-`DownloadManager.restore_state`
> ב-`download_manager.py`.

Voice match notes: this insight follows the same shape as the
neighbouring §25 paragraphs ("X is more than Y. The first version...
The fix..."). Cites the code surface (`Download.from_state_file`,
`DownloadManager.restore_state`) so the oral examiner can drill down.

## (B) §25 — replace idx 1349 ("מה לא הצליח") to drop the auto-resume admission

> מה לא הצליח: NAT traversal לא מומש — המערכת לא מקבלת חיבורים
> נכנסים. ו-MSE/PE לא מומש — אין הצפנה בערוץ peers. שני הפערים
> מתועדים בפרק 26.

Three failures dropped to two. Auto-resume is now in the "what worked"
list above (paragraph A).

## (C) §26 — delete idx 1363 (the "שחזור אוטומטי לאחר crash" future-work item)

The entire paragraph is removed. The neighbouring entries under
"חוויית משתמש" (algorithm switching, preview, dark mode, shortcuts)
stay.

## (D) §26 — replace idx 1377 ("סדר עדיפויות מומלץ") to drop "auto-resume + "

> חודש 1: incoming server + NAT traversal. חודש 2: algorithm
> switching + single executable. חודש 3: DHT + PEX. חודש 4: MSE/PE
> + BEP-52. חודש 5+: UX polish, performance, operations.

Month 2 had three items; now two.

## Image preservation

No image-bearing paragraphs in the §25/§26 region per the structure
map (image paragraphs are concentrated around §15 and §17). Edit is
text-only.
