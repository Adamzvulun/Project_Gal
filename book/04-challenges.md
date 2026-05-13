# פרק 4 – אתגרים

## פתיח

פרק זה מציג את האתגרים ההנדסיים שעמדו בפני הסטודנט במהלך תכנון
ופיתוח הפרויקט, ואת ההכרעות הטכניות שהתקבלו בעקבותיהם. בעוד שפרק 2
(תקציר/מבוא) ציין את האתגרים ברמת הסקירה, פרק זה צולל לתיאור
**טכני, מפורט וקונקרטי** של כל אתגר — מקור הקושי, הניסיונות
הראשוניים, השורש העמוק של הבעיה, וההכרעה שהובילה לפתרון. רבים
מהאתגרים מוצגים יחד עם הפניות לקטעי קוד בפרק 21 ובנספח א'.

האתגרים מאורגנים בארבעה צירים: **אתגרי פרוטוקול וקידוד** (4.1),
**אתגרי אלגוריתמיקה ויעילות** (4.2), **אתגרי קונקורנציה ותהליכי
מערכת הפעלה** (4.3), ו**אתגרי אינטגרציה רב-לשונית ואבטחה** (4.4).
האתגר המרכזי שהשפיע על האדריכלות הסופית — **באג ההתקעות
(*Download Stalling*)** — מקבל סעיף נפרד (4.5) שכן הוא איגד בתוכו
כמה אתגרים שזורים זה בזה והוביל לחשיבה מחדש על מספר רכיבים.

---

## 4.1 אתגרי פרוטוקול וקידוד

### 4.1.1 אכיפת מבנה Bencode בקפדנות ביטים

פורמט Bencode (RFC משוער של BitTorrent) הוא קידוד פשוט יחסית
מבחינת *תחביר* — ארבעה טיפוסים בלבד: integer (`i123e`), byte string
(`4:spam`), list (`l...e`) ו-dictionary (`d...e`). הקושי אינו
בתחביר אלא ב**מוסכמות הקנונית** המחייבות:

- מפתחות במילון חייבים להיות **ממוינים לקסיקוגרפית כ-byte-strings**.
- מספרים שלמים לא יכולים לכלול **אפס מוביל** (`i03e` אסור).
- מספרים שליליים לא יכולים להיות **"מינוס אפס"** (`i-0e` אסור).
- מחרוזות הן **בייטים גולמיים**, לא Unicode.

הקושי: שגיאה במוסכמה כלשהי תוביל ל-`info_hash` שונה, ובעקבות זאת
ה-tracker יחזיר רשימת peers ריקה ללא הודעת שגיאה ברורה. ההשפעה
שקטה לחלוטין — המערכת תרוץ ותתחבר, אך פשוט לא תקבל peers.

**ההכרעה**: לכפות במימוש של `bencode.py` את המוסכמות הקנוניות
**בשכבת ה-encoder**, ובדיקת decoder שמסרבת לקלוט קידוד לא-קנוני
(ולא מסתפקת בלקבל "מה שעבד"). מצורפת קבוצת בדיקות יחידה רחבה
ב-`tests/test_bencode.py` הכוללת בדיקות *round-trip* ובדיקות לדחיית
קלט פגום.

### 4.1.2 חישוב info_hash מעל מילון `info` המקודד מחדש

ה-`info_hash` הוא SHA-1 על **קידוד ה-Bencode של מילון ה-`info`
בלבד**, לא על קובץ ה-`.torrent` כולו. הקושי כפול:

1. צריך לקדד מחדש את מילון ה-`info` לפורמט קנוני — לא ניתן פשוט
   "לחתוך" את המקור מהקובץ. (במקרה של מילון לא-קנוני בקובץ המקור,
   חישוב מחדש ייתן info_hash שונה מזה שה-tracker מצפה.)
2. ההצפנה היא על בייטים גולמיים — לא על מחרוזת Unicode.

הקושי הזה גרם בשלב מוקדם של הפיתוח לחיבור מוצלח ל-tracker אך
לקבלת רשימת peers ריקה. אבחון לקח זמן מכיוון שאין שגיאת רשת — רק
התנהגות שקטה שגויה.

**ההכרעה**: ב-`torrent_metadata.py`, מבנה ה-`info` שמור כ-`dict`
פייתוני שלם, מקודד מחדש על-ידי `bencode.encode()` כשנדרש, ועליו
מחושב SHA-1. בדיקת יחידה ב-`tests/test_torrent_metadata.py` משווה
את ה-`info_hash` המחושב לערך ידוע מקבצי `.torrent` בעלי
`info_hash` מתועד.

