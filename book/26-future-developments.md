# פרק 26 – פיתוחים עתידיים

## פתיח

פרק זה מציג **roadmap מפורט** לפיתוחים עתידיים שיגדילו את
יכולות המערכת. השיפורים מקובצים לפי **חמש קטגוריות**, ולכל
אחד מצוין:

- **רמת חשיבות**: 🔴 High / 🟠 Medium / 🟢 Low.
- **הערכת מאמץ**: שבועות-אדם (אומדן).
- **תלות בקוד הקיים**: מודולים שיושפעו.
- **רקע**: למה זה רלוונטי.

הפרק הוא **אינטגרציה של פערים ושיפורים** שהוזכרו לאורך
הספר (פרקים 11–25). זוהי תוכנית הפעולה הריאלית לגרסה
הבאה.

---

## 26.1 קטגוריה 1 — Networking ופרוטוקול

### 26.1.1 🔴 שרת listen נכנס (Incoming Peer Server)

**כיום**: המערכת **אינה מקבלת חיבורים נכנסים** (פרק 11.4.4,
14.2.4). היא רק יוזמת חיבורים יוצאים. לכן היא לא תורמת
ל-swarm מהמלוא הפוטנציאל שלה.

**הצעת מימוש**: הוסף `asyncio.start_server` על פורט 6881
(או דינמי) ב-`Download._download_loop`. כל חיבור נכנס יקבל
`PeerConnection` עם תפקיד "incoming" (receiver של handshake).

**מאמץ**: 1–2 שבועות. **תלות**: `peer_connection.py`,
`download_manager.py`.

### 26.1.2 🔴 NAT Traversal (UPnP / STUN)

**כיום**: המערכת מאחורי NAT לא יכולה לקבל חיבורים גם אם
תפעיל listen server. דרוש מנגנון Port Mapping.

**הצעת מימוש**: שילוב `miniupnpc` library — בעת startup,
לבדוק אם הראוטר תומך UPnP, ולפתוח port mapping ל-6881.
חלופה: STUN לזיהוי כתובת ציבורית + hole punching.

**מאמץ**: 2–3 שבועות. **תלות**: מודול networking חדש.

### 26.1.3 🟠 DHT (Distributed Hash Table, BEP-5)

**כיום**: המערכת תלויה לחלוטין ב-tracker. אם ה-tracker
נופל — אין דרך לגלות peers.

**הצעת מימוש**: מימוש Kademlia DHT (BEP-5) — תהליך טוויני
שמתחזק רשת mainline DHT. peers ניתנים לגילוי דרך
`info_hash` בלי tracker.

**מאמץ**: 4–6 שבועות (מימוש מורכב). **תלות**: מודול חדש
`python_engine/dht.py`.

### 26.1.4 🟠 Peer Exchange (PEX, BEP-11)

**כיום**: המערכת מקבלת peers רק מה-tracker.

**הצעת מימוש**: מימוש הודעת `ut_pex` ב-peer wire protocol
(`MessageType.EXTENDED` עם payload BEP-11). peers מחליפים
ביניהם רשימות peers ידועים — מקטין תלות ב-tracker.

**מאמץ**: 1–2 שבועות. **תלות**: `peer_connection.py`,
`download_manager.py`.

### 26.1.5 🟢 IPv6 support

**כיום**: המערכת תומכת ב-IPv4 בלבד (פרסור compact ב-
`tracker_client.py:_parse_compact_peers` עם 6 בתים לכל
peer).

**הצעת מימוש**: הוספת תמיכה ב-compact6 (18 בתים לכל peer)
לפי BEP-7.

**מאמץ**: ימים בודדים. **תלות**: `tracker_client.py`.

---

## 26.2 קטגוריה 2 — אבטחה והצפנה

### 26.2.1 🟠 MSE/PE (Message Stream Encryption)

**כיום**: peer wire protocol הוא TCP גולמי (פרק 12.2.5).
ISPs יכולים לזהות ולחסום דרך DPI.

**הצעת מימוש**: מימוש BEP-לא-רשמי של MSE/PE — Diffie-Hellman
key exchange + RC4 encryption. תאימות עם clients קיימים
(qBittorrent, Transmission) חיונית.

**מאמץ**: 2–3 שבועות. **תלות**: `peer_connection.py`.

**הערה**: זוהי "obfuscation" ולא security אמיתית; ראה
פרק 12.2.6 ל-SWOT.

### 26.2.2 🟠 BitTorrent v2 (BEP-52) — SHA-256 + Merkle Trees

**כיום**: SHA-1 לפי BEP-3 (פרק 12.2.3).

**הצעת מימוש**: תמיכה כפולה — BEP-3 לקבצי `.torrent`
ישנים, BEP-52 לחדשים (Merkle Tree per file, SHA-256 hashes,
hybrid mode).

