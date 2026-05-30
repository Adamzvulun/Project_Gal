<div dir="rtl">

# 10 תרגילי עומק + 7 תרגילי קוד — תשובות מלאות

מסמך לימוד שעונה על כל אחד מ-17 התרגילים בדיוק לפי המבנה שהבוחן ביקש. לכל תרגיל: תשובות ל-5 השאלות, מילים ספציפיות מרשימת ה"חובה להתייחס", והפנייה לקובץ:שורה בקוד שאפשר להראות. הסגנון פה הוא "ספר", לא "שקופית" - השקופית היא הסיכום, וזה התוכן שמאחוריו.

טון: לא להסתיר חולשות. הבוחן ביקש "ביקורת עמוקה" - הוא מצפה שאגיד היכן זה לא מושלם. הודאה בעיני הבוחן הזה היא נקודות, לא הפסד.

---

## חלק א — 10 תרגילי עומק

---

### תרגיל 1 — למה rarest-first הוא הרבה יותר מ"בחירת החלק הנדיר"

**בפרויקט מתואר:** rarest-first piece selection
**קוד:** `python_engine/piece_manager.py` — `select_piece_rarest_first`

#### 1. מדוע rarest-first הוא למעשה בעיית optimization גלובלית?

המטרה הגלויה של האלגוריתם נראית מקומית: "תבחר piece שלא הרבה peers מחזיקים". אבל המטרה האמיתית, שאף peer בודד לא מחשב במפורש, היא **global vs local optimization** - שלכל piece ב-swarm יישארו מספיק עותקים גם כשה-seeders עוזבים. זאת פונקציית מטרה משותפת לכל ה-swarm, ו-rarest-first הוא ה-heuristic הלוקאלי שכל peer מבצע כדי לקרב את ה-swarm לקירוב טוב שלה. הסכימה של כל ההחלטות המקומיות מסתכמת לאפקט גלובלי - **distributed availability** עולה. זה דפוס קלאסי של אופטימיזציה מבוזרת: אופטימום גלובלי שמושג בלי מתאם מרכזי, רק מ-N heuristics לוקאליים זהים.

#### 2. כיצד rarity distribution משפיע על survivability של ה-swarm?

**Swarm robustness** מתבטא ביכולת ה-swarm לשרוד עזיבה של peers, ובמיוחד של seeders. אם piece מסוים קיים רק אצל seeder יחיד, **rare piece starvation** הוא הסיכון: ברגע שהוא מתנתק, ה-piece אבד מה-swarm לנצח, וכל מי שלא הספיק לקבל אותו לא יוכל להשלים את הקובץ. rarest-first מתעדף הפצה של חתיכות נדירות *לפני* השכיחות, כך שעותקים מתרבים במהירות וה-survivability עולה דרמטית. אצלי בניסוי - ב-`data/experiments/comparison_summary.csv` - ה-peer בשם `full` (היחיד שמחזיק את החתיכות 8-15) מספק *בדיוק* 512KB ב-rarest-first - כל בקשות החצי הנדיר ממוקדות אליו, כך שהם מופצים החוצה במהירות.

#### 3. מדוע local peer view עלול להטעות?

כל peer ב-swarm מתחזק חיבורים ל-30-50 peers בלבד - חלק זעיר מה-swarm הכולל שיכול להכיל אלפים. ה-rarity counter שאני מחשב מבוסס *רק* על ה-BITFIELD שקיבלתי מהשכנים האלה. piece שנראה לי "נדיר" כי רק 2 מ-30 השכנים שלי מחזיקים אותו, עשוי בפועל להיות שכיח מאוד בחצי השני של ה-swarm שלא רואה אותי. ההחלטה שלי מבוססת על **מדגם מוטה** של ה-distribution האמיתי. במאמר של Legout (IMC 2006) זה מנותח: הטיה מקומית מקטינה את האפקט של rarest-first, אבל לא הורסת אותו - הסיבה היא שכשמספיק peers מבצעים אותה הוריסטיקה במקביל, השגיאות מתקזזות סטטיסטית.

#### 4. כיצד simultaneous rare-piece requests יוצרים contention?

אם האלגוריתם דטרמיניסטי לחלוטין - "תמיד תבחר את ה-piece עם המספר הנמוך ביותר ברשימת הנדירים" - אז כל ה-peers שרואים את אותו piece כנדיר *באותו רגע* יבחרו בו במקביל. כולם פונים בו-זמנית לאותו seeder יחיד שמחזיק אותו. זה תרחיש קלאסי של **thundering herd**: ה-seeder מוצף, ה-bandwidth שלו מתחלק לרסיסים שאין מהם תועלת, וזמן ההורדה הכולל של ה-swarm גדל. מבחינת optimization גלובלית, contention כזה הוא bottleneck אמיתי.

#### 5. מדוע randomization בתוך rarest-set הכרחי?

הפתרון ל-contention הוא **probabilistic selection**: אחרי שזיהיתי את ה-tie set של החתיכות הנדירות ביותר (כל החתיכות עם אותו מונה מינימלי), אני בוחר ביניהן ב-`random.choice`. שני peers שרצים את אותו האלגוריתם, רואים את אותו tie set, אבל בוחרים *חתיכות שונות*. הסימטריה נשברת בלי תיאום. בעיני, זאת אחת התובנות היפות של BitTorrent - אקראיות הופכת מ"רעש" ל"רכיב הכרחי בארכיטקטורה". בקוד אצלי: `piece_manager.py:select_piece_rarest_first` - אחרי בניית ה-tie set יש `random.choice(candidates)`.

**סיכום מושגים:** distributed availability (סעיף 1), swarm robustness (סעיף 2), probabilistic selection (סעיף 5), global vs local optimization (סעיף 1), rare piece starvation (סעיף 2).

---

### תרגיל 2 — ביקורת עמוקה על Tit-for-Tat

**בפרויקט מתואר:** Tit-for-Tat choke/unchoke
**קוד:** `python_engine/download_manager.py` — `_tit_for_tat_unchoke`

#### 1. מדוע Tit-for-Tat אינו באמת "הוגן"?

**Game theory** מנתחת את BitTorrent כ-iterated prisoner's dilemma ו-Tit-for-Tat הוא הסטרטגיה המנצחת בו - לכן הוא יציב. אבל "יציב" אינו "הוגן". האלגוריתם מודד **bytes**, לא **value**: piece נדיר שהפיץ אותו ל-swarm שווה בלאו-דווקא לאותו מספר bytes של piece שכיח שלא תורם לרובסטיות. **fairness instability** נובעת מכך שהמטריקה מבוססת תרומה אינטגרלית עיוורת ולא "ערך תרומה לאופטימיזציה הגלובלית". בנוסף, ההגדרה של "תורם" עצמה מוטה לטובת מי שיש לו upload bandwidth גבוה - לא בהכרח מי שמתנהג הכי טוב.

#### 2. כיצד asymmetric bandwidth פוגע במנגנון?

**Bandwidth asymmetry** היא ה-ground truth של הרשת הביתית. ADSL/Cable טיפוסי הוא 100/10 - 100 מגה הורדה אבל רק 10 מגה העלאה. peer עם upload חלש פיזית לא מסוגל להחזיר לי באותו קצב שבו אני מזין אותו, גם אם הוא נותן 100% ממה שיש לו. האלגוריתם מתייג אותו כ"קמצן" ויוריד את עדיפות ה-unchoke שלו, למרות שמבחינת מאמץ הוא משתף פעולה לחלוטין. ה-**incentive systems** מעוותים פה: התמרוץ לא משקף את הכוונה, רק את היכולת.

#### 3. מדוע optimistic unchoke הכרחי?

בלי **optimistic unchoke** המערכת לא יכולה להתאושש מ-bootstrap. peer חדש שמתחבר ל-swarm מתחיל עם 0 bytes שנשלחו אליי - הציון שלו נמוך ממה של כל peer ותיק, ולכן הוא לעולם לא ייכנס ל-top-4. הוא לא יקבל ממני data, ולא יוכל לתת לי data בחזרה (כי אין לו pieces), ולעולם לא ייצא מהמקום. הפתרון של ברם כהן: כל 30 שניות לבחור peer אקראי ולפתוח לו choke ללא תלות בציון. זה ה"דלת הכניסה" למערכת, וזה גם המנגנון שמאפשר ל-swarm לגלות peers שהציון שלהם *יעלה* בעתיד אבל עדיין לא עלה.

#### 4. כיצד BitTyrant מנצל את האלגוריתם?

**Peer exploitation** דרך BitTyrant (Piatek et al., NSDI 2007) הוא הדוגמה הקנונית. ההתקפה: במקום לתת לכל peer את ה-bandwidth המקסימלי שלי, BitTyrant מודד לכל peer את **המינימום הדרוש כדי להישאר unchoked** ושולח רק כמות זאת. כך החיסכון ב-upload מאפשר ל-BitTyrant להחזיק unchoked קשרים עם הרבה יותר peers בו-זמנית, ולמקסם downloads משלהם בלי לתת חזרה את ה"מנה הוגנת". ההוכחה האמפירית במאמר: לקוח BitTyrant מקבל 70% יותר download throughput מלקוח רגיל באותם תנאים. המנגנון לא יכול להגן על עצמו כי הוא נשען על הנחה שהיריב גם הוא Tit-for-Tat.

#### 5. מדוע contribution measurement בעייתי בעולם אמיתי?

