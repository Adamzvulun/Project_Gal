# 12. תיאור תהליכי אבטחת המידע במערכת

## 12.1 תיאור התקיפה או ההגנה

המערכת היא לקוח BitTorrent מגן (defensive) ולא תוקף.
היא מתגוננת מפני שלושה סוגי איומים: peers זדוניים ששולחים
data פגום או מציפים בהודעות, tracker שנפרץ ועלול לחשוף
מידע על ההורדות, ותוקף MITM/eavesdropper על שכבת הרשת.

הניתוח מתחלק לשתי שכבות, כפי שדורש המחוון:

**שכבת התעבורה (Transport Layer)**: התעבורה מתחלקת לשני
ערוצים — ל-tracker (HTTP/HTTPS) ול-peers (TCP גולמי).
התקשורת ל-tracker מוצפנת אם ה-URL הוא HTTPS, אך התקשורת
ל-peers אינה מוצפנת כלל בגרסה הנוכחית. ההגנה העיקרית
בשכבה זו היא הגבלת גודל הודעה ל-2MB וטיימאוטים:

```python
# python_engine/peer_connection.py
async def _read_message(self):
    length_bytes = await asyncio.wait_for(
        self._reader.readexactly(4), timeout=REQUEST_TIMEOUT*2)
    length = struct.unpack('!I', length_bytes)[0]
    if length > MAX_MESSAGE_SIZE:        # 2 MB
        raise PeerConnectionError(f"Message too large: {length}")
```

בדיקת הגודל מתבצעת לפני הקצאת ה-buffer, כך ש-peer זדוני
לא יכול לאלץ אותנו להקצות גיגה-בתים של זיכרון ע"י שליחת
`0xFFFFFFFF` בקידומת. הטיימאוטים (30 שניות ל-handshake,
60 שניות לכל הודעה) מבטיחים ש-peer ש"נתקע" באמצע שליחה
ישוחרר ולא יחזיק את ה-coroutine לנצח.

**שכבת האפליקציה (Application Layer)**: כל ההיגיון
מרוכז במחלקה `SecurityManager` שב-`python_engine/security.py`.
המודול מבצע ארבע פעולות הגנה עיקריות:

1. **אימות handshake**: לפני שמקבלים אפילו הודעה אחת
   מ-peer, מאמתים שהוא מדבר את הפרוטוקול הנכון ושהוא יודע
   את ה-`info_hash` של ה-torrent. כל סטייה — אורך לא נכון,
   מחרוזת פרוטוקול לא נכונה, `info_hash` שאינו תואם —
   גורמת לסגירת החיבור באופן מיידי.

2. **אימות פורמט הודעות**: כל `msg_id` חייב להיות אחד
   מערכי ה-Enum (0–8). כל `piece_index` ב-HAVE חייב להיות
   בטווח חוקי. הפרות מצטברות במונה violations של ה-peer.

3. **אימות תוכן ב-SHA-1**: לפני שכותבים piece לדיסק,
   מחשבים SHA-1 שלו ומשווים מול ה-hash שב-`.torrent`.
   piece שנכשל באימות לא נכתב — וה-peer ששלח אותו מקבל
   נקודת חובה.

4. **מערכת מוניטין ובאן**: לכל peer מתחזקים אובייקט
   `PeerReputation` שצובר אירועים. שלוש שגיאות hash או
   חמש הפרות פרוטוקול → ban אוטומטי, וה-peer לא ינסה
   להתחבר אליו שוב:

```python
@property
def should_ban(self) -> bool:
    if self.hash_failures >= MAX_HASH_FAILURES_PER_PEER:  # 3
        return True
    if self.protocol_violations >= MAX_PROTOCOL_VIOLATIONS_PER_PEER:  # 5
        return True
    return False
```

הספים נבחרו שמרניים: שלוש שגיאות hash הן יותר ממה שמסבירה
תאונה רשתית — בדרך כלל מדובר ב-peer זדוני או buggy. הבאן
תקף לאורך כל ההורדה; גם אם ה-tracker יחזיר את אותו peer
ברשימה הבאה, `_connect_to_peers` יסנן אותו.

## 12.2 תיאור הצפנות

