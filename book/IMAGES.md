# IMAGES.md – רשימת תרשימים, צילומי מסך ואיורים

קובץ זה מרכז את כל התרשימים, צילומי המסך והאיורים שיש לשלב בספר.
הרשימה מתעדכנת באופן שוטף תוך כדי כתיבת הפרקים. עבור כל פריט מצוין:

- **מס'**: מזהה ייחודי לאיור (Fig-01, Fig-02, ...).
- **פרק**: הפרק והסעיף בו ישולב.
- **מיקום בקובץ**: עוגן/נקודת שילוב מדויקת בתוך קובץ הפרק.
- **סוג**: תרשים זרימה / תרשים ארכיטקטורה / תרשים תקשורת / ERD / UML / צילום מסך.
- **תיאור מפורט**: מה התרשים אמור להציג, מהם הרכיבים, החצים, התוויות.
- **סטטוס**: דרוש / נוצר / שולב.

---

## Fig-01 – סריקת הצעת הפרויקט החתומה

- **פרק**: 1 (הצעת הפרויקט שאושרה) — סעיף 1.1 / 1.17.
- **מיקום בקובץ**: `01-approved-proposal.md`, מיד אחרי כותרת הפרק
  (סעיף 1.1 *"פתיח לפרק"*); דף החתימות בסוף הפרק (סעיף 1.17).