**מאמץ**: 4–5 שבועות. **תלות**: `torrent_metadata.py`,
`piece_manager.py`, `peer_connection.py` (handshake חדש).

### 26.2.3 🟢 peer_id רנדומלי לכל torrent

**כיום**: `peer_id` יחיד לכל ה-session (פרק 12.2.7).

**הצעת מימוש**: הזזת `generate_peer_id()` מ-
`Download.__init__` (אחת לכל torrent) במקום מהאתחול
הראשון של ה-process.

**מאמץ**: יום אחד. **תלות**: `download_manager.py`.

### 26.2.4 🟢 TLS לתקשורת tracker

**כיום**: אם ה-tracker חושף `http://`, התקשורת לא מוצפנת.

**הצעת מימוש**: הוספת אזהרה ב-UI אם `announce` הוא HTTP
(לא HTTPS), והצעה לחפש tracker חלופי.

**מאמץ**: יום אחד. **תלות**: `Java GUI`.

---

## 26.3 קטגוריה 3 — חוויית משתמש (UX)

### 26.3.1 🔴 שחזור אוטומטי לאחר crash

**כיום**: `_save_state` כותב JSON, אך אין `_load_state` שמתחזק
את ההורדה בעת startup (פרק 25.5).

**הצעת מימוש**: ב-`DownloadManager.__init__` — סקירת
`data/state/*.json`, יצירה אוטומטית של `Download` אובייקטים
ב-state `Paused`. המשתמש לוחץ "Resume All" כדי להמשיך.

**מאמץ**: 1 שבוע. **תלות**: `download_manager.py`.

### 26.3.2 🟠 שינוי אלגוריתם תוך כדי הורדה

**כיום**: ה-Combos קובעים את האלגוריתם רק ב-`POST /torrents`;
אי-אפשר לשנות אחרי שההורדה התחילה (פרק 20.6).

**הצעת מימוש**: endpoint חדש `PATCH /torrents/<id>/algorithm`
+ כפתורי radio בטבלה הראשית.

**מאמץ**: 3 ימים. **תלות**: `api_server.py`, `Download`,
GUI.

### 26.3.3 🟠 preview של תוכן ה-torrent לפני הורדה

**כיום**: המשתמש לוחץ Add Torrent בלי לראות מה ה-torrent
מכיל (פרק 20.6).

**הצעת מימוש**: dialog ביניים אחרי בחירת הקובץ — מציג
שם, גודל, רשימת קבצים פנימיים (במצב multi-file),
trackers. אישור או ביטול.

**מאמץ**: 1 שבוע. **תלות**: GUI חדש.

### 26.3.4 🟢 dark mode

**כיום**: System Look-and-Feel — תלוי ב-OS (פרק 20.6).

**הצעת מימוש**: שילוב **FlatLaf** library + toggle ב-
toolbar.

**מאמץ**: 2–3 ימים. **תלות**: GUI; הוספת dependency.

### 26.3.5 🟢 קיצורי מקלדת מותאמים

**כיום**: רק קיצורי Swing דיפולטיביים (פרק 20.5.1).

**הצעת מימוש**: רישום `InputMap` + `ActionMap`:
- Ctrl+O: Add Torrent.
- Space: Pause/Resume של הנבחר.
- Delete: Cancel של הנבחר.
- Ctrl+H: History.
- ESC: סגירת dialog.

**מאמץ**: 2 ימים. **תלות**: GUI.

### 26.3.6 🟢 i18n מלא לעברית

**כיום**: רק כותרת החלון בעברית, יתר התוכן באנגלית
(פרק 20.6).

**הצעת מימוש**: `ResourceBundle` עם properties files —
`messages_he.properties` ו-`messages_en.properties`. RTL
layout דרך `ComponentOrientation.RIGHT_TO_LEFT`.

**מאמץ**: 1–2 שבועות. **תלות**: GUI לחלוטין.

---

## 26.4 קטגוריה 4 — ביצועים ויכולת

### 26.4.1 🟠 מודל multi-process עבור 100+ חיבורים

**כיום**: event loop יחיד מטפל בכל החיבורים. עבור ≥ 200
חיבורי TCP פעילים, ה-event loop עלול להפוך לצוואר בקבוק
(פרק 25.2.2).

**הצעת מימוש**: שימוש ב-`multiprocessing` + sharded
event loops — לדוגמה, חצי מה-peers ב-process A, חצי
ב-process B, עם shared queue.

**מאמץ**: 4 שבועות (מורכב). **תלות**: `download_manager.py`
+ `peer_connection.py`.

### 26.4.2 🟢 cache של pieces בזיכרון לטובת seeding

**כיום**: כל בקשת REQUEST מ-peer גורמת לקריאה מהדיסק
(הפעלה אלגוריתמית — אם המערכת תתחיל לתמוך seeding לאחר
26.1.1).

