# Fig-03 — תרשים ארכיטקטורת רשת (Network Architecture)

**פרק בספר**: 11.4 (תקשורת ופרוטוקולי רשת).
**סוג**: תרשים זרימת רשת — שלוש שכבות תקשורת שונות.

---

## התרשים

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'background':'#FFFFFF', 'primaryColor':'#FFFFFF', 'primaryBorderColor':'#000000', 'primaryTextColor':'#000000', 'lineColor':'#000000', 'edgeLabelBackground':'#FFFFFF', 'tertiaryColor':'#FFFFFF', 'clusterBkg':'#FFFFFF', 'clusterBorder':'#888888'}}}%%
flowchart LR
    subgraph LOCAL["Local Host (loopback 127.0.0.1)"]
        direction TB
        GUI["Java GUI<br/>(Swing)"]
        ENG["Python Engine<br/>(Flask + asyncio)"]
    end

    TRK[("Tracker<br/>external HTTP/HTTPS server")]

    subgraph SWARM["BitTorrent Swarm"]
        direction TB
        P1[("Peer 1")]
        P2[("Peer 2")]
        P3[("Peer 3")]
        P4[("Peer 4")]
        P5[("Peer 5")]
    end

    GUI <==>|"🟢 Local IPC<br/>HTTP / JSON<br/>localhost:5000"| ENG
    ENG <==>|"🔵 HTTP Tracker<br/>Bencode response<br/>port 80 / 443"| TRK
    ENG ==>|"🟠 Peer Wire Protocol<br/>TCP / BEP-3<br/>port 6881 + dynamic"| P1
    ENG ==>|" "| P2
    ENG ==>|" "| P3
    ENG ==>|" "| P4
    ENG ==>|" "| P5

    classDef proc   fill:#FFFFFF,stroke:#188038,stroke-width:2.5px,color:#000;
    classDef trk    fill:#FFFFFF,stroke:#1A73E8,stroke-width:2.5px,color:#000;
    classDef peer   fill:#FFFFFF,stroke:#E37400,stroke-width:2.5px,color:#000;
    class GUI,ENG proc;
    class TRK trk;
    class P1,P2,P3,P4,P5 peer;

    linkStyle 0 stroke:#188038,stroke-width:2.5px;
    linkStyle 1 stroke:#1A73E8,stroke-width:2.5px;
    linkStyle 2 stroke:#E37400,stroke-width:2.5px;
    linkStyle 3 stroke:#E37400,stroke-width:2px;
    linkStyle 4 stroke:#E37400,stroke-width:2px;
    linkStyle 5 stroke:#E37400,stroke-width:2px;
    linkStyle 6 stroke:#E37400,stroke-width:2px;
```

---

## שלוש שכבות התקשורת

| צבע | שכבה | פרוטוקול | פורט | שימוש |
|---|---|---|---|---|
| 🟢 **ירוק** | Local IPC | HTTP / JSON | `localhost:5000` | GUI ↔ Engine (REST) — תמיד על loopback בלבד |
| 🔵 **כחול** | HTTP Tracker | HTTP / HTTPS עם תשובה ב-Bencode | `80` / `443` | Engine ↔ Tracker — `announce` תקופתי |
| 🟠 **כתום** | Peer Wire | TCP raw + BEP-3 | `6881` + דינמי | Engine ↔ Peers — `handshake`, `BITFIELD`, `REQUEST`, `PIECE`, `HAVE`, `CHOKE`/`UNCHOKE` |

> **הערה**: רק 5 peers מוצגים כייצוג סכמטי של ה-swarm. בפועל ה-`Download` יכול לנהל עד עשרות חיבורים מקבילים (`max_workers` מוגבל בקוד).

---

## מקור לאימות (קוד)

| ערך בתרשים | מיקום בקוד |
|---|---|
| `localhost:5000` | `python_engine/api_server.py:499` — `run_server(host='127.0.0.1', port=5000)` |
| `port 6881` (BitTorrent default) | `python_engine/tracker_client.py:23` — `DEFAULT_PORT = 6881` |
| TCP פתיחת חיבור ל-peer | `python_engine/peer_connection.py:166` — `asyncio.open_connection(self.ip, self.port)` |
| Handshake 68 בתים | `python_engine/peer_connection.py:20` — `HANDSHAKE_LEN = 68` |
| `Bencode response` מ-tracker | `python_engine/tracker_client.py:97-128` — parser של רשימת peers בפורמט compact/dict |

---

## איך להעתיק את התרשים ל-Google Docs / Word

1. גש ל-**https://mermaid.live**
2. מחק את הקוד שמופיע משמאל.
3. העתק את הקוד מתחת ל-` ```mermaid ` עד לפני ` ``` ` (כולל שורת `%%{init...`).
4. הדבק משמאל. התרשים מתעדכן מימין על רקע לבן.
5. **Actions → PNG** (או SVG לאיכות גבוהה).
6. ב-Google Docs: `Insert → Image → Upload from computer`.

חלופה: פתח את הקובץ ב-GitHub וצלם את התרשים (`Win+Shift+S` / `Cmd+Shift+4`).