### 4.1.3 וולידציה של Peer Wire Protocol — state machine מלא

הפרוטוקול בין peers הוא **state machine**: אסור לשלוח `request`
לפני `unchoke` ולפני `interested`; אסור לשלוח `piece` שלא התבקש;
אסור לשלוח `have` בלי שהושלם piece בפועל. peers מציאותיים — בעיקר
שכאלה הרצים לקוחות ישנים או מימושים חובבניים — עלולים להפר את
ה-state machine מבלי לציין זאת.

הקושי: אכיפה רכה מדי תאפשר ל-peer לזרוק את המערכת. אכיפה קשה מדי
תנתק peers תקינים על "טעויות זניחות".

**ההכרעה**: מימוש של רף אכיפה שונה לסוגי הפרות שונים:

- **הפרות שגרתיות** (למשל `piece` עבור block שלא ביקשנו) — שמירת
  count, אך לא ניתוק מיידי.
- **הפרות חמורות** (handshake לא תקין, `length` חורג, הודעה גדולה
  מ-2MB) — ניתוק מיידי וסימון peer כ-banned.
- **הפרות חוזרות** (חציית סף `MAX_PROTOCOL_VIOLATIONS_PER_PEER=5`)
  — ניתוק וחסימה.

הקוד ב-`security.py` בשילוב עם הוולידציות ב-`peer_connection.py`
מממש את הלוגיקה. ראה גם פרק 12 לפירוט מלא של מודל האיום.

---

## 4.2 אתגרי אלגוריתמיקה ויעילות

### 4.2.1 בחירת piece מתוך קבוצה נדירה — מבנה נתונים מתאים

מימוש נאיבי של rarest-first הוא `O(n)` בכל בחירה: לעבור על כל
ה-pieces, לחשב את המינימום של `peer_frequency`, ולסנן את הקבוצה.
עבור torrents גדולים (אלפי pieces), זה מהיר מספיק (זמן הבחירה זניח
ביחס לזמן ההורדה של בלוק), אך מציב שאלה: **מה לבחור בתוך הקבוצה?**

בחירה דטרמיניסטית (תמיד הראשון) יוצרת תופעה של *piece convergence*
— כל ה-peers ב-swarm בוחרים את אותו piece, מקבלים בלוקים זהים, ולא
מצליחים להעלות חזרה אחד לשני (כי לכולם יש את אותם הבלוקים). בחירה
אקראית מתוך הקבוצה הנדירה ביותר פותרת את הבעיה אבל מציבה אתגר:
**ההגרלה חייבת להיות שוויונית בתוך הקבוצה ולא מוטה לכיוון
pieces "פופולריים" שבכל זאת נכנסו לקבוצה ההנדירה.**

**ההכרעה**: ב-`piece_manager.py`, פונקציית `select_piece_rarest_first`
מבצעת:

```python
# python_engine/piece_manager.py (קצור)
min_freq = min(self._peer_frequency[i] for i in candidates)
rarest_set = [i for i in candidates
              if self._peer_frequency[i] == min_freq]
return random.choice(rarest_set) if rarest_set else None
```

קטע הקוד מציג את עקרון "מינימום + הגרלה". סיבוכיות סופית `O(n)`
לבחירה, וזיכרון `O(n)` למילון התדירויות. הקטע המלא של הפונקציה
מופיע בנספח א.4 עם תיעוד תיק היחידה שלה.

### 4.2.2 איזון בין pipelining לעצימות זיכרון

ה-spec מגדיר ש-peer יכול לבקש בלוקים מ-peer יריב במקביל
(*pipelining*) — אבל לא מגדיר כמה. רוב הלקוחות המסחריים מאפשרים
5–10 בקשות מקבילות לכל peer. במימוש הראשוני שלנו ה-מצב היה זהה:
`MAX_PENDING_REQUESTS=10`.

הקושי: בקצב ההורדה במציאות, 10 בקשות בלוקים (כ-160KB) מתמלאות
תוך עשירית שנייה ב-peer מהיר. לאחר מכן נוצרת **rate-limit
מלאכותית** — אנחנו מחכים לבלוק להגיע לפני שמבקשים את הבא. רוחב
הפס של הקו אינו מנוצל.

