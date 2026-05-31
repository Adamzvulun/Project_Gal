<div dir="rtl">

# שאלות שלא נענו במצגת V3 - תשובות מוכנות

מתוך 63 השאלות שהמורה שלח (15 תרגילי עומק, 5 שאלות פסילה, 20 ארכיטקטורה, 20 קוד/אלגוריתמים, 3 שוברות מערכת), שלוש לא קיבלו מענה ישיר בדק. הקובץ הזה מספק תשובה מלאה לכל אחת, עם file:line מהקוד - מוכן לדיבור אם הבוחן ישאל.

הסגנון זהה לתמליל - גוף ראשון, רגוע, מסביר *למה*, מודה במגבלות כשרלוונטי.

---

## שאלת ארכיטקטורה 12

> **"איזה רכיב אחראי למנוע מצב שבו אותו Piece יורד פעמיים במקביל?"**

> "התשובה היא ה-DownloadManager, באמצעות מבנה נתונים שנקרא `_peer_piece` - מילון שממפה peer ל-piece שהוא מטפל בו כרגע. הרעיון הוא **assignment 1-ל-1**: בכל רגע נתון, peer אחד מטפל ב-piece אחד. כשאני מקצה piece ל-peer, ה-piece נכנס למילון; כשהוא מסיים, יוצא. peer אחר שמבקש משימה לא יכול לקבל piece שכבר נמצא במילון.

> בקוד זה ב-`download_manager.py:144` להגדרה (`self._peer_piece: Dict[str, int] = {}`), והלוגיקה ב-`_request_from_peer` בערך משורה 507 - שם בודקים אם ה-peer כבר עובד על משהו, ואם לא, מקצים piece שלא מוקצה ל-peer אחר (`assigned_pieces = set(self._peer_piece.values())`). זאת השכבה הראשונה.

> אבל המציאות יותר מורכבת, ולא רוצה להציג את זה פשוט מדי. יש שלושה תרחישי קצה.

> **ראשון - choke או disconnect באמצע piece.** כש-peer מנותק או מוריד אותי ל-choke באמצע, אני מנקה את ה-assignment שלו - השורות סביב 295-296 ו-405-407 ו-422-424. ה-piece חוזר להיות זמין ל-peer אחר. בלי הניקוי הזה, ה-piece היה תקוע - מסומן 'מוקצה' לעולם.

> **שני - endgame.** בסוף הורדה, כשנשארו רק כמה pieces חסרים, ה-1-ל-1 פוגע ב-throughput - אם יש פי שלוש peers מ-pieces חסרים, רוב ה-peers בטלים. ב-`_request_from_peer` משורה 538 יש fallback ל-IN_PROGRESS: peer ש'אין לו עבודה' לפי המילון מקבל piece שכבר ב-progress, ויכול לבקש את ה-blocks שעדיין לא נשלחו. כן, זה אומר שאותו piece *כן* יכול לרדת מיותר מ-peer אחד באותו זמן - אבל זה מכוון, וזאת הנקודה שבה רוצים את זה.

> **שלישי - duplicate completion guard.** אם בכל זאת הגיעה הודעת PIECE עבור piece שכבר הושלם (יכול לקרות בגלל קריאה במקביל), ב-`_on_peer_message` סביב שורה 382 יש בדיקה: 'Guard: skip if piece is already completed' - וה-block נזרק בשקט. אז גם כשהמערכת רואה הודעה כפולה, היא לא קורסת ולא מבזבזת זמן על אימות SHA-1 כפול.

> שלושת המנגנונים האלה יחד נותנים: בזמן הרגיל - peer-לכל-piece, ב-choke או disconnect - cleanup, ב-endgame - שכפול מבוקר. זאת לא 'שכבת מניעה אחת', זאת מערכת של שלוש שכבות."

**הפניות לקוד:**
- `download_manager.py:144` - הגדרת `_peer_piece`
- `download_manager.py:507-543` - לוגיקת assignment ו-endgame ב-`_request_from_peer`
- `download_manager.py:382` - duplicate completion guard ב-`_on_peer_message`
- `download_manager.py:296`, `405-407`, `422-424` - ניקוי על choke/disconnect

