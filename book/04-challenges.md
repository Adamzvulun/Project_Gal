# 4. אתגרים

הפרויקט הציג בפניי מספר אתגרים הנדסיים שדרשו לימוד עצמי
ועיון מעמיק בפרוטוקול. הנה האתגרים המרכזיים והפתרונות
שהתקבלו.

**מימוש Bencode קנוני**. פורמט הקובץ `.torrent` משתמש
בקידוד Bencode עם דרישות קנוניות שאינן בולטות לעין:
מפתחות במילון חייבים להיות ממוינים לקסיקוגרפית
כ-byte-strings (לא כ-strings), אסור לרווחים, אסור לזירוס
מוביל ב-integers (`i0e` ולא `i00e`). אי-עמידה בכללים
האלה גוררת `info_hash` שגוי — וכל ה-handshake עם ה-tracker
ועם ה-peers נכשל. הפתרון: מימשתי את ה-encoder/decoder
ידנית מ-bottom-up עם 44 unit tests לכל edge case.

**Peer Wire Protocol כפרוטוקול state-machine**. שלא כמו
HTTP, ה-Peer Wire Protocol הוא TCP גולמי עם הודעות
length-prefixed ו-state machine מתמשך לכל חיבור (am_choking,
am_interested, peer_choking, peer_interested). תקיפה
פוטנציאלית: peer זדוני שולח `length=0xFFFFFFFF`. הפתרון:
ולידציית `MAX_MESSAGE_SIZE=2MB` לפני הקצאת ה-buffer, ושני
טיימאוטים (`CONNECTION_TIMEOUT=30s`, `REQUEST_TIMEOUT=60s`)
שמשחררים peer ש"נתקע" באמצע שליחה.

**אלגוריתם rarest-first בזמן ריצה**. נדרשתי לעקוב אחרי
תדירות ה-pieces ב-swarm בזמן אמת (כל הודעת `HAVE` מעדכנת
מונה אחד), ובו-זמנית לבחור piece לבקש כשפיר מאשר UNCHOKE.
תכננתי `Dict[int, int]` ל-`_peer_frequency` (עדכון O(1)
ב-HAVE) ו-`Dict[str, Set[int]]` ל-`_peer_pieces` (diff
מהיר בעת ניתוק). הבחירה עצמה היא O(N) אבל רצה רק כשיש
unchoke חדש — לכן זה זול בפועל.

**Tit-for-Tat עם optimistic unchoke**. האלגוריתם הקלאסי
של Bram Cohen — לפתוח choke ל-4 ה-peers שתרמו הכי הרבה,
ולעוד אחד אקראי (optimistic) כדי לאפשר ל-peer חדש להכניס
את עצמו לדירוג. דרשתי לשמור per-peer `bytes_downloaded`
מעודכן בזמן אמת בתוך כל `PeerConnection`, ולהריץ את
הלוגיקה כל 10 שניות (`CHOKE_INTERVAL`).

**שילוב asyncio עם Flask**. ה-API server רץ ב-Flask
(סינכרוני), בעוד שכל הלוגיקה של ההורדה רצה ב-asyncio event
loop. הגשר ביניהם — `_run_async` — משתמש ב-
`asyncio.run_coroutine_threadsafe` כדי להגיש קואורוטינה
ל-event loop ולחכות לתוצאה. ה-event loop רץ ב-daemon
thread שמופעל בעת startup.

**חישוב SHA-1 חוסם**. `Piece.verify_hash` אורך ~2ms על
piece של 1MB. אם רץ ב-event loop הראשי, הוא חוסם את כל
ה-coroutines האחרות. הפתרון: `loop.run_in_executor(self._executor,
verify_piece, idx)` עם `ThreadPoolExecutor(max_workers=2)`.
אותו pattern חל גם על `_write_piece_sync` (כתיבה לדיסק).

**Integration בין Python ל-Java**. שתי השפות לא יודעות
לדבר ביניהן ב-native — הגשר חייב להיות פרוטוקולי. בחרתי
ב-REST/JSON על loopback (`localhost:5000`). זה מתועד היטב,
בודק ב-`curl` בנפרד מ-Java, ומאפשר לעתיד להוסיף clients
נוספים בלי לגעת ב-Engine.

**אבטחה מול peers זדוניים**. peers ב-swarm פתוח לא
מהימנים. תכננתי מערכת מוניטין שמסמנת peer אחרי 3 שגיאות
hash או 5 הפרות פרוטוקול (`SecurityManager`), ומונעת
ניסיונות התחברות חוזרים מ-`_connect_to_peers`. ראה פרק 12.

**NAT וחיבורים נכנסים**. המערכת מאחורי NAT לא יכולה לקבל
חיבורים נכנסים בלי port mapping. בחרתי לא לממש NAT
traversal (UPnP/STUN) בגרסה הראשונה — המערכת רק יוזמת
חיבורים יוצאים. זה מגביל את התרומה ל-swarm אבל מפשט
משמעותית את הפיתוח. מתועד כפיתוח עתידי.