**ההכרעה**: לאחר ניסויים, הוגדל `MAX_PENDING_REQUESTS=50`. ערך זה
מאפשר לקו רוחב פס של ~10 Mbps לרוץ במלואו, ובכל זאת אינו צורך
זיכרון מוגזם (50 בלוקים × 16KB = 800KB לכל peer × 50 peers ≤ 40MB
זיכרון מקסימלי). ראה ערכי קונפיגורציה ב-`peer_connection.py`:

```python
# python_engine/peer_connection.py (קצור)
BLOCK_SIZE = 16384            # 16KB per block (BEP-3)
MAX_PENDING_REQUESTS = 50     # pipeline depth per peer
CONNECTION_TIMEOUT = 30
REQUEST_TIMEOUT = 60
MAX_MESSAGE_SIZE = 2 * 1024 * 1024
```

### 4.2.3 ניהול תור בקשות שבוטלו (Block Request Tracking)

בלוק שנשלחה לו `request` ל-peer A יכול "להיתקע" אם A מנותק או
חונק אותנו. מימוש נאיבי משאיר את הבלוק "תפוס" — אף peer אחר אינו
מבקש אותו, וההורדה נתקעת. מימוש "לוותר ולבקש מ-B" יוצר בעיה אחרת:
A עדיין עלול להחזיר את הבלוק, וכעת יש לנו אותם נתונים פעמיים.

**ההכרעה**: ב-`piece_manager.py`, מבנה ה-`Block` שומר ארבעה שדות:
`requested` (האם נשלחה בקשה), `requested_time` (מתי), `requested_by`
(איזה peer), ו-`BLOCK_REQUEST_TIMEOUT=10` (אחרי כמה שניות הבלוק
"חוזר לחיים"). אחרי 10 שניות ללא תגובה, הבלוק זמין שוב לבקשה —
ועליה אנו מסתמכים ב-*endgame mode* (השלמת piece קרוב לסיומו).
דוגמת קוד:

```python
# python_engine/piece_manager.py (קצור)
@property
def is_requestable(self) -> bool:
    if self.received:
        return False
    if not self.requested:
        return True
    elapsed = time.time() - (self.requested_time or 0)
    return elapsed > BLOCK_REQUEST_TIMEOUT  # 10 seconds
```

האלגוריתם הזה לבדו אינו מספיק — הוא חלק מהפתרון הכולל של באג
ההתקעות (סעיף 4.5).

---

## 4.3 אתגרי קונקורנציה ותהליכי מערכת הפעלה

### 4.3.1 מעבר מ-blocking ל-asyncio

הבחירה הראשונית הייתה ב-`threading` עם תהליך לכל peer. עם 50 peers,
זה הוביל לעומס context-switching עצום על מערכת ההפעלה, ול-overhead
זיכרון של מספר MB לכל thread (stack). בנוסף, סנכרון בין threads
חייב mutex-ים מרובים, וכל שגיאת סנכרון יוצרת *race condition*
שקשה לאתר.

**ההכרעה**: מעבר ל-`asyncio` — event loop יחיד, חיבורי TCP
לא-חוסמים (`asyncio.open_connection`), והודעות מטופלות
ב-`async def _message_loop()` לכל peer. דוגמת קוד:

```python
# python_engine/peer_connection.py (קצור)
async def _message_loop(self) -> None:
    while self.connected:
        try:
            msg = await self._read_message()
            if msg is None:
                break
            self._handle_message(msg)
            if self.on_message:
                await self.on_message(self, msg)
        except (asyncio.CancelledError, ConnectionError):
            break
```

הקטע מציג את הלולאה האסינכרונית המטפלת בהודעות מ-peer יחיד. הגרסה
המלאה ראויה לעיון בנספח א.3.

### 4.3.2 הוצאת פעולות "כבדות" מ-event loop

האתגר הבא נחשף בעת בדיקות ביצועים: ההורדה הואטה דרמטית בכל הגעת
piece שלם. הסיבה הייתה שני סוגי פעולות החוסמים את ה-event loop:

1. **חישוב SHA-1** של piece שלם (256KB) — לוקח עשרות מילישניות.
2. **כתיבה לדיסק** של piece — לוקחת מילישניות עד עשרות מילישניות.

כאשר פעולות אלה רצות ב-event loop, הן מקפיאות את **כל** ה-peers
האחרים, חוסמות את ה-`_message_loop` שלהם, וגורמות להם להפסיק לקבל
נתונים. במצבים קיצוניים — לניתוק חיבורים על *timeout*.