---

## שאלת ארכיטקטורה 19

> **"איזה רכיב צפוי להיות צוואר הבקבוק הראשון: TrackerClient / PeerConnection / PieceManager / Disk I/O / Hash Verification? נמק."**

> "אני אהיה ישיר - **Disk I/O ו-Hash Verification, יחד**. שניהם נשברים ראשונים, וזאת בדיוק הסיבה ששניהם רצים ב-`ThreadPoolExecutor` ולא ב-event loop. אני אעבור על חמשת המועמדים אחד אחד.

> **TrackerClient לא צוואר בקבוק.** הוא מתעורר פעם בערך בשלושים דקות לפי ה-interval שה-tracker ביקש. גם 100 trackers בו-זמנית לא היו עולים מ-1% CPU. מחוץ למרוץ.

> **PeerConnection לא צוואר בקבוק כל עוד יש asyncio.** thread יחיד מנהל 50 חיבורים שכולם 99% מהזמן ממתינים ל-I/O. ה-async hands-off הוא בדיוק מה שמונע מזה להפוך לבעיה.

> **PieceManager לא צוואר בקבוק** - rarest-first הוא O(n) ב-pieces (לא ב-peers), `_peer_frequency` מתעדכן ב-O(1), והכול ב-RAM. עבור 1,000 pieces ו-200 peers זה כמה מגה ושאילתה אחת לבחירה. אפילו ב-50,000 pieces זה עדיין מתחת למילישנייה.

> **נשארו שניים, ויחד הם 'הראשון לישבר'.** Hash Verification מבצע SHA-1 על piece של 256 קילו - חישוב סינכרוני שאם יקרה ב-event loop הוא חוסם את כל ה-50 חיבורים יחד. Disk I/O - כתיבה של 256 קילו על דיסק רגיל זה כמה מילישניות, על SSD פחות, על HDD לפעמים עשרות. בשניהם, אם זה רץ ב-event loop, כל ה-peers קופאים יחד עד שהפעולה גומרת.

> **בדיוק לכן שניהם מועברים ל-executor.** ב-`download_manager.py:141` הגדרתי `ThreadPoolExecutor(max_workers=2)`. ב-`_on_peer_message` סביב שורה 393, אחרי שה-piece שלם, יש `await loop.run_in_executor(self._executor, self.piece_manager.verify_piece, piece_idx)` ואז `await loop.run_in_executor(self._executor, self._write_piece_sync, piece_idx)`. שני ה-`run_in_executor` הם הסיגנל שהקוד 'יודע' שאלו הצוואר.

> **דרך אחרת לחשוב על זה:** במקום לשאול 'איזה רכיב נשבר ראשון', אפשר לשאול 'איזה רכיב היה צריך הגנה מיוחדת בקוד?'. התשובה היא בדיוק שני אלה. למבני נתונים אחרים לא נתתי שום עטיפה מיוחדת - הם רצים ב-event loop ואין בעיה. רק SHA-1 וכתיבה לדיסק קיבלו executor. זאת הוכחה תכנונית שהם הצוואר.

> **מגבלה שאני רוצה להודות בה** - executor עם שני workers בלבד מספיק ל-50 חיבורים אבל יהיה צוואר חדש בקנה מידה של מאות הורדות במקביל. ב-production היה צריך max_workers לפי `os.cpu_count()` - תיקון של שורה אחת, מתועד כאופטימיזציה עתידית."

**הפניות לקוד:**
- `download_manager.py:141` - הגדרת `_executor` עם 2 workers
- `download_manager.py:393-400` - הקריאות ל-`verify_piece` ול-`_write_piece_sync` דרך executor
- `download_manager.py:461-462` - גם קריאת block מהדיסק (upload path) ב-executor
- `download_manager.py:804`, `837-840` - מימוש `_write_piece_sync` ו-`_write_piece`

---

## שאלת קוד/אלגוריתמים 18

> **"ב-TrackerClient מבוצעת בקשת GET /announce. מדוע מועברים downloaded uploaded left, ולמה Tracker צריך לדעת אותם?"**