מעבר ל-asymmetry: ה-measurement עצמו מבוסס על מה שראיתי **ב-window הצר שלי** - 20 שניות אצלי. peer שלא תרם בחלון הזה אבל תורם להפצה גלובלית של חתיכה נדירה ב-swarm כולו, נחשב חסר ערך מבחינתי. בנוסף, אני מודד את ה-bytes שהגיעו אליי - לא את ה-bytes שה-peer בכלל שלח. אם יש packet loss, אם יש latency גבוהה, אם המודד שלי מקבל את הbytes מאוחר מסיבות שאינן באשמת ה-peer - הוא מקבל ציון נמוך מהמגיע לו. **Fairness instability** כאן היא בעצם בעיה של "מי מודד את מי" במערכת מבוזרת בלי clock משותף ובלי observer ניטרלי.

**סיכום מושגים:** game theory (סעיף 1), incentive systems (סעיף 2), bandwidth asymmetry (סעיף 2), peer exploitation (סעיף 4), fairness instability (סעיפים 1, 5).

---

### תרגיל 3 — למה TCP מעל P2P יוצר complexity עצומה

**בפרויקט מתואר:** TCP Peer Connections
**קוד:** `python_engine/peer_connection.py` — `_message_loop`

#### 1. מדוע TCP stream אינו message protocol?

זאת אחת מההפתעות הכי גדולות שלי בפרויקט. **Stream-oriented communication** של TCP מבטיחה לי שני דברים בלבד: שמה ששלחתי יגיע בסדר ובלי אובדן. הוא *לא* מבטיח גבולות של הודעה. אם הצד השני שלח 4 הודעות בנות 50 בתים כל אחת, ה-recv שלי יכול להחזיר 200 בתים בקריאה אחת, או 73 בתים בקריאה ראשונה ו-127 בשנייה, או 1 בית בכל קריאה. TCP נראה כמו message protocol דרך socket API, אבל הוא נהר רציף של בתים. **Transport-layer semantics** של TCP הם stream, לא datagram, ואת הגבולות אני חייב להמציא בעצמי באמצעות framing.

#### 2. כיצד packet fragmentation משפיע על parsing?

ברמת ה-IP, MTU טיפוסי הוא 1500 בתים. הודעת PIECE עם block של 16K נשברת אוטומטית ל-11 IP packets. הם יכולים להגיע לא לפי הסדר, מאוחדים על-ידי TCP buffer, או מפורקים בכל גודל שה-OS מחליט. אם הקוד שלי "פשוט קורא וinterpret", הוא יכול לקרוא רק 1500 בתים מ-block של 16K ולנסות לפענח אותם - **buffering** הופך לחובה. הפתרון: לקרוא ראשית את 4 בתי האורך, לפענח את האורך, ואז לקרוא בדיוק את האורך הזה דרך `asyncio.readexactly` שעושה את האיסוף הפנימי בעצמו. ה-stream של TCP חוזר להיות message stream רק *אחרי* שעטפתי אותו ב-framing.

#### 3. מדוע partial reads מסוכנים?

תרחיש: ביקשתי block של 16K. הצד השני שלח אותו. ה-kernel הספיק להעביר 4K לאפליקציה שלי לפני שה-event loop נכנס ל-callback. אם הקוד שלי קורא `await reader.read(16384)` - הוא חוזר עם 4K במקום 16K. אם אני אז מנסה לפענח אותם כהודעה שלמה - אני מקבל ערבוב של חצי הודעה ועוד יותר גרוע, אני מאבד את 12K הבאים שיגיעו ב-kernel buffer הבא. הפתרון הוא `readexactly` שחוזר רק כשיש את כל ה-N בתים שביקשתי. **Asynchronous IO** כאן הוא חלק מהפתרון אבל גם חלק מהבעיה - הוא מאפשר לי לקרוא בלי לחסום, אבל בלי הקפדה על framing הוא לא פותר את partial reads.

#### 4. כיצד concurrent peer communication מסבך synchronization?

אצלי כל peer הוא coroutine נפרד ב-event loop. **Concurrency** במובן של asyncio: לא threads אמיתיים, אבל interleaving לא דטרמיניסטי בנקודות `await`. שני peers יכולים להשלים piece שונה באותה מילישנייה ולקרוא לאותו `PieceManager.submit_block`. שניים יכולים לעדכן את ה-frequency counter של אותו piece כש-BITFIELD מגיעים בו-זמנית. אצלי החלטה תכנונית: כל ה-state המשותף עובר דרך coroutines על אותו event loop, אז אין race ברמת ה-data races (asyncio הוא single-threaded). אבל יש race ברמת ה-logic - שני peers יכולים להחליט במקביל להוריד את אותו block, וצריך לטפל בזה ברמת היישום.

#### 5. מדוע slow peers יוצרים head-of-line blocking?

לפני שעברתי ל-`asyncio.create_task` לכל peer, peer איטי על ה-socket שלו היה תוקע את ה-loop כולו. תרחיש: 50 peers, אחד מהם על חיבור 56K. כשמגיע התור לקרוא ממנו, ה-event loop ממתין עד שיגיעו מספיק bytes - בזמן הזה ה-49 אחרים לא נקראים. **Head-of-line blocking** הוא ההגיון של TCP: בתוך socket יחיד, packet שלא הגיע חוסם את כל מה שאחריו. אצלי הפתרון הוא שכל peer הוא coroutine עם message loop משלו, ה-`await` שלו לא תוקע אחרים. אבל זה לא פותר HOL בתוך peer יחיד - בקצה ה-block שאני מבקש מפעם הזה ייקח דקה להגיע, וה-block הבא ממנו ימתין דקה לפני שיתחיל.

**סיכום מושגים:** stream-oriented communication (סעיף 1), asynchronous IO (סעיף 3), buffering (סעיף 2), concurrency (סעיף 4), transport-layer semantics (סעיף 1).

---

### תרגיל 4 — ביקורת עמוקה על piece hash verification

**בפרויקט מתואר:** SHA-1 piece verification
**קוד:** `python_engine/piece_manager.py` — `Piece.verify_hash`

#### 1. מדוע piece-level hashing אינו מגן מכל תקיפה?

**Integrity verification** אצלי היא ברמת piece, לא ברמת block. piece טיפוסי הוא 256KB = 16 blocks של 16KB. אני לא יודע אם piece תקין עד שכל 16 ה-blocks הגיעו. תוקף יכול לשלוח 15 blocks תקינים ו-block אחד פגום, וכל ה-piece נדחה - מה שדורש לבקש את 16 ה-blocks מחדש. זה מקרה ראשון: **performance-security tradeoffs** - בחירתי בגרנולריות של piece מקטינה את ה-overhead של אימות (256KB לכל hash במקום 16KB), אבל מאפשרת DoS בעלות נמוכה לתוקף. תקיפה שנייה: hash collision על SHA-1 מאפשרת תיאורטית להחליף content בלי שאני אבחין - גם אם זה pre-image attack שעדיין יקר, זה לא בלתי אפשרי לתוקף מדינה.

#### 2. כיצד collision attacks על SHA-1 רלוונטיים?

ב-2017 פורסם SHAttered - הדגמה ראשונה של **collision attack** מעשי על SHA-1. גוגל ו-CWI הראו שני קבצי PDF שונים עם אותו SHA-1. **Collision resistance** של SHA-1 נחשבת שבורה מאז. הרלוונטיות לפרויקט שלי: info_hash הוא SHA-1 של ה-info dictionary של ה-torrent. תאורטית, תוקף יכול לייצר torrent אחר עם אותו info_hash וה-handshake שלי יקבל אותו כתואם. ברמת ה-piece זה פחות רלוונטי - הצורך ב-collision על pieces ספציפיים בתוך torrent נתון, עם content מסוים שיש לי תועלת לזייף, מעשי הרבה פחות. אבל זה לא אפס. הפתרון הראוי - BEP-52 (BitTorrent v2) עם SHA-256 ו-Merkle Trees - מחוץ לסקופ של הפרויקט, ומתועד אצלי כפיתוח עתידי.

#### 3. מדוע malicious peers עדיין יכולים לפגוע?

גם עם **cryptographic validation** מושלמת, peer זדוני יכול לבצע **malicious payloads** ברמות אחרות: לשלוח blocks פגומים בכוונה כדי לבזבז לי זמן (DoS אפילו אם הוא נחסם אחרי 3 כשלים), לשלוח BITFIELD שקרי שמכריז על pieces שאין לו (יהפוך את ה-rarity counters שלי לשגויים), לקבל REQUEST ולא לענות (snubbing - דיברנו עליו בתרגיל 2), או לשלוח keep-alives כדי לשמור את ה-connection פתוח בלי לתרום. ה-SHA-1 verification מגן מקבלת content פגום, אבל לא מ-DoS על משאבים אחרים.

#### 4. כיצד corrupted blocks משפיעים על throughput?

תרחיש מעשי: ב-piece של 16 blocks, אם block אחד פגום, ה-piece כולו נדחה. כל ה-15 ה-blocks התקינים נזרקים וצריך לבקש מחדש. אם 1% מה-blocks פגומים בממוצע, ההסתברות ש-piece שלם של 16 blocks יעבור אימות היא 0.99^16 = 85%. כלומר 15% מה-pieces ידרשו ניסיון שני. ה-throughput האפקטיבי יורד ב-15%, וה-bandwidth שבזבזנו על ה-blocks הפגומים אבוד. במצב קיצוני, peer זדוני שמשלים 1 block פגום מתוך 16 בכוונה - על ה-fly - יכול להנמיך את ה-throughput שלי ב-50%-90% בלי שאזהה אותו כ-corrupt לפי המוניטין שלי (כי הוא לא מכשיל את ה-piece שלמה, רק את שחזורה).

#### 5. מדוע verification latency משפיע על ביצועים?