**ההכרעה**: שילוב `concurrent.futures.ThreadPoolExecutor(2)`
המבצע את הפעולות הכבדות **מחוץ ל-event loop**. דוגמת קוד:

```python
# python_engine/download_manager.py (קצור)
self._executor = ThreadPoolExecutor(max_workers=2)
loop = asyncio.get_event_loop()

# Heavy work pushed to threads
hash_ok = await loop.run_in_executor(
    self._executor, self.piece_manager.verify_piece, piece_idx)
if hash_ok:
    await loop.run_in_executor(
        self._executor, self._write_piece_sync, piece_idx)
```

הקטע מציג איך פעולות `verify_piece` ו-`_write_piece_sync` מועברות
לשרשור נפרד באמצעות `run_in_executor`, כך שה-event loop נשאר חופשי
לטיפול ב-I/O רשת.

### 4.3.3 תיאום Flask Thread עם Asyncio Event Loop

Flask, ברירת המחדל של ה-API שלי, רץ ב-thread סינכרוני; asyncio
event loop רץ ב-thread נפרד. כל פעולה ש-Flask מקבל (`POST /torrents`
למשל) חייבת בסופו של דבר להפעיל קוראוטינה ב-event loop, ולחכות
לתוצאה.

הניסיון הראשון היה להשתמש ב-`asyncio.run()` בכל handler של Flask —
אך זה יוצר **event loop חדש בכל בקשה**, וההורדות הקיימות (שרצות
על event loop הקבוע) לא מסונכרנות איתו.

**ההכרעה**: יצירה של event loop קבוע ויחיד ב-thread daemon נפרד
בעת אתחול האפליקציה, ושימוש ב-`asyncio.run_coroutine_threadsafe()`
לשליחת קוראוטינות אליו מ-Flask:

```python
# python_engine/api_server.py (קצור)
_loop = asyncio.new_event_loop()
_thread = threading.Thread(target=_loop.run_forever, daemon=True)
_thread.start()

def _run_async(coro, timeout: float = 60.0):
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)
```

`_run_async` היא הפונקציה היחידה שדרכה Flask מדבר עם המנוע
האסינכרוני, ועם timeout מובנה למניעת התקעות.

---

## 4.4 אתגרי אינטגרציה רב-לשונית ואבטחה

### 4.4.1 העברת נתונים בינאריים מ-Java ל-Python

קובץ `.torrent` הוא **בינארי גולמי**. ה-GUI ב-Java צריך להעלות
אותו לשרת Python דרך HTTP. ה-API הוא `POST /torrents`, וצריך
להעביר גם את הקובץ וגם פרמטרים נוספים (תיקיית הורדה, אלגוריתמים).

הניסיון הראשון היה `application/json` עם base64 encoding של
הקובץ — אך זה מנפח את הנתונים ב-33%, ויוצר תלות בהמרות שגויות.

**ההכרעה**: שימוש ב-`multipart/form-data` — סטנדרט HTTP מוכר שתומך
בבייטים גולמיים יחד עם פרמטרים טקסטואליים. ב-Java:

```java
// java_gui/src/ApiService.java (קצור)
String boundary = "----TorrentBoundary" + System.currentTimeMillis();
ByteArrayOutputStream baos = new ByteArrayOutputStream();
baos.write(("--" + boundary + "\r\n").getBytes());
baos.write(("Content-Disposition: form-data; name=\"file\"; " +
            "filename=\"" + file.getName() + "\"\r\n").getBytes());
baos.write("Content-Type: application/x-bittorrent\r\n\r\n".getBytes());
baos.write(Files.readAllBytes(file.toPath()));
baos.write(("\r\n--" + boundary + "--\r\n").getBytes());
```

ב-Python, Flask מקבל את הקובץ דרך `request.files['file']` ואת
הפרמטרים דרך `request.form`.

### 4.4.2 polling vs push לעדכוני סטטוס

ה-GUI צריך להציג סטטוס מתעדכן (אחוז התקדמות, מהירות, peers, log).
שתי גישות עיקריות:

- **Polling**: ה-GUI שואל `GET /torrents` כל N שניות.
- **Push (WebSocket / SSE)**: השרת דוחף עדכונים ל-GUI.

Push נראה אלגנטי יותר, אך מוסיף תלות בספריות נוספות
(`flask-sock`, `aiohttp-cors`) ומורכבות התחברות. Polling פשוט,
אבל גורם לעיכוב הצגה ושימוש מיותר ברוחב פס מקומי.