> "השאלה הזאת מצויינת כי היא מבדילה בין 'מי שמכיר את הפרוטוקול שטחית' לבין 'מי שקרא את BEP-3'. בכל announce אני שולח שלושה מספרים: uploaded (כמה בייטים העליתי מתחילת ההורדה), downloaded (כמה הורדתי), ו-left (כמה עוד נשאר לי). הם נמצאים בקוד ב-`tracker_client.py:157-159` כשדות מצב, וב-`tracker_client.py:194-196` הם נכנסים לפרמטרים של ה-GET. שלוש סיבות *שונות* למה ה-tracker צריך אותם.

> **סיבה ראשונה - הבחנה בין seeder ל-leecher.** כש-left=0 פירושו שגמרתי להוריד, ואני seeder. כש-left>0 אני leecher. ה-tracker בונה מזה את שני המספרים הראשיים שהוא מחזיר - `complete` ו-`incomplete` - מספר ה-seeders ומספר ה-leechers ב-swarm. אלו המספרים שאתה רואה בכל לקוח ('15 seeders, 200 leechers'), והם משפיעים על החלטות peer selection ברמה הגלובלית - swarm עם הרבה seeders ומעט leechers נמצא במצב 'בריא', ולקוחות חכמים מתאימים את ההתנהגות.

> **סיבה שנייה - אכיפת יחס ב-trackers פרטיים.** בקהילות BitTorrent פרטיות (סצנה מוקלטת, ranks אקדמיים, archive.org) יש דרישת share ratio - שעליתי לפחות X% ממה שהורדתי. ה-tracker רושם את uploaded/downloaded לכל peer לאורך זמן, מחשב יחס, וחוסם משתמשים שלא תורמים. בלי השליחה הזאת, האכיפה לא הייתה אפשרית. אצלי אין tracker פרטי, אבל הפרוטוקול תומך - וזאת ההבחנה.

> **סיבה שלישית, וזאת הכי קריטית - אירוע `completed`.** כש-left מגיע ל-0, אני שולח announce עם event=completed (ב-`tracker_client.py:209` רואים את ה-`event` בלוג). ה-tracker מסמן אותי כ-seeder מהרגע הזה ומונה +1 ב-`complete`. בלי שליחת left, ה-tracker לא היה יודע שעברתי ל-seeding. גם ה-event=started הראשון וה-event=stopped בסגירה מסתמכים על הסטטיסטיקות.

> **מה ה-tracker *לא* עושה עם זה?** הוא לא בודק שאני אמיתי - אני יכול לשלוח uploaded=999GB ולשקר. הוא מאמין לי. זאת חולשה ידועה של פרוטוקול ה-tracker, וזה אחד מהדברים ש-DHT וגם trackers פרטיים מנסים לפתור בדרכים אחרות (DHT לא מסתמך על self-reporting; trackers פרטיים מצליבים מול חברי swarm אחרים).

> **למה זה לא היה ב-slide של ה-flow?** כי בסקופ של ההצגה התמקדתי במה ה-tracker *מחזיר* (רשימת peers), לא במה אני *שולח*. בדיעבד, מילה אחת ב-slide 14 על שלושת המספרים הייתה משלימה את התמונה - מתועד לתיקון."

**הפניות לקוד:**
- `tracker_client.py:157-159` - שדות `uploaded`, `downloaded`, `left` ב-TrackerClient
- `tracker_client.py:175-178` - חתימת `announce` עם הפרמטרים האופציונליים
- `tracker_client.py:194-196` - הזרקת הערכים ל-params של הבקשה
- `tracker_client.py:209` - לוג של event ו-left בכל announce

---

## איך להשתמש בקובץ הזה

- בזמן ההצגה - אל תקרא משם. תכיר את התשובות.
- אם הבוחן שואל את אחת השלוש - תענה בעל-פה. עדיף לקצר.
- כל תשובה תוכננה לדיבור של 60-90 שניות בעל-פה. בקצב נורמלי, כל ה-3 יחד = ~4 דקות.
- אם הבוחן רוצה לראות בקוד - יש file:line בסוף כל תשובה. תפתח את הקובץ בעורך ותראה לו.

</div>