חישוב SHA-1 על 256KB לוקח כ-1-2 מילישניות על CPU מודרני. בודד זה זניח. אבל ב-piece rate של 100 pieces לשנייה (downloading מ-50 peers על קישור 1Gbps), זה 100-200ms של CPU רציף. אם אני מחשב SHA-1 על ה-event loop, זה חוסם את כל הקואורוטינות במהלך החישוב. **Performance-security tradeoffs** ברמה הזאת אצלי: העברתי את החישוב ל-`ThreadPoolExecutor` כדי שה-event loop ימשיך לזרום. הקוד ב-`download_manager.py:_on_peer_message` - אחרי `submit_block` שמחזיר True, ה-`verify_hash` רץ דרך `loop.run_in_executor`. זה מוסיף latency של context switch בודד אבל משחרר את ה-event loop להמשיך לטפל ב-IO.

**סיכום מושגים:** integrity verification (סעיף 1), collision resistance (סעיף 2), malicious payloads (סעיף 3), cryptographic validation (סעיף 3), performance-security tradeoffs (סעיפים 1, 5).

---

### תרגיל 5 — הבעיה האמיתית ב-peer reputation systems

**בפרויקט מתואר:** PeerReputation + SecurityManager
**קוד:** `python_engine/security.py`

#### 1. מדוע reputation אינו מדד אמין תמיד?

**Trust systems** במערכות מבוזרות סובלות מבעיה יסודית: למי אני סומך, ועל סמך מה? המוניטין שלי מבוסס על שני אותות פנימיים בלבד - כמה pieces העביר לי peer בהצלחה, וכמה הפר את הפרוטוקול מולי. אני לא יודע מה הוא עשה מול peers אחרים, מה ההיסטוריה שלו ב-swarm, או מה כוונותיו. **Probabilistic trust** היא לפיכך פשטנית: אחרי 3 כשלי hash הוא ב-ban, אחרת לא. אין סקאלה אנליטית, אין decay בזמן, ואין שילוב בין סוגי אותות שונים. זה מהיר וזול לחישוב אבל זה גם נאיבי. **Peer reliability** במציאות מורכבת יותר - peer יכול להיות אמין על pieces כלשהם ולא על אחרים, על שעות מסוימות ולא על אחרות, לפי load של המכונה שלו.

#### 2. כיצד Sybil attacks משפיעים?

זאת ההתקפה הכי משמעותית על מערכת מוניטין. ב-Sybil תוקף יוצר אלפי peer_id שונים מאותה מכונה. כל אחד מהם מתחיל reputation 0 - "neutral" אצלי. הוא יכול להתחיל לעבוד, להישחק, ולהיחסם אחרי 3 כשלים - אבל בינתיים 999 peer_id אחרים שלו עדיין פעילים. **Malicious identity rotation** הוא הכוח המניע: בעולם שבו זהות חופשית ליצירה (כל אחד יכול לג'נרט peer_id ב-`os.urandom(20)`), המוניטין הוא per-identity ולא per-attacker. **Distributed reputation** במובן של PageRank-לא-מרכזי עוזר חלקית, אבל גם הוא רגיש ל-Sybil. הפתרון האמיתי הוא **identity verification** דרך מקור מהימן (CA, social proof, proof-of-work), וזה סותר חלקית את הרוח המבוזרת של BitTorrent.

#### 3. מדוע peers חדשים נפגעים?

ה-cold start problem. peer חוקי לחלוטין שזה עתה נכנס ל-swarm מתחיל ב-reputation 0. מבחינתי, אין הבדל בינו לבין peer שעדיין לא הוכיח את עצמו לרעה. הוא נכנס לאותו pool של "peers להסתכל עליהם בחשד". במקרה שלי, זה לא מונע ממני להתחבר אליו (הוא לא מסומן ban עד שהוא מבצע 3 כשלים), אבל אם הייתי משתמש במוניטין כדי לתעדף *מי לחבר אליו ראשון*, peers חדשים היו במצב חיסרון מתמיד. הפתרון של BitTorrent הוא Optimistic Unchoke - שמנע את הבעיה בלי קשר למוניטין. אצלי, OU רץ ב-`_tit_for_tat_unchoke`.

#### 4. כיצד temporary network failures יוצרים false reputation?

**Peer reliability** מתערבב עם network reliability. תרחיש: peer חוקי לחלוטין, אבל בין שלנו יש router עם packet loss של 30%. 3 ה-pieces הראשונות שהוא שולח אליי מגיעות עם block אחד פגום בכל אחת - לא בגלל שהוא זדוני, אלא בגלל corruption ברשת. אצלי הוא חוטף ban אחרי 3 כשלים, ואני לעולם לא אדבר איתו שוב במהלך ה-session - גם אם הרשת התייצבה אחרי 5 דקות. **False reputation** במצב הזה הוא לא bug, הוא תוצאה ישירה של ה-threshold. הפתרון הראוי: מוניטין עם **decay** (forgiveness אחרי N דקות) או success_rate threshold (90% pieces תקינים, לא absolute count). שניהם לא מומשים אצלי, ומתועדים כמגבלות.

#### 5. מדוע distributed trust קשה מאוד למימוש?

הקושי היסודי: אמון דורש או (א) זהות אמיתית מאומתת, או (ב) היסטוריה שמשקפת התנהגות לאורך זמן, או (ג) רשת חברתית שמעבירה אמון בין צמתים. **Distributed reputation** מנסה לבנות את (ב) בלי מתאם מרכזי, אבל כל peer רואה רק slice קטן של ההיסטוריה, וה-aggregation דורש פרוטוקול נפרד (gossip, DHT עם reputation tokens) שלא קיים ב-BEP-3 הסטנדרטי. (א) דורש PKI - מי מנפיק תעודות? מי מבטל? וזה סותר את ה-decentralization. (ג) - web of trust - דורש social bootstrap שלא מתאים לשיתוף קבצים אנונימי. הוויתור של BitTorrent על אמון אמיתי הוא בחירה מודעת לטובת decentralization, ו-Tit-for-Tat הוא קירוב מעשי שיוצא מ"אני סומך עליך כל עוד אתה נותן לי".

**סיכום מושגים:** trust systems (סעיף 1), distributed reputation (סעיפים 2, 5), malicious identity rotation (סעיף 2), peer reliability (סעיפים 1, 4), probabilistic trust (סעיף 1).

---

### תרגיל 6 — ביקורת עמוקה על asyncio + REST Bridge

**בפרויקט מתואר:** Flask + asyncio + Java REST API
**קוד:** `python_engine/api_server.py` — `_run_async`, `start_event_loop`

#### 1. מדוע asyncio event loop מסובך ב-multi-peer networking?

**Async event loops** נראים כמו פתרון מושלם להרבה חיבורי TCP במקביל - וזה נכון, אבל יש בהם seam אחד שצריך לזכור. ב-asyncio של Python יש event loop יחיד שמטפל בכל הקואורוטינות. כל coroutine מתקדמת רק עד ה-`await` הבא ואז מחזירה שליטה ל-loop, שבוחר את הבאה שמוכנה לרוץ. במציאות של multi-peer זה אומר שיש 50 message loops על אותו event loop, ולכל אחד יש callback מורכב עם submission ל-PieceManager, hash verification, וכתיבה לדיסק. הקושי: כל פעולה שאינה async תוקעת את כל ה-50. בנוסף, debugging הופך לקשה - stack traces ב-asyncio הם פחות אינטואיטיביים, וקצב ה-context switch לא תלוי בזמן אלא בנקודות `await`. בתחילת הפרויקט נתקלתי כמה פעמים בקריאות סינכרוניות שהפילו את הביצועים מבלי לזרוק שגיאה.

#### 2. כיצד blocking operations שוברים concurrency?

הדוגמה הקלאסית: `time.sleep(2)` במקום `await asyncio.sleep(2)`. הראשון תוקע thread - וב-asyncio זה ה-thread היחיד - ל-2 שניות מלאות, וכל הקואורוטינות מקפיאות. דוגמה פחות ברורה: `hashlib.sha1(data).digest()` על piece של 256KB - לוקח 1-2 מילישניות. בודד זה זניח, אבל ב-100 פעמים בשנייה זה 100-200ms של CPU רציף, וזה מצטבר. עוד דוגמה: `file.write(data)` בלי async - I/O סינכרוני חוסם את ה-thread עד שה-OS מאשר. אצלי, כל אלה - hash, disk write - עוברים דרך `loop.run_in_executor(self._executor, ...)`. ה-`ThreadPoolExecutor` עם 2 workers מטפל בעבודה החוסמת ב-thread נפרד, וה-event loop ממשיך. **Concurrent networking** עובד רק כשכל פעולה חוסמת זוהתה והועברה.

#### 3. מדוע REST polling יוצר overhead?

ה-GUI שלי polls את `/torrents` כל 500ms. בכל poll: HTTP request, סריאליזציית JSON של כל ה-statuses, parsing ב-Java, ועדכון JTable. אצל הורדה בודדת זה זניח. במצב של 10 הורדות פעילות, **polling overhead** מצטבר: 720 בקשות בדקה, כל אחת מבקרת בכל ה-state של ה-engine. ה-CPU של ה-engine מבזבז זמן על serialization במקום על פרוטוקול, ויש latency של עד 500ms בין שינוי ב-engine להופעתו ב-GUI. הפתרון הראוי הוא WebSockets/SSE - **inter-process communication** מבוסס push במקום pull. במימוש שלי בחרתי polling כי הוא פשוט יותר ב-Java Swing ולא דורש ספריית WebSocket נוספת. ההחלטה מתועדת בספר כמגבלה מודעת.

#### 4. כיצד synchronization בין Java ל-Python מסובך?

**Inter-process communication** היא הזירה: שני תהליכים נפרדים, שני data models, ושני concurrency models. מצד ה-Python יש asyncio coroutines. מצד ה-Java יש EDT (Event Dispatch Thread) + ScheduledExecutorService. הגשר הוא JSON over HTTP, וכל פעולה דורשת serialization ל-JSON ו-deserialization בצד השני. בעיה מעשית: schema mismatches. שדה שהוספתי בצד ה-Python (`download_path`) דרש update בצד ה-Java ב-`TorrentStatus.fromJson`. אם הוא חסר ב-JSON ה-Java פיצח. אצלי הפתרון הוא להחזיר ערכי ברירת מחדל ב-Java אם השדה חסר, וגרסה של ה-API לא לשנות שדה קיים בלי קשר. אבל זה גשר שביר באופן יסודי - אין חוזה (אין OpenAPI schema), והשגיאות נתפסות רק בריצה.

#### 5. מדוע race conditions עדיין אפשריים?

ה-asyncio הוא single-threaded, אבל ה-Flask הוא threaded. כשבקשת REST מגיעה, Flask מקצה לה thread מתוך pool. ה-thread הזה קורא ל-`_run_async(coro)` שמשתמש ב-`asyncio.run_coroutine_threadsafe(coro, loop).result()`. בזמן שה-coro רץ ב-event loop, ה-Flask thread מחכה. כל זה עובד מצוין כל עוד הקורא לא נוגע ב-state של ה-engine ישירות. אבל יש מקרים שבהם Flask קורא ל-`download.get_status()` שמחזיר dictionary שמתעדכן ע"י ה-event loop באותה רגע (למשל `stats.bytes_downloaded` שהמלאכת מסונכרנת ע"י peer message). אלה **synchronization hazards** קלאסיים: read-during-write. ב-CPython, ה-GIL מגן ברמת dict access (אטומי), אבל לא ברמת logic (פקח, סנאפ של מצב לכמה שדות). אצלי, אני מסתפק בכך שה-data structures העיקריים (dict, list) הם CPython-atomic ברמת המבנה, ולא מנעל אותם במפורש - אבל זה החלטה תכנונית שאני יכול להגן עליה רק בידיעה שזאת הסתמכות על implementation detail של CPython.