**ההכרעה**: **שילוב מאוזן** — polling של `GET /torrents` כל
2 שניות (קצב טוב לסטטיסטיקה איטית כמו אחוז התקדמות), בשילוב עם
*incremental log polling* — `GET /torrents/<id>/logs?since=N` —
שמחזיר רק לוגים חדשים מאז ה-sequence האחרון שראינו. כל
לוג מקבל מספר סידורי גלובלי, וה-GUI שומר `logSeqTracker` לכל
torrent. כך, אף שמשתמשים ב-polling, חוויית הלוג היא כמעט real-time
ללא הצורך ב-WebSocket.

### 4.4.3 מעבר *Completed* — איך מזהים שהורדה הסתיימה לפני ה-poll הבא?

ה-poll קורה כל 2 שניות. אם הורדה הסתיימה רגע אחרי poll, חולפות
עד 2 שניות עד שה-GUI יידע. נראה זניח — אך גרם לעיכוב מוחשי
ב-popup שמודיע למשתמש שההורדה הסתיימה.

**ההכרעה**: בנוסף ל-polling של הסטטוס, ה-GUI **גם** עוקב אחרי
*log messages* (שמגיעים בקצב גבוה יותר), ומחפש בהם הודעת
`Completed:` כסיגנל מעבר. הקוד:

```java
// java_gui/src/TorrentClientGUI.java (קצור)
String prevState = previousStates.get(torrentId);
if ("Completed".equals(status.state) &&
    !"Completed".equals(prevState)) {
    showCompletionPopup(status.name, status.downloadPath);
}
previousStates.put(torrentId, status.state);
```

הקטע מציג איך המעבר ל-Completed נזוהה ויוצר popup. הזיהוי הזה
מתבסס על *state transition*, לא על *state value*, כך שלא יוצג
popup חוזר אם ה-poll מתבצע פעמיים על אותו מצב.

---

## 4.5 אתגר ה-Download Stalling — מקרה בוחן

הבאג הקשה ביותר שעמד בפני הפרויקט היה **התקעות הורדות בשיעור
15–20%**. הבאג הופיע באופן עקבי בכל torrent מעל ~50 pieces,
ולכן הפך לחסם מוחלט בפני סיום אפילו הורדה אחת.

### 4.5.1 תסמינים

- ההורדה מתחילה בקצב נורמלי (5–10 Mbps).
- אחרי 300–600 pieces (15–20% מ-torrent בינוני), קצב ההורדה צונח
  ל-0.
- חיבורי TCP נשארים פתוחים, peers לא נחנקים, אבל בקשות חדשות
  אינן נשלחות.
- אין שגיאה. אין log שמצביע על הסיבה. ה-GUI מציג "תקועה".

### 4.5.2 ניסיונות פתרון שכשלו

ב-`DOWNLOAD_STALLING_DEBUG_GUIDE.md` מתועדים בפירוט שש איטרציות של
אבחון, שכל אחת מהן זיהתה גורם תורם אך לא את שורש הבעיה:

1. ניסיון להוסיף ניקוי `_pending_requests` בהשהיה — לא עזר.
2. ניסיון להחליף את `MAX_PENDING_REQUESTS` מ-10 ל-50 — שיפר את
   המהירות עד הנקודה אך לא מנע התקעות.
3. ניסיון להוסיף `keep-alive` כל 30 שניות — לא עזר.
4. ניסיון לשמור block requests ב-set גלובלי במקום `Dict[peer]` —
   החמיר את המצב.
5. ניסיון להעביר את `_request_pieces` להפעלה במחזור קצר יותר —
   לא עזר.
6. ניסיון להחליף את ה-piece manager ב-implementation מבוסס
   `heapq` — לא קשור לבעיה.

### 4.5.3 שורש הבאג — *Block Scattering* ו-*Peer Convergence*

הניתוח הסופי חשף שהבאג אינו **באג נקודתי** אלא **תוצר לוואי של
ארכיטקטורה לא-מדויקת**, ששורשה במספר גורמים מצרפיים:

1. **Block scattering**: 50 peers הקצו במקביל בלוקים שונים מאותו
   piece. כל peer קיבל 1–2 בלוקים מתוך 16, ואחרי ש-peer חנק או
   נותק, הבלוק שלו "תקוע" — לא נשלחת בקשה חדשה.