המערכת משתמשת בפונקציה קריפטוגרפית אחת — **SHA-1** —
בשני תפקידים שונים. שני התפקידים הם **פונקציות hash
לאימות שלמות (integrity)** ולא הצפנה לשמירת סודיות.
זוהי הבחנה חשובה: BitTorrent הוא פרוטוקול שיתוף קבצים
פומבי — התוכן אינו אמור להישאר סודי, אלא אמין ולא משובש.

**שימוש 1 — `info_hash` כמזהה גלובלי של ה-torrent**: ה-
`info_hash` הוא ה-SHA-1 של המילון `info` בקובץ ה-`.torrent`
לאחר re-encoding ב-bencode. הוא משמש לזיהוי ה-torrent מול
ה-tracker, ולאימות התאמת peer בשלב ה-handshake.

```python
# python_engine/torrent_metadata.py
info_encoded = bencode.encode(info)
self.info_hash = hashlib.sha1(info_encoded).digest()
```

**שימוש 2 — אימות שלמות piece-by-piece**: הקובץ ה-`.torrent`
מכיל את השדה `pieces` — שרשור של hashים באורך 20 בתים כל
אחד. בעת ההורדה, אחרי שכל הבלוקים של piece התקבלו, מחושב
SHA-1 על התוכן ומושווה מול ה-hash הצפוי:

```python
# python_engine/piece_manager.py
def verify_hash(self) -> bool:
    actual_hash = hashlib.sha1(bytes(self._data)).digest()
    return actual_hash == self.expected_hash
```

אם ולו ביט אחד השתנה ב-piece — בין אם בגלל corruption
רשתי, באג ב-peer, או תקיפה מכוונת — ה-SHA-1 ישתנה לחלוטין
(אפקט המפולת) ו-`verify_hash` יחזיר False. הסיכוי לקולישן
אקראי הוא 2⁻¹⁶⁰, זניח לכל מטרה מעשית.

**ניתוח SWOT ל-SHA-1**:

- **Strengths**: מהיר מאוד (~500 MB/s ב-Python), קצר
  ועקבי (20 בתים), תאימות מלאה ל-BEP-3.
- **Weaknesses**: נחשב פגיע ל-cryptographic collision
  attacks החל מ-SHAttered (2017); 160 ביט פחות מהמומלץ
  לטווח ארוך.
- **Opportunities**: מעבר ל-SHA-256 הוסדר ב-BEP-52
  (BitTorrent v2), שכולל גם Merkle Trees לאימות חלקי piece.
- **Threats**: תאורטית, תוקף מאורגן יכול לייצר collision
  עבור `info_hash` ולהפיץ piece משובש; דורש משאבים
  אדירים שאינם בהישג יד תוקף ממוצע.

הבחירה ב-SHA-1 נכפתה על ידי תאימות לפרוטוקול הקיים —
כל ה-trackers, ה-clients וקבצי ה-`.torrent` בעולם מבוססים
SHA-1. מעבר ל-SHA-256 היה דורש מימוש מלא של BEP-52, מחוץ
לסקופ הגרסה הראשונה.

**הצפנה בשכבת התעבורה** אינה ממומשת בערוץ ה-peers. תוסף
**MSE/PE (Message Stream Encryption)** קיים ב-BitTorrent
כסטנדרט דה-פקטו, אך לא ממומש בפרויקט הזה. הוא מספק
*obfuscation* בעיקר נגד DPI של ISPs, ולא הגנת סודיות
אמיתית — אין בו אימות, ולכן הוא לא מגן מפני MITM. מימוש
שלו, יחד עם תמיכה ב-BEP-52, מתועד כפיתוח עתידי בפרק 26.

**פרטיות מול ה-Tracker**: ה-tracker חושף את עצם פעילותנו —
איזה torrent אנו מורידים (`info_hash`), מי אנחנו (`peer_id`),
ה-IP שלנו, וכמה הורדנו/העלינו. מיטיגציות עתידיות שמקובלות
ב-BitTorrent: **DHT (BEP-5)** מבטל את התלות בtracker
מרכזי, ו-**PEX (BEP-11)** מאפשר ל-peers להחליף ביניהם
רשימות peers. שניהם מתועדים כפיתוח עתידי.