**סיכום מושגים:** async event loops (סעיף 1), concurrent networking (סעיף 2), inter-process communication (סעיפים 3, 4), polling overhead (סעיף 3), synchronization hazards (סעיף 5).

---

### תרגיל 7 — למה BitTorrent הוא למעשה בעיית Distributed Systems

**בפרויקט מתואר:** P2P swarm architecture

#### 1. מדוע swarm אינו מערכת יציבה?

**Swarm dynamics** הם המהות. ה-swarm אינו אוסף קבוע של peers - הוא נחשב כקבוצה דינמית שמשתנה כל הזמן. peers נכנסים (מתחילים הורדה חדשה), יוצאים (סיימו, או החליטו לעצור), נחסמים, מתחברים מחדש, משנים IP. אין רגע יחיד שבו מצב ה-swarm "סופי". **Decentralized systems** מהסוג הזה לא יכולים להגיע ל-equilibrium במובן הקלאסי כי הקלט המוקלד משתנה לפני שה-equilibrium מחושב. מבחינתי כ-peer יחיד, אני רואה רק תמונת snapshot - וה-snapshot הזה כבר לא מדויק ברגע שהשתמשתי בו. זה השיעור הכי קשה ב-distributed systems: היציבות היא לא חוסר שינוי, היא **distributed coordination** שמתאזן בנקודה שבה השינוי מתפזר.

#### 2. כיצד churn משפיע על availability?

**Peer churn** - שיעור היציאה והכניסה של peers ביחידת זמן - הוא המנוע של חוסר היציבות. מאמר Legout מודד churn טיפוסי של 10-30% תוך 5 דקות בכמה swarms פתוחים. ההשפעה: piece שהיה זמין אצל 50 peers לפני 10 דקות, אולי זמין אצל 20 עכשיו. **Distributed coordination** ברמת ה-swarm דורשת שכל הפעולות יתחשבו ב-churn: announce תקופתי ל-tracker (אצלי כל ~30 דקות לפי interval שהוא מחזיר), reconnect אוטומטי ל-peers שנפלו, ועדכון rarity counters בכל BITFIELD/HAVE חדש. אם הייתי מחשב rarity פעם אחת ומסתמך עליה, אחרי 5 דקות זה היה רעש מוחלט.

#### 3. מדוע decentralized coordination קשה?

הקושי האמיתי: אין מי שיודע "את התשובה הנכונה". כל peer מקבל החלטות מקומיות מבוססות מידע חלקי. הסכימה של החלטות מקומיות יוצרת התנהגות גלובלית - emergent - שאף אחד לא תכנן ישירות. **Decentralized systems** דורשים שכל peer יבצע אלגוריתם זהה, וההצלחה תלויה ב"compatibility" של הפעולות. אם 90% מהlecthers מבצעים rarest-first נכון ו-10% מבצעים random, ה-swarm עדיין מתפקד אבל פחות יעיל. אם 50% מבצעים strategy עוין, ה-swarm קורס. **Distributed coordination** מבוססת על trust בכך שהמרבית תשחק לפי הכללים, ושסטיות קטנות יתקזזו בממוצע.

#### 4. כיצד partial knowledge משפיע על decision-making?

אני רואה רק את ה-BITFIELD של 30 ה-peers שלי, לא של אלפים ב-swarm. ה-rarity שאני מחשב היא **לוקאלית** במובן חמור: piece שנראה לי נדיר אצל 2 מ-30 שכנים, יכול להיות זמין אצל 800 מתוך 1000 ב-swarm כולו. ההחלטה שלי מבוססת על מדגם מוטה. הדומה ל-CAP theorem: כדי לקבל החלטה "נכונה" הייתי צריך מבט גלובלי, אבל הוא לא קיים ולא יכול להתקיים בלי מתאם מרכזי. הקירוב המעשי: ככל שיש לי יותר שכנים, ה-sample size עולה והשונות יורדת. זה הסבר טוב למה limits כמו `MAX_CONNECTIONS = 50` הם tradeoff - יותר connections = יותר טוב לרובסטיות, יותר overhead לתחזוקת ה-state.

#### 5. מדוע eventual consistency מופיעה ב-BitTorrent?

