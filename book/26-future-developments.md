# 26. פיתוחים עתידיים

הפרק מציג שיפורים מתוכננים לגרסה הבאה של המערכת,
מקובצים לפי תחום. הסדר בכל קבוצה הוא לפי עדיפות
(החשוב ראשון).

## רשת ופרוטוקול

**שרת listen נכנס (Incoming Peer Server)**. כיום
המערכת רק יוזמת חיבורים יוצאים ולא מקבלת חיבורים
נכנסים, ולכן היא לא תורמת ל-swarm מהמלוא הפוטנציאל
שלה. מימוש: הוספת `asyncio.start_server` על פורט 6881
ב-`Download._download_loop`. כל חיבור נכנס יקבל
`PeerConnection` עם תפקיד "incoming". אומדן מאמץ: 1–2
שבועות.

**NAT Traversal (UPnP / STUN)**. גם אם נוסיף listen
server, המערכת מאחורי NAT לא תוכל לקבל חיבורים מבחוץ.
דרוש מנגנון Port Mapping — שילוב `miniupnpc` או STUN
לזיהוי כתובת ציבורית + hole punching. אומדן: 2–3
שבועות.

**DHT (BEP-5)**. המערכת תלויה לחלוטין ב-tracker; אם
הוא נופל אין דרך לגלות peers. מימוש Kademlia DHT
יבטל את התלות. אומדן: 4–6 שבועות (מימוש מורכב).

**Peer Exchange (PEX, BEP-11)**. peers מחליפים ביניהם
רשימות peers דרך הודעת `ut_pex` בפרוטוקול. מקטין תלות
ב-tracker ומאיץ את הצטרפות peers חדשים ל-swarm.
אומדן: 1–2 שבועות.

**IPv6**. כיום compact peer parsing תומך רק ב-IPv4
(6 בתים לכל peer). הוספת compact6 (18 בתים) לפי
BEP-7. אומדן: ימים בודדים.

## אבטחה והצפנה

**MSE/PE (Message Stream Encryption)**. עוקף DPI של
ISPs. הצפנה מבוססת Diffie-Hellman + RC4. תאימות עם
qBittorrent ו-Transmission חיונית. אומדן: 2–3 שבועות.

**BitTorrent v2 (BEP-52)**. SHA-256 במקום SHA-1,
Merkle Trees לאימות חלקי piece, hybrid mode לתאימות
לאחור. אומדן: 4–5 שבועות.

**peer_id רנדומלי לכל torrent**. כיום `peer_id` יחיד
לכל ה-session, מה שמאפשר correlation בין torrents
שונים. הזזת `generate_peer_id()` לתוך `Download.__init__`.
אומדן: יום.

## חוויית משתמש

**שחזור אוטומטי לאחר crash**. `_save_state` כבר כותב
JSON, אבל אין `_load_state` שמתחזק את ההורדה בעת
startup. מימוש: ב-`DownloadManager.__init__` סקירה של
`data/state/*.json`, יצירה אוטומטית של `Download`
ב-state `Paused`. אומדן: שבוע.

**שינוי אלגוריתם תוך כדי הורדה**. כיום ה-Combos קובעים
את האלגוריתם רק ב-`POST /torrents`. הוספת endpoint
`PATCH /torrents/<id>/algorithm` + כפתורי radio בטבלה.
אומדן: 3 ימים.

**preview של תוכן ה-torrent לפני הורדה**. dialog ביניים
אחרי בחירת הקובץ עם שם, גודל, רשימת קבצים פנימיים,
trackers. אומדן: שבוע.

**dark mode**. שילוב **FlatLaf** library + toggle
ב-toolbar. אומדן: 2–3 ימים.

**קיצורי מקלדת** ו-**i18n מלא לעברית**. אומדן: שבוע
לכל אחד.

## ביצועים ויכולת

**מודל multi-process עבור 100+ חיבורים**. event loop
יחיד עלול להיות צוואר בקבוק בעומס גבוה. sharded event
loops + shared queue. אומדן: 4 שבועות.

**LRU cache של pieces בזיכרון**. רלוונטי כשנפעיל
seeding. אומדן: שבוע.

**Selective download (file priorities)**. בחירת קבצים
ספציפיים להוריד ב-multi-file torrent. אומדן: שבועיים.

## תפעול

**הפצה כ-executable יחיד** — PyInstaller + jpackage
כדי לקבל `.exe`/`.app`/`.deb` בלי דרישת Python ו-JDK
מותקנים. אומדן: 1–2 שבועות.

**rolling log files** ב-`data/logs/` עם רוטציה יומית.
אומדן: יום.

**`GET /metrics` בפורמט Prometheus** — לאינטגרציה
במערכות monitoring סטנדרטיות. אומדן: 2 ימים.

## סדר עדיפויות מומלץ

חודש 1: incoming server + NAT traversal. חודש 2:
auto-resume + algorithm switching + single executable.
חודש 3: DHT + PEX. חודש 4: MSE/PE + BEP-52. חודש 5+:
UX polish, performance, operations.
