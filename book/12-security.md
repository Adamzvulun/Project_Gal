# פרק 12 – תיאור תהליכי אבטחת המידע במערכת

## פתיח

פרק זה מתאר את **תהליכי אבטחת המידע** של המערכת בהתאם לסעיף 12
בנוהל ההגשה. הפרק נחלק לשני תתי-סעיפים נדרשים:

- **12.1 — תיאור התקיפה או ההגנה**: מודל איום, וקטורי תקיפה,
  וההגנות שמומשו בקוד; ניתוח מפורט בשכבת התעבורה ובשכבת
  האפליקציה, כפי שדורש המחוון לקטגוריית *"מערכות הפעלה /
  רשתות מחשבים / תקשורת נתונים / אבטחת מידע"* (עמ' 3 בנוהל,
  *"ניתוח איומים בשכבת האפליקציה, שכבת התעבורה לפחות"*).
- **12.2 — תיאור הצפנות**: השימוש ב-SHA-1 (info_hash ו-piece
  verification), ניתוח SWOT לאלגוריתמי hash/הצפנה, ופרטיות
  מול ה-tracker.

מבחינה מערכתית, המערכת היא **לקוח BitTorrent מגן (defensive)**:
היא אינה מבצעת תקיפות, אלא מתגוננת מפני שלוש משפחות איומים —
peers זדוניים בתוך ה-swarm, tracker שנפרץ, ותוקף MITM/eavesdropper
על הרשת הציבורית. כל מנגנוני ההגנה מרוכזים במודול
`python_engine/security.py` (מחלקת `SecurityManager` + 326 שורות
קוד), עם נקודות אכיפה ב-`peer_connection.py` (ולידציית פרוטוקול)
וב-`download_manager.py` (אינטגרציה, באן ב-runtime).

---

## 12.1 תיאור התקיפה או ההגנה

### 12.1.1 גישת האבטחה הכוללת

הפרויקט אינו פרויקט תקיפה אלא **פרויקט הגנה**. כל המנגנונים
שיוצגו להלן נועדו לעמוד בפני 3 משפחות איומים עיקריות:

1. **Peers זדוניים בתוך ה-swarm** — מקבלים חיבור TCP מאיתנו אך
   מנסים לפגוע במערכת (לשלוח data פגום, להציף בהודעות, להתחזות
   ל-peer חוקי, להפיל אותנו ע"י הודעות חורגות).
2. **Tracker שנפרץ או זדוני מלכתחילה** — שולח רשימת peers
   זדוניים, מאסף מידע על ההורדות שלנו (info_hash, IP, peer_id,
   uploaded/downloaded), או דוחה את ההורדה.
3. **MITM/Eavesdropper בשכבת הרשת** — האזנה לתעבורה בין הלקוח
   ל-tracker או בין הלקוח ל-peers, החדרת הודעות מזויפות,
   שינוי תעבורה.

המערכת לא מנסה לפתור את שלוש המשפחות בצורה מלאה — חלק מהאיומים
מטופלים מלא, חלק חלקית, וחלק נשארים מחוץ לסקופ הגרסה הנוכחית
ומוזכרים מפורשות בפרק 26 (פיתוחים עתידיים).

> **תרשים נדרש (Fig-08)**: תרשים מודל איום (Threat Model
> Diagram). ראה רשומה ב-`IMAGES.md`.

### 12.1.2 וקטורי איום (Threat Vectors)

הטבלה הבאה מפרטת את וקטורי האיום הספציפיים שהפרויקט נדרש
להתמודד איתם:

| מס' | וקטור | שכבה | חומרה | מנגנון הגנה |
|---|---|---|---|---|
| T1 | Peer שולח block עם data שגוי (מכוון) | אפליקציה | גבוהה | SHA-1 verify per piece + ban אחרי 3 כשלים |
| T2 | Peer שולח `length prefix` חורג (DoS על זיכרון) | תעבורה | גבוהה | `MAX_MESSAGE_SIZE = 2 MB` + מעקב violations |
| T3 | Peer שולח `piece_index` מחוץ לטווח | אפליקציה | בינונית | `validate_piece_index` → protocol violation |
| T4 | Peer שולח `handshake` עם `info_hash` שגוי | אפליקציה | גבוהה | זריקת `PeerConnectionError` + סגירת חיבור |
| T5 | Peer שולח `msg_id` לא חוקי | אפליקציה | נמוכה | זריקה ב-`MessageType(msg_id)` → drop של ההודעה |
| T6 | Peer מציף ב-HAVE/BITFIELD שגויים | אפליקציה | בינונית | מנייה ב-`protocol_violations` + ban אחרי 5 |
| T7 | Peer לא מגיב (slowloris, חיבור תלוי) | תעבורה | בינונית | `CONNECTION_TIMEOUT=30s`, `REQUEST_TIMEOUT=60s` |
| T8 | Tracker מחזיר peers זדוניים | אפליקציה | בינונית | מערכת המוניטין מסננת לאורך זמן (per-peer) |
| T9 | MITM בין הלקוח ל-tracker | תעבורה | בינונית | HTTPS אם ה-tracker תומך (תלוי URL) |
| T10 | MITM בין הלקוח ל-peers | תעבורה | בינונית | **לא מטופל בגרסה זו** (אין MSE/PE) — מצוין בסעיף 12.2.5 |
| T11 | מעקב פרטיות ע"י ה-tracker | אפליקציה | נמוכה | מוסבר ומתועד; mitigations עתידיים — DHT/PEX |

### 12.1.3 שכבת התעבורה — איומים והגנות

שכבת התעבורה במערכת מתבססת על **TCP/IP** משלוש צריכות שונות:
(1) HTTP/REST מקומי ל-`localhost:5000`; (2) HTTP/HTTPS אל
ה-tracker; (3) TCP גולמי אל peers (Peer Wire Protocol של BEP-3).
ההגנות שמומשו בכל אחת:

**(א) TCP loopback (לקוח ↔ Engine)** — תקשורת `127.0.0.1` בלבד,
לכן אינה חשופה למאזין רשת חיצוני; אין צורך ב-TLS לתקשורת זו
(loopback אינו עובר מחוץ למחשב). וקטורי איום בשכבה זו מינימליים,
ויהיו רלוונטיים רק אם תוקף כבר השיג ריצה מקומית — במקרה כזה
ה-attack surface הרבה יותר גדול מאשר ה-API.

**(ב) HTTP/HTTPS ל-tracker** — אם ה-`announce URL` בקובץ ה-
`.torrent` הוא `https://...`, ספריית `aiohttp` תבצע handshake
TLS אוטומטית ותאמת את התעודה מול ה-CA store של המערכת. אם
ה-tracker חושף רק `http://`, התעבורה תהיה גלויה ל-MITM. הבחירה
שלנו: לא לחסום `http` (תאימות לטרקרים ישנים), אך לתעד את הסיכון.

**(ג) TCP גולמי ל-peers (Peer Wire Protocol)** — אין הצפנה,
אין אימות. הגנה מ-DoS על שכבת התעבורה מסתמכת על שני מנגנוני
timeout ועל הגבלת message size:

```python
# python_engine/peer_connection.py (קצור)
MAX_MESSAGE_SIZE = 2 * 1024 * 1024     # 2 MB
CONNECTION_TIMEOUT = 30                # שניות
REQUEST_TIMEOUT = 60                   # שניות

async def _read_message(self):
    length_bytes = await asyncio.wait_for(
        self._reader.readexactly(4), timeout=REQUEST_TIMEOUT * 2)
    length = struct.unpack('!I', length_bytes)[0]
    if length == 0:
        return PeerMessage(MessageType.KEEP_ALIVE)
    if length > MAX_MESSAGE_SIZE:
        raise PeerConnectionError(
            f"Message too large: {length} bytes (max {MAX_MESSAGE_SIZE})")
    payload = await asyncio.wait_for(
        self._reader.readexactly(length), timeout=REQUEST_TIMEOUT)
    # ...
```

הסבר: כל הודעה ב-Peer Wire Protocol מתחילה בקידומת 4 בתים של
אורך. **בדיקת הגודל מתבצעת לפני** הקצאת ה-buffer (`readexactly`)
— כך peer זדוני לא יכול לאלץ אותנו להקצות גיגה-בתים של זיכרון
ע"י שליחת `0xFFFFFFFF` בקידומת. ה-`asyncio.wait_for` עוטף את
כל `readexactly` בטיימר, כך ש-peer ש"נתקע" באמצע שליחה נסגר
תוך 60 שניות לכל היותר ולא מחזיק את ה-coroutine לנצח.

### 12.1.4 שכבת האפליקציה — איומים והגנות

זוהי שכבת ההגנה המעמיקה ביותר במערכת. כל ההיגיון בשכבה זו
מרוכז במחלקה `SecurityManager` (`python_engine/security.py`)
ובמחלקה `PeerReputation` שעוטפת אותה. ההגנה מתבצעת בארבעה
מוקדים:

**(א) ולידציית `handshake`** — ה-handshake הוא **קו ההגנה
הראשון**: לפני שאנו מקבלים אפילו הודעה אחת מ-peer, אנו מאמתים
שהוא מדבר את הפרוטוקול הנכון ושהוא יודע את ה-`info_hash` של
ה-torrent שאנו מורידים:

```python
# python_engine/peer_connection.py (קצור)
async def _receive_handshake(self):
    data = await asyncio.wait_for(
        self._reader.readexactly(HANDSHAKE_LEN),
        timeout=CONNECTION_TIMEOUT)
    pstrlen = data[0]
    if pstrlen != PROTOCOL_STRING_LEN:
        raise PeerConnectionError(f"Invalid protocol length: {pstrlen}")
    if data[1:1 + pstrlen] != PROTOCOL_STRING:
        raise PeerConnectionError("Invalid protocol string")
    received_info_hash = data[1 + pstrlen + 8: 1 + pstrlen + 8 + 20]
    if received_info_hash != self.info_hash:
        raise PeerConnectionError("Info hash mismatch during handshake")
    self.remote_peer_id = data[1 + pstrlen + 8 + 20: 1 + pstrlen + 8 + 40]
```

הסבר: כל סטייה — אורך לא נכון, מחרוזת פרוטוקול לא נכונה, או
`info_hash` שאינו תואם — גורמת לסגירה מיידית של החיבור. זהו
מנגנון מובנה ב-BEP-3 שמונע מ-peer "תועה" מ-swarm אחר לדבר
איתנו בטעות, וגם מקשה על תקיפת capability confusion.

**(ב) ולידציית פורמט הודעות** — לאחר ה-handshake, כל הודעה
שמגיעה עוברת:
- **בדיקת אורך** (חיובי, ≤ 2MB) — בקוד ב-12.1.3.
- **בדיקת `msg_id`** — חייב להיות אחד מערכי ה-Enum `MessageType`
  (`CHOKE=0` עד `CANCEL=8`); ערך לא חוקי נזרק כ-`ValueError`
  והודעה זו מושמטת בלי לפגוע בשאר ה-session.
- **בדיקת `piece_index` ב-`HAVE`** — חייב להיות בטווח
  `[0, num_pieces)`; אחרת `_handle_message` זורק
  `PeerConnectionError` והחיבור נסגר.

**(ג) אימות תוכן piece-by-piece** — לב ההגנה. לפני שאנחנו
כותבים piece לדיסק, אנחנו מאמתים את ה-SHA-1 שלו מול ה-hash
שהופיע בקובץ ה-`.torrent`. piece שנכשל באימות **לא נכתב לדיסק**
וה-peer ששלח אותו מקבל נקודת חובה:

```python
# python_engine/download_manager.py (קצור)
if is_complete:
    verified = await loop.run_in_executor(
        self._executor, self.piece_manager.verify_piece, piece_idx)
    if verified:
        self.security.report_successful_piece(peer_key, piece_idx)
        await loop.run_in_executor(
            self._executor, self._write_piece_sync, piece_idx)
    else:
        self._log(f"Piece {piece_idx} HASH FAILED from {peer_key}")
        self.security.report_hash_failure(peer_key, piece_idx)
        if self.security.is_peer_banned(peer_key):
            self._log(f"Banned peer {peer_key} (too many hash failures)")
```

הסבר: אם `verify_piece` מחזירה False, ה-piece מאופס ב-
`PieceManager` (נטען חזרה כ-MISSING), ומידע על הכשל נרשם ב-
`SecurityManager.report_hash_failure`. הפעולות הכבדות (חישוב SHA-1
וכתיבה לדיסק) רצות ב-`ThreadPoolExecutor` כדי שלא לחסום את
ה-event loop.

**(ד) מערכת מוניטין ובאנים** — מתוארת בסעיף 12.1.5.

### 12.1.5 מנגנון המוניטין (Peer Reputation System)

המערכת מתחזקת *רישומי מוניטין נפרדים לכל peer* (לפי
`f"{ip}:{port}"`). כל peer מקבל אובייקט `PeerReputation` שצובר
מונים של אירועים שליליים וחיוביים, ומחושב לו ציון אמון בטווח
[0.0, 1.0]:

```python
# python_engine/security.py (קצור)
MAX_HASH_FAILURES_PER_PEER = 3
MAX_PROTOCOL_VIOLATIONS_PER_PEER = 5

class PeerReputation:
    def __init__(self, peer_key: str):
        self.hash_failures = 0
        self.protocol_violations = 0
        self.invalid_messages = 0
        self.successful_pieces = 0
        # ...

    @property
    def should_ban(self) -> bool:
        if self.hash_failures >= MAX_HASH_FAILURES_PER_PEER:
            return True
        if self.protocol_violations >= MAX_PROTOCOL_VIOLATIONS_PER_PEER:
            return True
        return False

    @property
    def trust_score(self) -> float:
        total = (self.successful_pieces + self.hash_failures
                 + self.protocol_violations + self.invalid_messages)
        if total == 0:
            return 0.5
        good = self.successful_pieces
        bad = (self.hash_failures * 3 + self.protocol_violations * 2
               + self.invalid_messages)
        return max(0.0, min(1.0, good / (good + bad)))
```

הסבר ההיגיון: לכל סוג חטא משקל שונה — כשל hash הוא חמור פי 3
מהודעה לא חוקית (כי הוא מצביע על data corruption מכוון), והפרת
פרוטוקול חמורה פי 2. חישוב הציון אינו לינארי אלא יחס של good
מול good+bad משוקלל, כך ש-peer שהביא 100 pieces תקינים שורד
כשל חד-פעמי. הספים (`MAX_HASH_FAILURES=3`, `MAX_PROTOCOL=5`)
נבחרו שמרניים: שלוש שגיאות hash הן יותר ממה שמסבירה תאונה
רשתית — לרוב מדובר ב-peer זדוני או buggy.

כאשר `should_ban` מחזיר True, `_ban_peer` מוסיף את ה-peer ל-
`_banned_peers: Set[str]`. בלולאת ה-`_connect_to_peers`
ב-`download_manager.py` יש בדיקה מפורשת:

```python
# python_engine/download_manager.py (קצור)
for peer in list(self._known_peers):
    peer_key = f"{peer.ip}:{peer.port}"
    if peer_key in self._connections:
        continue
    if self.security.is_peer_banned(peer_key):
        continue           # ← peer מבונה לעולם לא ינסה להתחבר אליו שוב
    # ...
```

לכן באן אינו רק "סוגר את החיבור הנוכחי" — הוא **מונע ניסיונות
התחברות עתידיים** ל-peer זה לכל אורך ההורדה, גם אם ה-tracker
ישלח אותו שוב ברשימת ה-peers.

### 12.1.6 לוג אירועי אבטחה

כל אירוע (`hash_failure`, `protocol_violation`, `invalid_message`,
`timeout`, `peer_banned`) נכנס לרשימה
`SecurityManager._events: List[SecurityEvent]` עם חותמת זמן,
חומרה (`info`/`warning`/`error`), ותיאור. הלוג נחשף ב-API
דרך `/events` (ראה פרק 11.5) ומופיע ב-`AlgorithmStatsDialog`
של ה-GUI. callbacks חיצוניים יכולים להירשם דרך `on_event`,
כך שמודולים אחרים (לדוגמה, מודול היסטוריה ב-SQLite) יכולים
לתעד אירועי אבטחה גם הם.

> **תרשים נדרש (Fig-09)**: תרשים זרימת הגנה (Defense Flow
> Diagram). ראה רשומה ב-`IMAGES.md`.

### 12.1.7 סיכום הגנות שכבת האפליקציה

הטבלה מסכמת את שכבות ההגנה לפי "*defense in depth*":

| שכבת הגנה | מיקום בקוד | מתי מופעל |
|---|---|---|
| ולידציית handshake (info_hash, pstr) | `peer_connection.py:_receive_handshake` | בחיבור הראשון לכל peer |
| בדיקת אורך הודעה (≤ 2 MB) | `peer_connection.py:_read_message` | בכל הודעה |
| בדיקת `msg_id` חוקי | `peer_connection.py:_read_message` | בכל הודעה |
| בדיקת `piece_index` ב-HAVE | `peer_connection.py:_handle_message` | בכל הודעת HAVE |
| timeout 30/60/120s | קבועים ב-`peer_connection.py`/`security.py` | בקריאות חוסמות |
| SHA-1 verify per piece | `piece_manager.py:verify_hash` | בסיום piece |
| Reputation + auto-ban | `security.py:SecurityManager` | באירוע hash/protocol |
| חסימת התחברות חוזרת | `download_manager.py:_connect_to_peers` | בכל סבב חיבורים |

---

## 12.2 תיאור הצפנות

המחוון (עמ' 11 בנוהל) מבקש *"תיאור הצפנות — אם יש"*. בפרויקט
זה נעשה שימוש פונקציה קריפטוגרפית אחת — **SHA-1** — בשני
תפקידים שונים, ושני התפקידים הם **פונקציות hash לאימות שלמות
(integrity)** ולא הצפנה לשמירת סודיות (confidentiality). זוהי
הבחנה חשובה: BitTorrent הוא פרוטוקול **שיתוף קבצים פומבי** —
התוכן אינו אמור להישאר סודי, אלא אמין ולא משובש. ככזה, חתימת
SHA-1 על כל piece היא המנגנון הקריפטוגרפי המרכזי בפרוטוקול.

### 12.2.1 שימוש 1 — `info_hash` כמזהה ה-torrent

כל קובץ `.torrent` מכיל מילון bencoded עם מפתח `info`. ה-
**`info_hash`** הוא ה-SHA-1 של ה-bytes המקוריים של המילון
הזה לאחר re-encoding בפורמט bencode. ה-`info_hash` משמש
לשלושה דברים:

1. **זיהוי ה-torrent** מול ה-tracker (פרמטר ב-announce).
2. **אימות התאמת peer** בשלב ה-handshake (כפי שראינו ב-12.1.4).
3. **לזהות** ש-`.torrent` שעבר ידיים לא שונה בדרך.

```python
# python_engine/torrent_metadata.py (קצור)
if b'info' not in self._metadata:
    raise TorrentMetadataError("Missing 'info' dictionary")
info = self._metadata[b'info']
if not isinstance(info, dict):
    raise TorrentMetadataError("'info' must be a dictionary")

# Compute info_hash: SHA-1 of the re-encoded info dictionary
info_encoded = bencode.encode(info)
self.info_hash = hashlib.sha1(info_encoded).digest()
```

הסבר: מבחינה קריפטוגרפית, כל אדם בעולם יכול לקחת `.torrent`
זהה ולקבל את אותו `info_hash` — לכן זהו **מזהה ייחודי גלובלי**
שאינו דורש רישום מרכזי. שיטה זו מקבילה למזהי content-addressed
storage כמו ב-IPFS.

### 12.2.2 שימוש 2 — אימות שלמות piece-by-piece

הקובץ ה-`.torrent` מכיל את השדה `pieces` — שרשור של hashים
באורך 20 בתים כל אחד (SHA-1 על תוכן ה-piece המקורי). בעת
ההורדה, `PieceManager` מאמת כל piece שהתקבל מול ה-hash הצפוי:

```python
# python_engine/piece_manager.py (קצור)
class Piece:
    def __init__(self, index: int, length: int, expected_hash: bytes):
        self.index = index
        self.expected_hash = expected_hash
        # ...

    def verify_hash(self) -> bool:
        actual_hash = hashlib.sha1(bytes(self._data)).digest()
        return actual_hash == self.expected_hash
```

הסבר: piece טיפוסי גדול 256KB–1MB. אם **ולו ביט אחד** השתנה
ב-piece — בין אם בגלל corruption רשתי, באג ב-peer, או תקיפה
מכוונת — ה-SHA-1 ישתנה לחלוטין (אפקט המפולת של פונקציות hash
טובות) ו-`verify_hash` יחזיר False. הסיכוי לקולישן אקראי הוא
2⁻¹⁶⁰, זניח לכל מטרה מעשית. עלות החישוב: ~5 מיקרו-שניות לכל
KB על מעבד מודרני, ולכן החישוב הזה מתבצע ב-`ThreadPoolExecutor`
ולא חוסם את ה-event loop.

### 12.2.3 ניתוח SWOT — SHA-1

המחוון דורש מפורשות *"ניתוח וביצוע SWOT לאלגוריתמי הצפנה"*
(עמ' 3, קטגוריית מערכות הפעלה/רשתות/אבטחה). SWOT ל-SHA-1
בהקשר הפרויקט:

| ממד | פירוט |
|---|---|
| **Strengths** | מהיר מאוד (≥ 500 MB/s במעבד מודרני, ללא חומרה ייעודית); נתמך בכל ספריית סטנדרטית של Python (`hashlib`); אורך פלט קצר ועקבי (20 בתים = 160 ביט) שמאפשר אריזה צפופה ב-`pieces`; **תאימות מלאה לפרוטוקול BEP-3** של BitTorrent. |
| **Weaknesses** | **SHA-1 נחשב פגיע ל-cryptographic collision attacks החל מ-2017** (SHAttered, Google/CWI); ייצור collisions ממוקדות הוא יקר אך אפשרי לתוקף מאורגן; **160 ביט פחות מהמומלץ היום** לטווח ארוך (≥ 256 ביט). |
| **Opportunities** | מעבר ל-**SHA-256** הוסדר ב-**BEP-52** (BitTorrent v2), שמשתמש גם ב-Merkle Trees לאימות חלקי piece ולחיסכון ב-bandwidth; שילוב **BLAKE2b/BLAKE3** היה משפר ביצועים פי 2–3 לעומת SHA-1 ועדיין מעניק ביטחון של 256 ביט. |
| **Threats** | **תקיפת collision על `.torrent`** — תוקף שיוצר שני קבצים שונים עם אותו `info_hash` (כפי שהוכח עבור PDFים ב-SHAttered) יכול תאורטית להפיץ piece משובש ב-swarm; **הפרוטוקול BEP-3 לא יוצא מ-deprecation** בשל בסיס מותקן עצום — כל הספרייה הפומבית של torrents עדיין SHA-1; כשל בפועל יחייב מיגרציה גלובלית. |

**ההכרעה בפרויקט**: בחירת SHA-1 נכפתה ע"י **תאימות לפרוטוקול
הקיים** — כל ה-trackers, ה-clients וקבצי ה-`.torrent` בעולם
מבוססים SHA-1 (BEP-3). מעבר ל-SHA-256 היה דורש מימוש מלא של
BEP-52, שכולל פירוק piece ל-blocks של 16KB עם Merkle Tree, שינוי
משמעותי ב-handshake, וב-protocol extensions — מחוץ לסקופ הגרסה
הראשונה. הסיכון בפועל מוגבל מאוד: collision attack על
`.torrent` ספציפי דורש משאבים של מדינה (Google הוציאו ~6,500
שנות מעבד על PDF יחיד ב-2017), והפרוטוקול עצמו אינו רגיש ל-
preimage attack (שאינה ידועה ל-SHA-1).

### 12.2.4 השוואת אלגוריתמי hash חלופיים

| אלגוריתם | אורך פלט | שימוש ב-BitTorrent | ביטחון | מהירות (Python) |
|---|---|---|---|---|
| **MD5** | 128 ביט | היסטורי בלבד | שבור (preimage + collision) | מהיר |
| **SHA-1** | 160 ביט | **BEP-3 / v1 (הפרויקט)** | פגיע ל-collision | מהיר (~500 MB/s) |
| **SHA-256** | 256 ביט | **BEP-52 / v2** | מאובטח | בינוני (~200 MB/s) |
| **SHA-3 (Keccak)** | משתנה | אין | מאובטח (תכנון שונה) | איטי |
| **BLAKE2b** | משתנה (≤ 512) | אין | מאובטח | מהיר מאוד (~1 GB/s) |
| **BLAKE3** | משתנה | אין | מאובטח | מהיר ביותר (~3 GB/s) |

בחירת SHA-1 מוצדקת כאמור ע"י תאימות בלבד; ללא מגבלת התאימות
**BLAKE3** היה הבחירה האופטימלית (ביטחון 256 ביט + ביצועים פי 6
מ-SHA-1).

### 12.2.5 הצפנה בשכבת התעבורה — מה יש ומה אין

| ערוץ תקשורת | הצפנה בפועל | הסבר |
|---|---|---|
| Java GUI ↔ Engine | אין | loopback (`127.0.0.1:5000`) — אינו עובר ברשת |
| Engine ↔ Tracker | **HTTPS אם ה-URL הוא `https://`** | תלוי ב-`announce URL` בקובץ ה-`.torrent`; `aiohttp` מבצע אימות תעודה אוטומטית |
| Engine ↔ Peers | **אין** | Peer Wire Protocol ב-BEP-3 רץ ב-TCP גולמי |

הסיבה לחוסר ההצפנה בערוץ ה-peers היא היסטורית: BEP-3 (2008)
לא הגדיר הצפנה, כי ההנחה הייתה ש-content public. עם השנים
התוסף **MSE/PE (Message Stream Encryption / Protocol Encryption)**
פותח כ-BEP-לא-רשמי כדי לעקוף **deep packet inspection (DPI)**
של ISPs שניסו להגביל תעבורת BitTorrent. MSE/PE משתמשת ב-
Diffie-Hellman להסכמת מפתח ו-RC4 להצפנה זרם.

**במערכת הנוכחית MSE/PE לא ממומשת**. הסיבות:
1. מורכבות מימוש (DH key exchange, RC4 state, השוואת תיאום בין
   peers שתומכים/לא תומכים);
2. RC4 עצמו נחשב חלש היום וה-IETF פסל אותו ב-2015;
3. ל-MSE/PE אין יעד אבטחה אמיתי — היא **אנטי-DPI**, לא הגנת
   סודיות (אין אימות).

מימוש MSE/PE מוזכר מפורשות בפרק 26 (פיתוחים עתידיים) כשיפור
אפשרי לעתיד, יחד עם מימוש **BitTorrent v2 (BEP-52)** שמביא גם
SHA-256 וגם אופציות חתימה דיגיטלית.

### 12.2.6 SWOT לאלגוריתמי הצפנה בעולם BitTorrent

מאחר שהפרויקט אינו מצפין את שכבת ה-peers, ה-SWOT הבא מתייחס
ל-**אלגוריתמי ההצפנה הפוטנציאליים** שיכולנו לבחור (השלמה
לדרישת המחוון):

**MSE/PE (RC4 + DH-768)**:

| ממד | פירוט |
|---|---|
| Strengths | תאימות נרחבת לקליינטים קיימים (qBittorrent, Transmission); קל יחסית לממש; עוקף DPI ביעילות. |
| Weaknesses | RC4 נחשב חלש (יכולות תקיפה מ-2013); DH-768 מתחת לסטנדרט 2024 (≥ 2048 ביט); ללא אימות, פגיע ל-MITM. |
| Opportunities | החלפת RC4 ב-ChaCha20-Poly1305 + DH-2048 תיתן AEAD מודרני בעלות חישובית דומה. |
| Threats | MSE/PE מספקת *obfuscation* ולא *security* — תוקף אקטיבי עדיין יכול ל-MITM; מבחינת privacy זה תיקון חלקי בלבד. |

**TLS 1.3 על TCP (היפותטי, לא חלק מ-BEP כלשהו)**:

| ממד | פירוט |
|---|---|
| Strengths | סטנדרט תעשייתי בוגר; אימות תעודה + הצפנה + integrity ב-AEAD יחיד; ספריות זמינות בכל שפה. |
| Weaknesses | מצריך תעודות (PKI) שלא מתאימות למודל P2P אנונימי; overhead handshake גבוה. |
| Opportunities | שילוב Self-Signed certs + Trust-On-First-Use (TOFU) ע"ב peer_id יכול לגשר על הפער. |
| Threats | חורג מ-BEP, ישבור תאימות עם כל ה-swarm הקיים. |

**Noise Protocol Framework**:

| ממד | פירוט |
|---|---|
| Strengths | מודרני, AEAD מובנה, גמיש (תומך בתבניות עם/בלי אימות); אומץ ב-WireGuard. |
| Weaknesses | פחות ספריות זמינות בפייתון; דורש החלטות עיצוב נוספות (תבנית הפרוטוקול). |
| Opportunities | יוכל להחליף את MSE/PE כסטנדרט הבא ל-BitTorrent. |
| Threats | אינו חלק מאף BEP פעיל. |

### 12.2.7 פרטיות מול ה-Tracker

ה-tracker חושף את עצם פעילותנו בדרכים הבאות (מבוסס על
`security.py:TRACKER_PRIVACY_ANALYSIS` שמתעד את הניתוח בקוד
עצמו):

1. **`info_hash`** — חושף איזה torrent אנו מורידים.
2. **`peer_id`** — מזהה ייחודי שלנו (20 בתים) שיכול לעקוב
   אחרינו על פני announces ועל פני torrents שונים.
3. **כתובת IP** — נחשפת ל-tracker ולכל peer ב-swarm.
4. **`uploaded` / `downloaded`** — מאפשרים בניית פרופיל
   שימוש על פני זמן.
5. **`port`** — משלים את ה-network endpoint.

**מיטיגציות עתידיות** (גם הן מתועדות בקוד):
- **DHT (Distributed Hash Table, BEP-5)** — מבטל את התלות
  ב-tracker מרכזי, מבצע גילוי peers דרך mainline DHT (Kademlia).
- **Peer Exchange (PEX, BEP-11)** — מאפשר לקבל peers ישירות
  מ-peers אחרים במקום מ-tracker.
- **`peer_id` רנדומלי לכל session** — מקטין correlation; ניתן
  לממש במהפך מינורי ב-`generate_peer_id()`.
- **VPN/Tor כשכבת רשת חיצונית** — מסתיר את ה-IP, אך אינו
  משנה שום דבר ברמת היישום.

**במצב הנוכחי** המערכת **כן** מייצרת `peer_id` חדש בכל הפעלה
דרך `generate_peer_id()` ב-`tracker_client.py`, אך ה-`peer_id`
נשאר זהה לאורך כל ה-session ולכל ה-torrents הפעילים בה
בו-זמנית — לכן ה-correlation בין torrents שונים באותה הרצה
עדיין אפשרי. שיפור עתידי: `peer_id` נפרד לכל torrent.

---

## 12.3 סיכום הפרק

פרק זה הציג את **מערך אבטחת המידע** של המערכת:

- **12.1** ניתח את **שכבת התעבורה** (TCP loopback, HTTP/HTTPS
  ל-tracker, TCP ל-peers) ואת **שכבת האפליקציה** (`SecurityManager`
  עם מערכת מוניטין, ולידציית handshake, ולידציית הודעות,
  ספים אוטומטיים לבאן, ולוג אירועים). הוצגה טבלת 11 וקטורי
  איום (T1–T11) עם מנגנוני ההגנה הספציפיים, ונמסר רק וקטור
  אחד (T10 — MITM בערוץ peers) ללא טיפול בגרסה הנוכחית.

- **12.2** הציג את שני השימושים ב-**SHA-1** במערכת — ייצור
  `info_hash` בעת פענוח קובץ `.torrent` ואימות piece-by-piece
  לאחר הורדה — והעמיד **ניתוח SWOT מלא** ל-SHA-1, השוואה
  לאלגוריתמי hash חלופיים (MD5, SHA-256, SHA-3, BLAKE2/3),
  סקירת מצב ההצפנה בשכבת התעבורה (HTTPS אופציונלי ל-tracker,
  ללא MSE/PE לערוץ peers), ניתוח SWOT לשלוש משפחות אלגוריתמי
  הצפנה רלוונטיות (MSE/PE, TLS 1.3, Noise), וניתוח פרטיות מול
  ה-tracker עם מיטיגציות עתידיות.

הגישה הכוללת היא **defense in depth** — שמונה שכבות הגנה
נפרדות לפני שתוכן נכתב לדיסק (טבלה ב-12.1.7), כך ש-peer זדוני
חייב להפר מספר מנגנוני בקרה בו-זמנית כדי להזיק. הקוד בפועל
מרוכז ב-`security.py` (326 שורות) ובנקודות אכיפה ב-
`peer_connection.py` ו-`download_manager.py`.

הפרק הבא (פרק 13) הוא פרק קצר המציין שהנושא **למידת מכונה** —
שאליו מתייחס סעיף 13 בנוהל — אינו ישים לפרויקט זה, ולכן
לא נכתב לו תוכן מהותי, תוך שמירה על המספור הרציף.