הקובץ עצמו הוא **eventual consistency** קלאסית: בסוף, כל ה-peers שהשלימו את ההורדה מחזיקים את אותו תוכן בדיוק. אבל בכל רגע ביניים, יש state inconsistency - peer A יש לו pieces 1, 3, 5; peer B יש לו 2, 4, 6; peer C עדיין באמצע piece 7. אין נקודה אחת שבה כולם תואמים. ההסכמה היא רק על ה-target state (הקובץ המאומת ע"י info_hash), לא על מסלול ההגעה. **Distributed coordination** במובן ה-BitTorrent היא הצפת ה-state graduated במגוון מצבים partial עד שכל ה-peers מגיעים לאותו end state. ה-info_hash + SHA-1 per piece הם ה"ground truth" שמאפשרים eventual consistency להיות מאומתת.

**סיכום מושגים:** distributed coordination (סעיפים 2, 3, 5), peer churn (סעיף 2), decentralized systems (סעיפים 1, 3), eventual consistency (סעיף 5), swarm dynamics (סעיף 1).

---

### תרגיל 8 — ביקורת עמוקה על Bencode

**בפרויקט מתואר:** Bencode parser/encoder
**קוד:** `python_engine/bencode.py`

#### 1. מדוע recursive parsing מסוכן?

**Recursive parsing** הוא הטכניקה הטבעית ל-Bencode כי הוא רקורסיבי לפי הגדרה: dict יכול להכיל list שמכיל dict ש-... אצלי המימוש משתמש ב-Python recursion ישירות. הסכנה: Python מגדיר recursion limit של 1000 כברירת מחדל, ו-stack frame ב-Python הוא יקר יחסית. torrent מפוצץ עם nesting של 1001 שכבות (`lllll...` הרבה פעמים) יפיל את ה-parser עם `RecursionError`. **Memory exhaustion** ברמת ה-stack היא קיצור-דרך ל-DoS בלי לשלוח כמות data גדולה. הפתרון הראוי: iterative parser עם explicit stack, או recursion limit מפורש בקוד. אצלי אין הגנה מפורשת - אני מסתמך על Python's default. זאת מגבלה אמיתית של ה-parser, ואני מודה בה.

#### 2. כיצד malformed torrents עלולים לקרוס parser?

**Malformed metadata** היא הקלט הראשון מהרשת או מהמשתמש, ולכן ה-attack surface הראשון. דוגמאות מ-`bencode.py` שלי: `i00e` (integer עם leading zero) נדחה במפורש. `i-0e` (negative zero) נדחה. dict עם מפתחות לא ממוינים נדחה. string עם length שאינו תואם ל-data בפועל - הקריאה לא מצליחה. ל-parser שלי יש בדיקות לכל הצורות הקנוניות האלה. **Protocol robustness** דורשת שכל הסטיה מה-canonical form תזרק exception ספציפי במקום להחזיר data שגוי - כי data שגוי שמגיע לחישוב ה-info_hash מקלקל את ה-identity של ה-torrent, וזה כשל שקט. הקפדה על canonical form בכל decoder היא לא קוסמטיקה - היא דרישה ל-correctness.

#### 3. מדוע deeply nested structures בעייתיים?

מעבר ל-stack overflow מסעיף 1, יש בעיית **memory exhaustion** אחרת: nested structure גם תופס זיכרון בצורה לא לינארית. dict שמכיל 1000 lists שכל אחד מכיל 1000 dicts - זה מיליון objects ב-Python, וכל אחד מהם הוא ~64 בתים של overhead לפני ה-data בכלל. torrent של 100KB יכול להתפענח ל-100MB של Python objects אם הוא בנוי בקפידה. אצלי אין memory limit על תוצאת parsing - הגנה ראויה הייתה לעקוב אחרי גודל ה-result במהלך ה-parsing ולעצור מעבר ל-threshold (נגיד 10MB).

#### 4. כיצד integer overflows אפשריים?

Python מצד אחד מוגן מ-integer overflow ברמת השפה - int הוא arbitrary precision. אבל זה לא אומר שאין בעיה. במצב שבו ה-parser מקבל `i999999999999999999999999999999999999e`, הוא ייצור int תקין אבל ענק. אם אני אחר כך משתמש בערך הזה כ-offset, כ-size, או כ-array index - אני יכול לקבל MemoryError, IndexError, או חישובים שקטים שגויים. במקומות הביקורתיים אצלי (`get_piece_length`, `get_file_offset`) אני מוודא שהערכים בטווח סביר, אבל לא בכל מקום. **Parser security** במובן הזה היא רב-שכבתית: ה-parser נכון, אבל הצרכן של תוצאת ה-parsing צריך לוולד את הערכים בסקופ של השימוש שלו.

#### 5. מדוע parser validation הוא attack surface?

ה-parser הוא הקוד הראשון שרץ על קלט מהרשת. **Parser security** היא קריטית כי תוקף יכול לבחור את ה-input. כל באג ב-parser - integer overflow, buffer underrun, type confusion, recursive depth - הוא נקודת תקיפה ישירה. במחקר על parsers של BitTorrent היו דוגמאות של clients שאפשר היה לקרוס פשוט בקובץ .torrent מעוצב מטעמיהם. אצלי השמירה היא בכך שה-parser כתוב ב-Python (memory-safe, אין buffer overflows קלאסיים), עם בדיקות canonical form מפורשות. אבל גם ב-Python, **protocol robustness** דורשת לתפוס כל exception ב-decoder ולהחזיר שגיאה למשתמש במקום לקרוס - ואצלי, ה-API endpoint שמקבל torrent עוטף את ה-decode ב-try/except ומחזיר 400 על כל שגיאה. זה גם הגנה וגם UX - המשתמש יודע שהקובץ שלו שבור.

**סיכום מושגים:** recursive parsing (סעיף 1), parser security (סעיף 4, 5), malformed metadata (סעיף 2), memory exhaustion (סעיפים 1, 3), protocol robustness (סעיפים 2, 5).

---

### תרגיל 9 — הבעיה האמיתית ב-DownloadManager

**בפרויקט מתואר:** DownloadManager orchestration
**קוד:** `python_engine/download_manager.py` — `_download_loop`, `_request_pieces`

#### 1. מדוע scheduling requests קשה?

**Distributed scheduling** במציאות של 50 peers ו-1600 pieces (לקובץ 400MB): מי מבקש מה ממי. הבחירות הן מבוזרות (כל peer בוחר עצמאית) אבל הקואורדינציה מקומית. השאלה היא לא רק "מה לבקש", אלא "מה לבקש *ממי*, כמה לבקש במקביל מאותו peer, ומה לעשות כש-pending requests מצטברים". אצלי ה-DownloadManager מקצה לכל peer **piece אחד** בכל רגע נתון (ב-`_peer_piece` dict), ובתוך ה-piece אני שולח עד `MAX_PENDING_REQUESTS = 50` blocks. זה החלטה תכנונית: בלי הקצאה כזאת, blocks מתפזרים על pieces רבות וה-piece completion rate יורד דרמטית. עם הקצאה יציבה, מקדמים piece לסיום מהר יותר ופחות "פתוחים".

#### 2. כיצד concurrent requests יוצרים race conditions?

**Concurrency hazards** במצב הזה: שני peers משלימים את אותו piece באותו רגע. אצלי, `submit_block` בודק אם ה-piece כבר completed לפני submit - duplicate block נדחה בשקט. הסיבה: `_on_peer_message` של PIECE לפעמים מקבל הודעה ל-piece שכבר התקבל מ-peer אחר ועבר אימות. עוד race: שני peers שולחים BITFIELD בו-זמנית, ה-frequency counter מתעדכן פעמיים. ה-CPython GIL הופך את הפעולות הבסיסיות לאטומיות, אבל הלוגיקה דורשת שיקול - למשל, פעולת "מצא piece פנוי + סמן piece זה כ-in-progress" חייבת להיות אטומית ברמת הלוגיקה, וזה דורש או lock או עיצוב שמתמודד עם duplicate work.

#### 3. מדוע peer failures משפיעים על entire flow?

peer שמתנתק באמצע piece משאיר blocks "תלויים" במצב requested-but-not-received. **Request orchestration** דורשת ניקוי: מצד אחד, הblocks האלה צריכים להיות שוב requestable ע"י peers אחרים; מצד שני, אם אני שולח request לאותו block ל-peer אחר במהירות, ייתכן שה-peer הראשון בכל זאת ישלח אותו (race נוסף). אצלי, על peer disconnect: `clear_peer_requests` עובר על כל ה-pieces in-progress ומנקה את ה-block requests שהיו ב-peer הזה. בלי זה היה download stalling - blocks תקועים ב-"requested" וה-piece לא מתקדם. **Distributed scheduling** דורש cleanup explicitly של state שנשאר אחרי peer failure.

#### 4. כיצד request queues עלולות להתפוצץ?

ב-`MAX_PENDING_REQUESTS = 50` per peer ו-50 peers, יש לי תאורטית 2500 outstanding requests. כל request מחזיק entry ב-`_pending_requests` של PeerConnection ובמערכת tracking של PieceManager. **Queue dynamics**: אם הקצב של תגובות יורד (peers איטיים, network congestion), ה-queue ימשיך לגדול עד שאני אגיע ל-timeout ועדיפויות. בלי ניהול נכון יש שני סיכונים: זיכרון גדל, ו-blocks תקועים ב-"requested" וחוסמים peers אחרים מלעבוד עליהם. אצלי יש שני מנגנונים: `_pending_requests` counter עם timeout (15 שניות) שמאפס אם אין response, ו-block-level `requested_time` עם timeout נפרד (10 שניות) שמאפשר re-request מ-peer אחר. שני מנגנונים שמתאזנים בין aggressive (להמשיך לזרום) ל-conservative (לא לבזבז bandwidth על duplicate work).

#### 5. מדוע timeout tuning הוא tradeoff קשה?

**Timeout management**: timeout קצר מדי = הרבה ניתוקים מיותרים, peers נחשבים מתים כי הם רק איטיים, וה-reconnect overhead מצטבר. timeout ארוך מדי = slot תקוע על peer גוסס וה-download לא מתקדם. אצלי: `BLOCK_REQUEST_TIMEOUT = 10s` (block יכול להישאל מ-peer אחר אחרי 10 שניות), `PIECE_REQUEST_TIMEOUT = 30s` (piece in-progress מאופס אחרי 30s), `pending_requests` reset אחרי 15s, snubbing threshold 60s, peer cleanup interval 15s. בחירת המספרים האלה לא הייתה אנליטית - היא הייתה אמפירית. הרצתי הורדות, ראיתי איפה stalling, וכוונתי. ב-tracker שמחזיר interval של 30 שניות זה יחס סביר. במציאות של רשת אחרת, ייתכן שצריך לכוון מחדש - **timeout management** הוא משתנה תלוי-context.

**סיכום מושגים:** distributed scheduling (סעיפים 1, 3), request orchestration (סעיף 3), timeout management (סעיף 5), queue dynamics (סעיף 4), concurrency hazards (סעיף 2).

---

### תרגיל 10 — הבעיה האמיתית של הפרויקט

**המערכת מתיימרת:** "לממש לקוח BitTorrent מלא"

#### למה זה לא רק "להוריד קבצים"

המראית-עין של פרויקט BitTorrent היא פשוטה: יש קובץ ברשת, אני רוצה אותו אצלי, התוצאה היא bytes על דיסק. אבל זה ה-**outcome**, לא ה-**problem**. אם רק היה צריך להוריד קובץ, הייתי משתמש ב-HTTP GET ולא היה לי פרויקט.

ה-problem האמיתי הוא יחד של חמש בעיות שונות שכל אחת מהן היא תחום מחקר בפני עצמו:

##### Distributed optimization

rarest-first הוא heuristic לוקאלי לבעיית כיסוי מבוזרת: שלכל piece תישאר זמינות גם כשה-seeders עוזבים. כל peer פותר חלק קטן של בעיה גלובלית בלי לדעת זאת. הסכימה היא הקירוב.

##### Asynchronous coordination

Tit-for-Tat הוא משחק חוזר ב-N שחקנים ללא תקשורת ישירה ביניהם. ההחלטה של מי לפתוח לו choke מבוססת על אות עקיף: מה ה-peer נתן לי לאחרונה. אין message שאומר "תפתח לי", רק התנהגות שיוצרת תמריץ.

##### Probabilistic peer behavior

Optimistic unchoke + randomization בתוך ה-tie set של rarest-first הם הכרחיים. בלי אקראיות, המערכת מתכנסת ל-degenerate states. עם אקראיות, הפעולה הופכת לסטוכסטית באופן בסיסי - ההתנהגות "בממוצע" טובה, אבל לא דטרמיניסטית.

##### Transport uncertainty

TCP נותן לי אמינות (delivery ordered, no loss), אבל לא נותן לי גבולות הודעה, ולא נותן לי ערובות לזמן. את שני אלה אני בונה בעצמי: framing דרך length-prefix, ו-timeouts מפורשים. TCP הוא רק הקרקע, לא הפתרון.

##### Adversarial networking

אני מניח שכל peer שאני מדבר איתו עשוי להיות עוין: לשקר על pieces שיש לו (BITFIELD שגוי), לשלוח data פגום, לא לענות אחרי unchoke, להתחזות לזהויות שונות (Sybil). כל קוד שלי שמדבר עם הרשת חייב להניח adversarial input - חישוב hash על כל data, ולידציה על כל הודעה, threshold-based banning.

#### האשליה של "deterministic distributed control"

ה-7 הטכנולוגיות שמופיעות בפרויקט - rarest-first, Tit-for-Tat, peer reputation, SHA-1 validation, asyncio, TCP peer protocol, REST orchestration - יוצרות **illusion of deterministic distributed control**. מבחוץ זה נראה כאילו יש מערכת שמפעילה את ההורדה: הקובץ יורד, הסטטוס יציב, הסיום צפוי.

האמת המוסתרת:

- **rarest-first** היא probabilistic - random.choice בתוך ה-tie set. ההחלטה ב-run הבא שונה.
- **Tit-for-Tat** הוא משחק חוזר עם תוצאה אמרג'נטית, לא algorithm מתכנסת.
- **peer reputation** הוא per-identity, ולכן Sybil-vulnerable. ה-"trust" הוא אשליה של trust.
- **SHA-1 validation** היא אחרי-מעשה. בזמן ההורדה אני לא יודע אם data תקין עד שכל ה-piece הגיע, ו-SHA-1 עצמו כבר עם collision attack מוכר.
- **asyncio** היא single-threaded cooperative. נראית concurrent אבל בעצם interleaved, וכל blocking operation שוברת אותה.
- **TCP peer protocol** נראה message-based, אבל הוא stream על stream. framing הוא אשליה שאני בונה.
- **REST orchestration** היא polling-based - ה-GUI לא יודע מה ה-engine עושה ברגע זה, רק מה הוא ענה לפני 500ms.

הלקוח שלי עובד לא בגלל שיש שליטה דטרמיניסטית, אלא בגלל ש-N החלטות מקומיות פרובביליסטיות מתאזנות סטטיסטית לאורך זמן. כשמדובר ב"מהנדס תוכנה" - זה השיעור החשוב ביותר של הפרויקט: ההבדל בין שליטה לבין הופעת שליטה.

---

## חלק ב — 7 תרגילי קוד

---

### תרגיל קוד 1 — `select_piece_rarest_first`

**קוד:** `python_engine/piece_manager.py` — `PieceManager.select_piece_rarest_first`

**ניתוח הקוד:**

- **Rarity counting:** `_peer_frequency: Dict[int, int]` - מילון מ-piece index ל-counter של כמה peers מחזיקים אותו. מתעדכן ב-`add_peer_pieces` (כשמגיע BITFIELD) וב-`mark_peer_has_piece` (כשמגיע HAVE). מבנה O(1) לעדכון, O(N) לסריקה.
- **Peer availability maps:** `_peer_pieces: Dict[str, Set[int]]` - לכל peer (לפי peer_key מסטרינג) set של אינדקסים שיש לו. דרושים כדי לדעת אילו pieces אני יכול לבקש ממנו ספציפית. Set מאפשר membership check ב-O(1) ו-cleanup ב-`remove_peer`.
- **Random rarest selection:** השלבים בפונקציה - (1) לסנן רק pieces שב-MISSING שיש להם peer זמין שמחזיק אותם, (2) למצוא את ה-counter המינימלי, (3) לבנות tie set של כל ה-pieces עם counter זה, (4) `random.choice(candidates)`. ה-randomization בתוך tie set היא קריטית - בלי זה contention.
- **Missing-piece tracking:** `Piece.status: PieceStatus` עם הסטטוסים MISSING, IN_PROGRESS, COMPLETED. הסנן בוחר רק MISSING - pieces שטרם החלו להיות מורדים. pieces IN_PROGRESS עוברים דרך nemesis אחר - `find_in_progress_piece` שמטפל ב-endgame mode.

**שאלת עומק: כיצד stale peer-state information יגרום piece starvation?**

תרחיש: peer A מתנתק. אם לא הוסר במפורש מ-`_peer_pieces`, ה-set שלו נשאר. ה-rarity counter בשבילו עדיין סופר אותו. piece שהיה אצל A בלבד נשאר עם counter ≥ 1 גם אחרי שהוא הלך. כשאני מחפש pieces נדירים, ה-piece הזה לא ייראה מספיק נדיר (כי הוא לא 0, הוא 1), אבל בפועל אי-אפשר להוריד אותו - אף peer פעיל לא מחזיק אותו. **Piece starvation**: ה-piece לעולם לא נבחר לבקשה, ההורדה לא מתקדמת.

הפתרון בקוד: `PieceManager.remove_peer(peer_key)` מנקה הן את ה-set של ה-peer מ-`_peer_pieces` והן מפחית את ה-counter של כל piece שהיה לו ב-`_peer_frequency`. נקרא מ-`DownloadManager._cleanup_dead_peers`. בלי זה ה-frequency counters נהיים שקריים, וה-rarest-first מתבסס על נתונים מתים. זה היה אחד מ-6 הבאגים שתפסתי בזמן debug של ה-stalling (מתועד ב-`DOWNLOAD_STALLING_DEBUG_GUIDE.md`).

---

### תרגיל קוד 2 — `_tit_for_tat_unchoke`

**קוד:** `python_engine/download_manager.py` — `Download._tit_for_tat_unchoke`

**ניתוח הקוד:**

- **Upload contribution scoring:** הציון מבוסס על `conn.bytes_received_in_window(20.0)` של PeerConnection - חלון נע של 20 שניות. בגרסה הראשונה שלי השתמשתי ב-`bytes_downloaded` מצטבר, אבל זה גרם ל-peers שתרמו פעם להישאר בראש הדירוג לנצח. ה-window מיישם **sliding window contribution** שמשקף התנהגות אחרונה.
- **Peer sorting:** `sorted(candidates, key=lambda c: c.bytes_received_in_window(20.0), reverse=True)`. peers שהם snubbed מוזזים לסוף הרשימה דרך partition מקדים (`is_snubbed` בודק 60 שניות בלי block). הסדר הסופי: non-snubbed מ-best ל-worst, ואז snubbed.
- **Optimistic unchoke:** אחרי שבחרתי את ה-top 3 (לא 4) על-פי תרומה, אני בוחר peer רביעי באקראי מבין הנותרים שלא נבחרו. זה ה-Optimistic Unchoke - דלת הכניסה ל-peers חדשים. בלי זה, peer חדש (ציון 0) לעולם לא ייכנס.
- **Interval scheduling:** רץ כל `CHOKE_INTERVAL = 10` שניות מ-`_choke_loop`. למה 10s? כי החלון הוא 20s, ושני מחזורים בתוך החלון מספיקים כדי שהמטריקה תהיה יציבה. 5s היה רועש מדי, 30s היה מגיב לאט.

**שאלת עומק: כיצד bandwidth asymmetry תפגע בהוגנות האלגוריתם?**

ADSL ביתי טיפוסי: 100Mbps הורדה, 10Mbps העלאה - יחס של 10:1. peer עם הקצאה כזאת *לעולם* לא יכול להעלות אליי באותו קצב שאני שולח אליו, גם אם הוא מקצה לי 100% מה-upload שלו. ב-`_tit_for_tat_unchoke` אני מודד `bytes_received_in_window` - כמה ה-peer שלח אליי. ה-peer הזה ייראה "תורם פחות" מ-peer עם 1Gbps symmetric שמעלה לי 30% מה-bandwidth שלו - גם אם השני נותן רק שליש מהמאמץ שלו.

המנגנון הזה מעניש intent טוב כשיש לו תקרה פיזית נמוכה. **Bandwidth asymmetry** נמצאת בתשתית הביתית של רוב המשתמשים, ולכן ה-bias נכון לרוב ה-swarm. שני מנגנונים מקטינים את ההשפעה: (1) Optimistic Unchoke - peers עם תרומה נמוכה עדיין מקבלים unchoke באקראי, (2) sliding window - חלון של 20 שניות מאזן באופן מקומי בלי קיצוץ קשה. אבל ה-bias לא מתבטל - peer ביתי תמיד ייראה גרוע יותר מ-data center peer באותה השוואה. הפתרון התאורטי הוא לדרג לפי **proportion** של ה-upload bandwidth של ה-peer (איך אני יודע מה ה-bandwidth שלו?), וזה דורש פרוטוקול הצהרה שלא קיים ב-BEP-3.

---

### תרגיל קוד 3 — `PeerConnection.read_message`

**קוד:** `python_engine/peer_connection.py` — `PeerConnection._message_loop`, `_read_message`

**ניתוח הקוד:**

- **TCP stream parsing:** ה-loop קורא 4 בתי אורך דרך `await self._reader.readexactly(4)`. `readexactly` חיוני - הוא חוסם עד שיש את כל 4 הבתים, ומטפל ב-partial reads באופן שקוף. בלי זה אני יכול לקבל 2 בתי אורך ולפענח אותם שגוי.
- **Length-prefixed framing:** אחרי קריאת האורך, `length, = struct.unpack('>I', length_bytes)` - 4-byte big-endian. אם length == 0 זה keep-alive. אם length > MAX_MESSAGE_SIZE (2MB) אני זורק exception ומנתק. ולידציה זאת מונעת תקיפת DoS שבה peer מכריז על אורך 4GB.
- **Partial reads:** אחרי האורך, `await self._reader.readexactly(length)` קורא בדיוק את ההודעה. גם פה - readexactly מטפל ב-partial reads. הקריאה מובטחת להחזיר את כל ה-bytes או לזרוק exception (`IncompleteReadError`).
- **Protocol validation:** מזהה ההודעה הוא הבית הראשון. `MessageType(message_id)` ימחיש exception אם זה לא ערך חוקי (0-8). ה-payload מוחלץ לפי ה-type ומועבר ל-`_handle_message` שמעדכן state ייעודי (peer_choking, peer_pieces וכו') ואז קורא ל-on_message callback.

**שאלת עומק: כיצד malformed peer messages יפילו את state machine?**

תרחיש 1: peer שולח UNCHOKE לפני BITFIELD. אצלי אין שגיאה - אני מסמן `peer_choking = False`, אבל `peer_pieces` עדיין ריק כי לא הגיע BITFIELD. כש-`_request_pieces` מחפש מה לבקש, הוא לא ימצא piece שה-peer מחזיק (כי אני חושב שהוא לא מחזיק כלום) ולא יבקש כלום. כשלון שקט, לא קריסה. אבל מבחינת state machine, אני במצב לא עקבי - הוא לא choking אבל אני לא יכול לבקש ממנו.

תרחיש 2: HAVE עם piece_index ≥ num_pieces. אם לא מוולדים, `peer_pieces[index] = True` ייצר IndexError כי ה-list באורך num_pieces. אצלי, `_handle_message` בודק `if 0 <= index < self.num_pieces` לפני העדכון. הפרה נכנסת ל-SecurityManager שמגדיל את מונה הפרות הפרוטוקול, ואחרי 5 - ban.

תרחיש 3: PIECE עם piece_index לא תקין או block offset שלילי. הולידציה ב-PieceManager.submit_block - אם offset + length > piece_length, ההצבעה נדחית. אם piece_index לא קיים, ה-piece לא נמצא ב-list וההצבעה נדחית. בכל מקרה - לוג, ולפעמים report ל-security.

תרחיש 4: PIECE עם content שלא תואם hash. ה-piece מאופס למצב MISSING, וה-SecurityManager מקבל hash_failure report על ה-peer. אחרי 3 - ban.

הכלל הכללי: **כל הודעה נכנסת חייבת ולידציה לפני שהיא משנה state**. הולידציה היא הקו הראשון של הגנה על ה-state machine. בלי זה, peer זדוני אחד יכול להפיל את כל ההורדה דרך IndexError בודד.

---

### תרגיל קוד 4 — `Piece.submit_block + verify_hash`

**קוד:** `python_engine/piece_manager.py` — `Piece.submit_block`, `Piece.verify_hash`

**ניתוח הקוד:**

- **Block assembly:** `submit_block(offset, data)` מקבל offset של block בתוך ה-piece ואת ה-bytes. הקוד מוצא את ה-Block הרלוונטי לפי offset, מוודא ש-`block.length == len(data)` (אחרת זה data שגוי), ומאחסן ב-`block.data`. הוא גם מעדכן `block.received = True`. הפונקציה מחזירה True אם כל ה-blocks התקבלו (`all(b.received for b in self.blocks)`).
- **Piece reconstruction:** `_data` המלא של ה-piece מורכב ב-`get_data()` שעושה `b''.join(b.data for b in self.blocks)`. הסדר מובטח כי ה-blocks ממוינים לפי offset בקונסטרוקטור. ה-bytes הסופיים הם piece שלם שמוכן לאימות.
- **SHA-1 verification:** `verify_hash()` מחשב `hashlib.sha1(self._data).digest()` ומשווה ל-`expected_hash` שהגיע מ-.torrent. שתי שורות, אבל הן הקרקע של ה-trust במערכת. בלי זה כל peer זדוני יכול להחליף קובץ.
- **Corruption handling:** אם verify_hash מחזיר False, `reset()` נקרא - ה-piece חוזר למצב MISSING, כל ה-blocks מאופסים, ו-request state נמחק. ה-SecurityManager מקבל `report_hash_failure(peer_key, piece_idx)` עם ה-peer האחרון ששלח. אחרי 3 כשלים, ה-peer מקבל ban.

**שאלת עומק: כיצד malicious block flooding יגרום resource exhaustion?**

תרחיש: peer זדוני שולח אליי PIECE messages שלא ביקשתי. אצלי, `submit_block` מוודא שה-offset וה-length תקינים, אבל הוא לא בודק אם ה-block היה ב-`requested` state. אם אני לא בודק זאת, ה-block יישמר ב-`block.data`, יגדיל את גודל הזיכרון שאני מקצה. ב-piece של 256KB יש 16 blocks של 16KB. peer זדוני יכול לשלוח 16 blocks בטרם הספקתי לבקש, וה-piece נחשב complete לפני שביקשתי - וה-hash check ייכשל כי ה-content זדוני, אבל כבר השקעתי 256KB של RAM ו-CPU על SHA-1.

הגנות במימוש: (1) `MAX_PENDING_REQUESTS = 50` per peer - אם peer שולח יותר מ-50 PIECE messages בלי שיש requests pending, זה zigzag לוגי שמתבטא בתשובה לא הגיונית. (2) `_pending_requests` counter שמופחת בכל PIECE - אם הוא יורד ל-0 ו-PIECE עדיין מגיע, אני יכול לזרוק את ההודעה. (3) `MAX_MESSAGE_SIZE = 2MB` בולם הודעת PIECE ענק שמכריזה על length גדול. (4) על piece שכבר completed, ה-PIECE message נדחה בשקט - duplicate guard.

המגבלה האמיתית אצלי: אני *לא* בודק במפורש שה-block היה ב-`requested` state לפני submit. peer יכול לשלוח blocks שלא ביקשתי, ואצלי הם יישמרו. **Resource exhaustion** דרך זה מוגבל ל-256KB per piece (גודל maximum) ול-N pieces (~1600 לקובץ 400MB), כלומר תקרה של ~400MB גם ב-worst case. במציאות זה לא קטסטרופלי, אבל פתרון נכון היה להוסיף בדיקה ש-`block.requested == True` לפני submit. זה מתועד כשיפור עתידי.

---

### תרגיל קוד 5 — `TrackerClient.announce`

**קוד:** `python_engine/tracker_client.py` — `TrackerClient.announce`, `TrackerResponse.__init__`

**ניתוח הקוד:**

- **Announce parameters:** הבקשה היא HTTP GET עם פרמטרים url-encoded: `info_hash` (20 בתים בינאריים, urlencode כ-percent-encoded), `peer_id` (20 בתים), `port` (6881), `uploaded`, `downloaded`, `left` (סטטיסטיקות סשן), `event` (`started`, `completed`, `stopped`, או null לפעולה תקופתית), `compact=1` (לבקש compact peer list).
- **Peer list parsing:** ה-response עצמו ב-bencode. `TrackerResponse.__init__` מפענח ב-`bencode.decode` ומחלץ את ה-fields. ה-peers יכולים להגיע בשתי צורות: compact (string של 6×N בתים, 4 IP + 2 port לכל peer) או dict (list של dicts עם 'ip', 'port', 'peer_id'). אצלי שני הפורמטים נתמכים.
- **Tracker interval handling:** `response['interval']` בשניות - כמה זמן לחכות לפני announce הבא. `_periodic_announce_loop` של TrackerClient רץ ב-task נפרד וקורא ל-`announce()` בכל interval. אם ה-tracker מחזיר interval של 0 (חוקי אבל זדוני - מציף את עצמו), אני אוכף minimum של 60 שניות.
- **Compact peer decoding:** ה-loop `for i in range(0, len(peer_bytes), 6)` קורא 6 בתים בכל iteration. `socket.inet_ntoa(peer_bytes[i:i+4])` נותן IP string, `struct.unpack('>H', peer_bytes[i+4:i+6])[0]` נותן port. תקיפת ולידציה: אם len(peer_bytes) לא מתחלק ב-6, יש שגיאה ב-format - אני זורק exception.

**שאלת עומק: כיצד malicious tracker responses יפגעו ב-peer discovery?**

ה-tracker הוא נקודת trust מרכזית מסוכנת. ב-BitTorrent הקלאסי אני סומך עליו לחלוטין: הוא נותן לי את רשימת ה-peers, ואני מתחבר אליהם בלי ולידציה נוספת. תקיפות אפשריות:

**Eclipse attack:** tracker מחזיר אך ורק peers שבשליטת התוקף. כל ה"peers" שלי הם בעצם sock puppets של אותו תוקף. הוא יכול לשלוח לי data שגוי (אבל SHA-1 יבלום), או להתעלם מבקשות שלי כדי לעצור את ההורדה. אצלי אין הגנה ישירה - הגנה תאורטית: multi-tracker (`announce-list` במקום `announce` יחיד) - אצלי הקוד תומך, אבל אם רק tracker יחיד מוגדר ב-torrent אני בלעדי אליו.

**Information leak:** ה-tracker יודע מי מוריד מה, מתי, וכמה. שאלת privacy עצומה. ב-`security.py` יש docstring שנקרא TRACKER_PRIVACY_ANALYSIS שמתעד את הבעיה הזאת. הפתרון התעשייתי: DHT (שאינו tracker) או trackerless torrents עם PEX.

**DoS via interval:** tracker מחזיר interval של 1 שנייה - אני אציף אותו עצמו ואקרוס תחת load. אצלי `_periodic_announce_loop` אוכף MIN_INTERVAL של 60 שניות.

**Malformed response:** tracker מחזיר peer_bytes שלא מתחלקים ב-6. parsing יזרוק exception, ה-announce ייכשל, אבל הקודמים נשמרו. השפעה חלקית.

**Fake peer count:** tracker מצהיר על 50 peers ומחזיר רק 5 (או 1000 שמתוכם 950 כתובות שגויות). אין לי דרך לאמת. השפעה: rarity counting מוטה, optimism unfounded.

הפתרון האמיתי לאמינות tracker הוא **decentralization**: DHT + PEX מורידים את התלות ב-tracker יחיד. אצלי שניהם לא מומשים ומתועדים כפיתוח עתידי.

---

### תרגיל קוד 6 — `SecurityManager + PeerReputation`

**קוד:** `python_engine/security.py` — `SecurityManager`, `PeerReputation`

**ניתוח הקוד:**

- **Reputation scoring:** `PeerReputation` הוא dataclass per-peer עם `hash_failures: int`, `protocol_violations: int`, `successful_pieces: int`, `trust_score: float`. כל אירוע פונקציות update קוראות לעדכן אותו. ה-score עצמו (`trust_score`) הוא חישוב פשוט: `successful_pieces - 3*hash_failures - 2*protocol_violations`. negative = חשוד.
- **Invalid piece tracking:** `report_hash_failure(peer_key, piece_idx)` מגדיל hash_failures. נקרא מ-`Download._on_peer_message` כש-`verify_piece` מחזיר False. אצלי ה-implementation שלי לא יודע *איזה* peer ספציפית שלח את ה-block הפגום (כי piece מורכב מ-blocks ממקורות שונים), אז ה-blame נופל על ה-peer האחרון שתרם block. זאת מגבלה של גרנולריות piece-level - לא יכול להאשים peer ספציפי על block ספציפי בלי tagging מפורש.
- **Peer banning:** `is_peer_banned(peer_key)` בודק שני ספים: `hash_failures > MAX_HASH_FAILURES_PER_PEER` (3) או `protocol_violations > MAX_PROTOCOL_VIOLATIONS_PER_PEER` (5). אם True, ה-DownloadManager מנתק את ה-PeerConnection ולא מאפשר connect מחדש באותו session.
- **Timeout handling:** אין timeout עליבן - הוא קבוע לכל ה-session. peer שב-ban נשאר ב-ban עד שהאפליקציה מופעלת מחדש. **No decay**.

**שאלת עומק: כיצד Sybil rotation תעקוף את מנגנון המוניטין?**

תרחיש בסיסי: תוקף יוצר 1000 peer_id שונים מאותה מכונה. כל peer_id הוא 20 בתים, נוצר ב-`os.urandom(20)` - יש 2^160 ערכים אפשריים. אין מתאם בין peer_id למכונה הפיזית. כל peer_id מתחיל reputation 0 - "neutral".

מסלול ההתקפה:
1. תוקף מקצה 100MB של pieces פגומים.
2. עם peer_id #1, הוא מתחבר אליי, שולח blocks פגומים, ונחסם אחרי 3 כשלי hash.
3. בינתיים peer_id #2 כבר מתחבר מאותו IP (אצלי ה-ban הוא per-peer_id, לא per-IP).
4. עם peer_id #1000 הוא ממשיך לבזבז לי זמן.

בלי הגנה אחרת, 1000 peer_id × 3 כשלים × ~5 שניות לכשל = 15000 שניות של בזבוז שלי. במציאות זה מוגבל ב-`MAX_CONNECTIONS = 50`, אבל גם 50 peer_id רוטטים זה מספיק כדי להפריע למשך זמן ארוך.

הגנות שיכולתי להוסיף ולא הוספתי:
- **Per-IP ban** במקום per-peer_id. הקושי: NAT - הרבה משתמשים חוקיים מאחורי אותו IP בכלל. ban על IP יחסום אנשים תמימים.
- **Per-subnet ban** (/24). פחות פוגע ב-NAT, יותר ב-cloud providers.
- **Proof-of-work** על handshake - הצד היוצא חייב לחשב hash עם מספר 0-bits כדי להוכיח השקעה. מקטין את כמות peer_id שתוקף יכול להפעיל בו-זמנית.
- **Reputation decay** + **forgiveness** - מאפשר peer חוקי שכשל בגלל network failure להתאושש.

אף אחת מההגנות האלה לא קלה. **identity verification** דרך CA סותרת decentralization. **Proof-of-work** מעניש מובייל. **per-IP** מענישה NAT. הבחירה ב-per peer_id היא בחירה מודעת בפשטות, עם ההכרה שזה רק קו ראשון נגד תוקפים נאיביים. תוקפים מתוחכמים יעקפו. זה מתועד אצלי בספר כמגבלה.

---

### תרגיל קוד 7 — `start_event_loop` + `_run_async`

**קוד:** `python_engine/api_server.py` — `_run_async`, `start_event_loop`

**ניתוח הקוד:**

- **asyncio integration:** ב-startup של ה-Flask app, אני יוצר event loop נפרד ב-thread רקע: `_loop = asyncio.new_event_loop()`, `Thread(target=_loop.run_forever, daemon=True).start()`. ה-thread רץ לנצח עד שהאפליקציה נעצרת.
- **Flask bridge:** `_run_async(coro, timeout=60)` מקבל coroutine ו-מטפל בהרצתה ב-loop השני: `asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout=timeout)`. ה-Flask thread (המקורי) חוסם עד שה-coro מסיים ב-loop. כל endpoint שמדבר עם ה-engine קורא ל-`_run_async`.
- **Thread coordination:** שני threads עיקריים - Flask worker (אחד מכמה ב-pool) ו-asyncio event loop (יחיד, daemon). הקואורדינציה היא דרך ה-future של `run_coroutine_threadsafe` - thread-safe דרך internal locks של asyncio. אין mutex מפורש בקוד שלי.
- **Async task lifecycle:** tasks ב-asyncio נוצרות מ-`asyncio.create_task()` בתוך coroutines רצות. ב-download flow: `_download_loop` הוא task ראשי, ובתוכו `create_task` ל-`_choke_loop`, `_keep_alive_loop`, ולכל `_message_loop` per peer. ה-tasks מתגלגלות עד `pause()` או `cancel()` ש-cancels אותן explicitly.

**שאלת עומק: כיצד blocking REST calls יגרמו event-loop starvation?**

תרחיש: Flask handler קורא ל-`_run_async(download.get_status(), timeout=60)`. בתוך `get_status` יש קוד נראה תמים: `stats = self._compute_stats(); time.sleep(2); return stats`. ה-`time.sleep(2)` הוא **blocking** - הוא חוסם את ה-thread שעליו הוא רץ. וה-thread הזה הוא ה-event loop של asyncio!

**Event-loop starvation:** במהלך 2 השניות האלה:
- כל ה-coroutines האחרות שלא הספיקו לאוטל `await` הן ממתינות, כי ה-loop לא מתקדם.
- כל `_message_loop` של כל peer מקופאים. הם לא קוראים מהsockets שלהם.
- ה-OS receive buffers של ה-sockets מתחילים להתמלא ב-data מ-peers.
- ברגע שהם מתמלאים, TCP backpressure מופעלת - peers שולחים flow control משלהם.
- במקרים קיצוניים, peers לאחר timeout שולחים RST ומתנתקים מהצד שלהם.

תוצאה ראלית של `time.sleep(2)` אחד: ניתוקים המוניים של peers, איפוס של download state. הבעיה היא שזה לא זורק error - הקוד עובד "תקין", רק הביצועים קטסטרופליים.

הגנות במימוש שלי:
- כל פעולה חוסמת *חייבת* לעבור ל-`loop.run_in_executor(self._executor, ...)`. ה-executor הוא `ThreadPoolExecutor(max_workers=2)` שמטפל בעבודה חוסמת בלי לחסום את ה-event loop.
- הקוד שעובר ב-executor הוא: hash verification (`hashlib.sha1`), disk write (`file.write`), ולפעמים disk read (ב-restore_state).
- ה-`asyncio.sleep` הוא תמיד בשימוש במקום `time.sleep`. ה-IO הוא תמיד `await reader.read()` במקום `socket.recv()`.

הקושי בפרקטיקה: זה lint שאני צריך לעשות בעצמי. אין `mypy` plugin שיתפוס `time.sleep` בתוך coroutine ויזרוק error. בתחילת הפרויקט אכן נתקלתי בכמה bugs כאלה - ה-engine פשוט פעל לאט בלי סיבה ברורה, וזיהיתי את הסיבה רק אחרי הוספת logging מפורט. הלקח הזה מתועד בספר.

---

## הערות לימוד

- **קודם תשובה, אז הצבעה לקוד.** הבוחן יקשיב להגדרה ואז יבקש להראות. תמיד יש לי file:line מוכן.
- **הביקורת היא הזדמנות, לא הגנה.** כשהוא שואל "למה זה לא טוב?" - אני נכנס לשם בלי לפחד. הוא רוצה לראות שאני יודע *איפה* זה לא מושלם, לא לשמוע שזה מושלם.
- **כל מילה מ"חובה להתייחס" צריכה להיאמר בקול.** הוא כתב אותן במפורש - הוא יבדוק שאני אמרתי אותן. בכל תשובה, סימנתי איפה כל מושג מהרשימה מופיע.
- **קוד שלא ראיתי - "אני אסתכל".** אם הוא שואל על שורה שאני לא זוכר בעל-פה, מתפיש את הלפטופ ופותח את הקובץ. עדיף "לא בעל-פה" מ"אמרתי משהו לא נכון".

</div>