**הצעת מימוש**: LRU cache של 50–100 pieces ב-זיכרון.

**מאמץ**: 1 שבוע. **תלות**: מודול חדש או חלק ב-
`piece_manager.py`.

### 26.4.3 🟢 selective download (file priorities)

**כיום**: בקובץ `.torrent` עם 100 קבצים, כל הקבצים יורדים
ברצף.

**הצעת מימוש**: ב-GUI — בחירת קבצים ספציפיים להוריד; ב-Engine
— ולידציה ש-piece מכיל לפחות אחד מהקבצים הנבחרים.

**מאמץ**: 2 שבועות. **תלות**: `piece_manager.py`,
`torrent_metadata.py`.

### 26.4.4 🟢 streaming download (חלקים בסדר רציף)

**כיום**: rarest-first מוריד באקראי — לא ניתן להתחיל לצפות
בקובץ וידאו לפני סיום.

**הצעת מימוש**: מצב "Sequential" שבו האלגוריתם מוריד מ-
piece 0 ומעלה, עם buffer קטן מראש.

**מאמץ**: 1 שבוע. **תלות**: `piece_manager.py` (אלגוריתם
חדש).

---

## 26.5 קטגוריה 5 — תפעול והרחבה

### 26.5.1 🟠 הפצה כ-executable יחיד

**כיום**: דרושים Python + JDK + תלויות (פרקים 14.2, 23.2).

**הצעת מימוש**: שימוש ב-PyInstaller לאריזת ה-Engine כ-
binary; שילוב עם jpackage ל-Java לאריזת ה-GUI כ-executable
מערכת הפעלה ספציפי (`.exe`/`.app`/`.deb`).

**מאמץ**: 1–2 שבועות. **תלות**: build pipeline.

### 26.5.2 🟠 הוספת REST API נוספים

**כיום**: 13 endpoints. ניתן להרחיב ל-CLI מלא, mobile app,
או web UI.

**הצעת מימוש**: התשתית קיימת — כל endpoint חדש הוא קוד
זול. דוגמאות לעתיד:
- `GET /torrents/<id>/files` — רשימת קבצים פנימיים.
- `POST /torrents/<id>/files/<idx>/priority` — קביעת priority.
- `WS /stream` — WebSocket לעדכוני real-time במקום polling.

**מאמץ**: יום-יומיים לכל endpoint.

### 26.5.3 🟢 לוגים מתמשכים (rolling log files)

**כיום**: לוגים רק ל-stdout ול-buffer בזיכרון.

**הצעת מימוש**: `logging.handlers.RotatingFileHandler` ל-
`data/logs/api_server.log` עם רוטציה יומית, max 10 קבצים.

**מאמץ**: יום אחד. **תלות**: `api_server.py`.

### 26.5.4 🟢 metrics endpoint (Prometheus)

**כיום**: לא משתלב במערכות monitoring סטנדרטיות.

**הצעת מימוש**: `GET /metrics` עם פורמט Prometheus —
מטריקות כמו `active_downloads`, `total_bytes_downloaded`,
`peer_connections`, `hash_failures_total`.

**מאמץ**: 2 ימים. **תלות**: `api_server.py`.

---

## 26.6 סדר עדיפויות מומלץ

| חודש | משימה |
|---|---|
| **חודש 1** | 26.1.1 (incoming server) + 26.1.2 (NAT traversal) |
| **חודש 2** | 26.3.1 (auto-resume) + 26.3.2 (PATCH algorithm) + 26.5.1 (single executable) |
| **חודש 3** | 26.1.3 (DHT) + 26.1.4 (PEX) |
| **חודש 4** | 26.2.1 (MSE/PE) + 26.2.2 (BEP-52) |
| **חודש 5+** | UX polish (26.3.3-26.3.6), performance (26.4), operations (26.5) |

---

## 26.7 סיכום הפרק

הפרק תיעד **23 פיתוחים עתידיים** בחמש קטגוריות:

- **Networking & Protocol** (5): incoming server, NAT, DHT,
  PEX, IPv6.
- **Security & Crypto** (4): MSE/PE, BEP-52, per-torrent
  peer_id, HTTPS warnings.
- **UX** (6): auto-resume, algorithm switching, preview,
  dark mode, keyboard shortcuts, i18n.
- **Performance** (4): multi-process, cache, selective,
  streaming.
- **Operations** (4): single executable, more APIs, log
  rotation, Prometheus.

מסומנים: 4 ב-🔴 (קריטי), 12 ב-🟠 (חשוב), 7 ב-🟢 (מינור).

הסדר המומלץ (סעיף 26.6) שם בעדיפות גבוהה ביותר את שיפורי
ה-networking (incoming server + NAT) שיאפשרו תרומה
מלאה ל-swarm.

הפרק הבא (פרק 27) הוא **ביבליוגרפיה** — מקורות שעליהם
מסתמך הפרויקט.