2. **Peer convergence**: כל ה-peers בחרו את אותם 3–5 pieces "הכי
   נדירים" באותו רגע, מה שאוכל את היכולת לעבוד פיסות במקביל.
3. **Pending request counter stuck**: `_pending_requests` של peer
   מסוים נשאר ב-10 כי לא הגיע piece — ה-peer נראה "תפוס" אבל
   בפועל סיים מזמן.
4. **HAVE לא מועבר**: לאחר השלמת piece, ה-`HAVE` נשלח באופן
   סדרתי ל-50 peers, מה שתפס את ה-event loop ל-100ms ומנע
   טיפול ב-PIECE messages שהגיעו במקביל.

### 4.5.4 הפתרון המקיף

הפתרון הסופי, שעבד, היה **ארכיטקטוני** ולא **תיקון באג נקודתי**:

1. **Per-peer piece assignment** — `_peer_piece: Dict[str, int]`
   מקצה לכל peer piece אחד בלבד בכל זמן. הבלוקים של piece זה הם
   "טריטוריה" של ה-peer. כך נמנע block scattering.
2. **Block request tracking with timeouts** — כל בלוק שומר
   `requested_by` ו-`requested_time`. אחרי 10 שניות, הבלוק "חוזר
   לחיים" וזמין ל-peer אחר.
3. **Choke handling** — כאשר peer חונק, כל ה-block requests שלו
   מתבטלים מיידית ב-`clear_peer_requests(peer_key)`.
4. **Stuck counter recovery** — אחרי 15 שניות בלי PIECE response,
   `_pending_requests` מאופס.
5. **Non-blocking broadcast** — `_broadcast_have` מופעל כ-
   `asyncio.create_task()` עם `gather()` במקום בלולאה סדרתית.
6. **Immediate pipelining** — בכל UNCHOKE או PIECE completion,
   הוקצתה עבודה חדשה מיידית, ולא בלולאת ה-`_request_pieces`
   הבאה.

הפתרון פותר את הבעיה לחלוטין: torrents עד 4GB מורדים בהצלחה
ב-100%.

### 4.5.5 לקחים

ארבעה לקחים מרכזיים נלמדו מהמקרה:

1. **לא כל באג הוא באג נקודתי** — לפעמים תכן ארכיטקטוני חלש
   מתבטא כסימפטומים מקומיים.
2. **תיעוד מסודר של ניסיונות שכשלו** הוא בעל ערך — מכוון לאיזה
   אזורים לבדוק ולאיזה לא.
3. **כל פעולה ארוכה ב-event loop היא סיכון** — broadcast סדרתי
   ל-50 peers זה מספיק כדי להזיק.
4. **timeouts הם תשתית, לא עיטור** — בלעדיהם, כל מערכת מבוזרת
   מתפרקת כאשר peer אחד פועל בצורה לא צפויה.

תיעוד מלא של תהליך פתרון הבאג נמצא ב-`DOWNLOAD_STALLING_DEBUG_GUIDE.md`
בשורש הריפו, וניתוח טכני מעמיק יותר יוצג בפרק 24 (בדיקות והערכה)
ובפרק 25 (מסקנות).

---

## סיכום הפרק

פרק זה הציג חמש קבוצות אתגרים שעמדו בפני הפרויקט: **אכיפת
פרוטוקול וקידוד** (Bencode קנוני, חישוב info_hash, וולידציה של
Peer Wire Protocol); **אלגוריתמיקה ויעילות** (בחירה נכונה בתוך
קבוצה נדירה, איזון pipelining, ניהול block timeouts); **קונקורנציה
ומערכת הפעלה** (מעבר מ-threading ל-asyncio, executor לפעולות
כבדות, תיאום Flask–asyncio); **אינטגרציה רב-לשונית** (multipart
לקבצים בינאריים, polling יעיל, זיהוי מעברי מצב); ולבסוף **באג
ההתקעות** — מקרה בוחן ארכיטקטוני שחייב חשיבה מחדש על שמונה
מנגנונים בשילוב.

כל האתגרים שתועדו כאן נפתרו במלואם, וההכרעות שהתקבלו ילוו את
פרקי האפיון והמימוש שלהלן: פרק 11 יציג את הארכיטקטורה המקיפה את
ההכרעות הללו, פרק 21 יציג את הקוד הקונקרטי המממש אותן, ופרק 24
יוכיח אמפירית את עמידותם בעומס.