- **סוג**: סריקת מסמך (PDF / תמונה).
- **תיאור מפורט**: יש לשלב את כל עמודי ה-PDF המקורי
  `הצעת פרוייקט - אדם זבולון 329441273 V2.2.pdf` (השמור בריפו) כסריקה
  בתוך המסמך — דף השער, תוכן העניינים של ההצעה, ולפחות עמוד החתימות
  האחרון (עמ' 23 ב-PDF המקורי) שעליו מופיעות שלוש החתימות: סטודנט,
  מנחה, רכז מגמה. ההגשה הסופית ב-Word צריכה לכלול את כל 23 העמודים
  של ההצעה כסריקה רציפה או כנספח מודפס.
- **סטטוס**: דרוש.

---

## Fig-02 – תרשים ארכיטקטורה כללי (Top-Down) של המערכת

- **פרק**: 1 (הצעת הפרויקט) — סעיף 1.8.1, וכן יצוטט שוב בפרק 11.
- **מיקום בקובץ**: `01-approved-proposal.md`, מיד אחרי הפסקה הפותחת
  של סעיף 1.8.1 *"חלוקה לשכבות ולמודולים"*.
- **סוג**: תרשים ארכיטקטורה.
- **תיאור מפורט**: תרשים זהה במהותו לתרשים בעמ' 8 של ההצעה המקורית.
  התרשים צריך להציג שתי שכבות עיקריות:
  - **Client** (חלק עליון) — מכיל את `Java GUI Client` עם שני
    תת-רכיבים: `Java GUI (Swing)` ו-`HTTP Client (REST calls)`.
  - **BitTorrent Engine** (חלק תחתון) — מכיל את הרכיבים:
    `REST API Server (Flask)`, `TorrentMetadata (Bencode parsing)`,
    `Security (Validation & Logging)` בשורה עליונה; `DownloadManager
    (choke/unchoke)` במרכז; `TrackerClient (HTTP/HTTPS)`,
    `PieceManager (rarest-first)`, `PeerConnection* (TCP sockets)`
    בשורה תחתונה.
  - חצים: מ-Java GUI ל-REST API Server (תווית `REST API`); מ-Flask
    אל DownloadManager; מ-DownloadManager אל שלושת הרכיבים התחתונים;
    מ-TrackerClient לרכיב חיצוני `Tracker Servers` (תווית `announce /
    response`); מ-PeerConnection לרכיב חיצוני `Peers in Swarm`
    (תווית `peer wire protocol`).
  - יש להציג את הגבולות הלוגיים של ה-Client לעומת ה-Engine באמצעות
    מסגרות מודגשות, כדי להבהיר שמדובר בשני תהליכים נפרדים על אותה
    מכונה המתקשרים דרך REST.
- **סטטוס**: דרוש.

---

## Fig-03 – תרשים רצף הורדה (Sequence Diagram)

- **פרק**: 1 (הצעת הפרויקט) — סעיף 1.9.2, וכן יצוטט שוב בפרק 11
  ובפרק 15.
- **מיקום בקובץ**: `01-approved-proposal.md`, בסוף סעיף 1.9.2
  *"תקשורת בין peers – Peer Wire Protocol"*.
- **סוג**: תרשים רצף (Sequence Diagram) ברוח UML.
- **תיאור מפורט**: תרשים זהה במהותו לתרשים בעמ' 12 של ההצעה המקורית.
  *Lifelines*: `Java GUI`, `Python REST API`, `DownloadManager`,
  `TrackerClient`, `PeerConnection`, `Remote Peer`, `PieceManager`
  (PM). זרימה:
  1. `Java GUI → Python REST API`: `POST /torrents` עם קובץ `.torrent`.
  2. `REST API → DownloadManager`: `startDownload(metadata)`.
  3. `DownloadManager → TrackerClient`: `announce(info_hash, stats)`,
     החזרה: `peers[]`.
  4. *loop* על peers: `DownloadManager → PeerConnection`: `connect(ip,
     port)`; `PeerConnection → Remote Peer`: `handshake(info_hash,
     peer_id)`; `Remote Peer → PeerConnection`: `handshake(...)`,
     `bitfield`.
  5. *loop* (עד שהקובץ הושלם):
     - `DownloadManager → PieceManager`: `selectPiece(rarest-first)`,
       החזרה: `pieceIndex`.
     - `DownloadManager → PeerConnection`: `request(pieceIndex,
       blocks)`; `PeerConnection → Remote Peer`: `request(...)`;
       `Remote Peer → PeerConnection`: `piece blocks`.
     - `PeerConnection → DownloadManager`: `data(pieceIndex, block)`;
       `DownloadManager → PieceManager`: `submitBlock(pieceIndex,
       block)`; *הערה*: "If piece complete & hash OK".
- **סטטוס**: דרוש.

---

## Fig-04 – תרשים מרכיבי מערכת BitTorrent

- **פרק**: 6 (רקע תיאורטי) — סעיף 6.1.2 *"מבנה מערכת BitTorrent"*.
- **מיקום בקובץ**: `06-theoretical-background.md`, מיד אחרי
  סעיף 6.1.2.
- **סוג**: תרשים מושגי / היררכי.
- **תיאור מפורט**: תרשים המציג את ארבעת המרכיבים התפקודיים של
  מערכת BitTorrent ואת היחסים ביניהם:
  - בצד שמאל למעלה: **קובץ `.torrent`** (קופסה מלבנית) — מתאר
    את התוכן (`announce`, `info` dict, `pieces[]`, `info_hash`).
  - בצד ימין למעלה: **Tracker** (מסד נתונים / קופסת שרת) — מחזיק
    טבלה: `info_hash → [peer_1, peer_2, ...]`.
  - במרכז: **Swarm** (מעגל גדול) — מכיל את כלל ה-peers.
  - בתוך ה-swarm: **Seeders** (סמל ירוק עם 100%) ו-**Leechers**
    (סמל צהוב עם אחוז חלקי).
  - חצים:
    - מ-Client (`.torrent` בידיו) → Tracker: `announce(info_hash)`.
    - מ-Tracker → Client: `peers[]`.
    - בין כל זוג peers ב-swarm: חץ דו-כיווני המסומן
      `Peer Wire Protocol`.
  - יש להציג את הגבול בין השכבה הלוגית (קובץ torrent +
    info_hash + tracker — שכבת *Discovery*) לבין שכבת ה-Data
    Transfer (peers ב-swarm) באמצעות קו מקווקו.
- **סטטוס**: דרוש.

---

## Fig-05 – תרשים Context (Top-Down רמה 0)

- **פרק**: 11 (ארכיטקטורה) — סעיף 11.1.1.
- **מיקום בקובץ**: `11-architecture.md`, בסעיף 11.1.1.
- **סוג**: Context Diagram (UML / DFD level 0).
- **תיאור מפורט**: תיבה שחורה יחידה במרכז עם הכותרת *"BitTorrent
  Distributed File Sharing System"*. סביבה ארבעה שחקנים חיצוניים,
  עם חצים דו-כיווניים אליה: (1) `User` משמאל למעלה — אינטראקציה
  עם GUI; (2) `Tracker` (סמל שרת) מימין למעלה — תקשורת HTTP
  announce/response; (3) קבוצת `Peers` (`Peer 1`, `Peer 2`, `Peer
  N`) מתחת — תקשורת TCP/BEP-3. כל חץ עם תווית קצרה
  (`HTTP`, `TCP`, `User Actions`).
- **סטטוס**: דרוש.

---

## Fig-06 – תרשים Top-Down רמה 2 (תת-מערכות)

- **פרק**: 11 (ארכיטקטורה) — סעיף 11.1.3.
- **מיקום בקובץ**: `11-architecture.md`, בסעיף 11.1.3.
- **סוג**: תרשים ארכיטקטורה מפורט.
- **תיאור מפורט**: שני מלבנים גדולים זה לצד זה, המייצגים את שני
  התהליכים:
  - **Java GUI Process** (שמאל): בתוכו תיבה ראשית
    `TorrentClientGUI (Main)`; שתי תיבות תחת — `ApiService`
    (HttpClient) ו-`AlgorithmStatsDialog` (Modal).
  - **Python Engine Process** (ימין): שלוש שורות תיבות:
    שורה 1 — `Flask REST API Server`; שורה 2 — `DownloadManager`
    (במרכז) המקושר אל `PieceManager`, `PeerConnection`,
    `TrackerClient`; שורה 3 — `Security`, `TorrentMetadata` (משמאל)
    ו-`JSON state files`, `SQLite (history.db)` (מימין).
  - חץ דו-כיווני באמצע בין שני התהליכים, עם תווית
    `REST/JSON over HTTP — localhost:5000`.
  - חצים יוצאים מ-`TrackerClient` ו-`PeerConnection` החוצה לקצוות
    התרשים (מסומנים `→ Tracker` ו-`→ Peers in Swarm`).
- **סטטוס**: דרוש. ניתן להתבסס על התרשים בעמ' 8 של הצעת הפרויקט,
  אך בגרסה מורחבת לפי תוכן הסעיף.

---

## Fig-07 – תרשים ארכיטקטורת רשת

- **פרק**: 11 (ארכיטקטורה) — סעיף 11.4.2.
- **מיקום בקובץ**: `11-architecture.md`, בסעיף 11.4.2.
- **סוג**: תרשים זרימת רשת.
- **תיאור מפורט**: שלוש שכבות תקשורת מוצגות בשלושה צבעים שונים:
  - **שכבה ירוקה (Local IPC)**: חץ דו-כיווני בין תיבת `Java GUI`
    לתיבת `Python Engine`, עם תווית `HTTP/JSON · localhost:5000`.
  - **שכבה כחולה (HTTP Tracker)**: חץ דו-כיווני בין `Python
    Engine` לתיבה חיצונית `Tracker (HTTP/HTTPS)`, עם תווית
    `Bencode response · port 80/443`.
  - **שכבה כתומה (Peer Wire Protocol)**: חץ מ-`Python Engine`
    היוצא לקבוצה של ~5 תיבות `Peer 1..5` (מיוצגות כ-swarm), עם
    תווית `TCP/BEP-3 · port 6881 + dynamic`.
  - בתחתית התרשים, מקרא הסבר על כל שכבה: פרוטוקול, רוחב פס
    טיפוסי, ודרישות אבטחה.
- **סטטוס**: דרוש.

---

## Fig-08 – תרשים מודל איום (Threat Model Diagram)

- **פרק**: 12 (אבטחת מידע) — סעיף 12.1.1.
- **מיקום בקובץ**: `12-security.md`, בסוף סעיף 12.1.1 (לפני
  טבלת וקטורי האיום ב-12.1.2).
- **סוג**: תרשים מודל איום (Trust-Boundary Diagram).
- **תיאור מפורט**: התרשים מציג את **המערכת כתיבה מרכזית** עם
  גבולות אמון (trust boundaries) מסומנים בקווים מקווקווים, ו-3
  מקורות איום חיצוניים:
  - **תיבה מרכזית** (`BitTorrent Client`) — מחולקת לשני
    תת-איזורים: `Java GUI` ו-`Python Engine`, עם קו ירוק
    דק (Trust Boundary פנימי = loopback).
  - **שחקן עוין 1**: `Malicious Peer` — תיבה אדומה, מחוץ
    לגבול האמון; חץ דו-כיווני אדום אליה עם תווית `TCP/BEP-3
    (T1–T7)`.
  - **שחקן עוין 2**: `Compromised Tracker` — תיבה כתומה, מחוץ
    לגבול האמון; חץ דו-כיווני כתום אליה עם תווית `HTTP/HTTPS
    (T8, T11)`.
  - **שחקן עוין 3**: `Network Attacker (MITM/Eavesdropper)` —
    תיבה צהובה הממוקמת **על גבי החצים** של שני השחקנים
    הקודמים, עם תווית `T9, T10`.
  - בכל חץ צמודה רשימה של מזהי האיום (T1–T11) שהוא נושא,
    בהתאמה לטבלה ב-12.1.2.
  - מקרא צבעים: אדום=peer, כתום=tracker, צהוב=רשת,
    ירוק=loopback פנימי.
- **סטטוס**: דרוש.

---

## Fig-09 – תרשים זרימת הגנה (Defense Flow Diagram)

- **פרק**: 12 (אבטחת מידע) — סעיף 12.1.6.
- **מיקום בקובץ**: `12-security.md`, בסוף סעיף 12.1.6 (לפני
  טבלת הסיכום ב-12.1.7).
- **סוג**: תרשים זרימה (Flowchart).
- **תיאור מפורט**: התרשים מציג את **שמונת שכבות ההגנה** כשרשרת
  decision-points, החל מקבלת ה-handshake וכלה בכתיבה לדיסק.
  כל שלב הוא רומבוס (החלטה) או מלבן (פעולה); כל החלטה שלילית
  ("FAIL") מוליכה לתיבת `Reject + report to SecurityManager`,
  וכל החלטה חיובית ("OK") ממשיכה לשלב הבא:
  1. **Handshake validation** (אורך 68, pstr, info_hash) →
     FAIL ⇒ `PeerConnectionError`.
  2. **Message length ≤ 2 MB?** → FAIL ⇒ `protocol_violation`.
  3. **Valid msg_id (0–8)?** → FAIL ⇒ drop silently.
  4. **piece_index in range?** → FAIL ⇒ `protocol_violation`.
  5. **Block buffered into piece**.
  6. **All blocks received?** → לא: חזרה לשלב 2 לקריאת הודעה
     הבאה; כן: המשך.
  7. **SHA-1 == expected_hash?** → FAIL ⇒
     `report_hash_failure` → אם `should_ban` ⇒ ban.
  8. **Write piece to disk**.
  - בצד התיבות הרלוונטיות תוצג כתובית עם הקובץ והפונקציה
    האחראית (`peer_connection.py:_receive_handshake`,
    `piece_manager.py:verify_hash`, וכו').
  - מקרא: ירוק=זרימה תקינה, אדום=זרימת כשל/באן.
- **סטטוס**: דרוש.

---

<!-- פריטים נוספים יתווספו עם התקדמות כתיבת הפרקים -->
