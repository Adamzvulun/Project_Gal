# Fig-02 — תרשים ארכיטקטורה (Top-Down Level Design)

**פרק בספר**: 11.1 (ארכיטקטורה כללית).
**סוג**: תרשים ארכיטקטורה דו-רמתי.

---

## רמה 1 — ארכיטקטורה כללית (Top Level)

```mermaid
flowchart LR
    GUI["Java GUI<br/>(Swing • JFrame)"]
    ENG["Python Engine<br/>(asyncio • Flask)"]
    TRK[("Tracker<br/>external")]
    PEERS[("Peers 1..N<br/>swarm")]

    GUI <-->|"HTTP / REST<br/>localhost:5000"| ENG
    ENG <-->|"HTTP / HTTPS<br/>announce"| TRK
    ENG <-->|"TCP / BEP-3<br/>peer-wire protocol"| PEERS

    classDef proc fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#000;
    classDef ext  fill:#FFF4E5,stroke:#E37400,stroke-width:2px,color:#000;
    class GUI,ENG proc;
    class TRK,PEERS ext;
```

---

## רמה 2 — פירוט המודולים בתוך Python Engine

```mermaid
flowchart TB
    subgraph PE["Python Engine"]
        direction TB
        API["Flask REST API<br/>(api_server.py)"]
        DM["DownloadManager<br/>(download_manager.py)"]
        DL["Download<br/>(download_manager.py)"]
        PM["PieceManager<br/>(piece_manager.py)"]
        PC["PeerConnection *<br/>(peer_connection.py)"]
        TC["TrackerClient<br/>(tracker_client.py)"]
        SM["SecurityManager<br/>(security.py)"]
        TM["TorrentMetadata<br/>(torrent_metadata.py)"]
        BC["Bencode<br/>(bencode.py)"]

        API --> DM
        DM --> TM
        DM --> DL
        DL --> PM
        DL --> SM
        DL --> TC
        DL --> PC
        TM --> BC
        TC --> BC
    end

    GUI2["Java GUI"] <-.HTTP/JSON.-> API
    TC <-.HTTP announce.-> TRK2[("Tracker")]
    PC <-.TCP BEP-3.-> PEERS2[("Peers")]

    classDef mod fill:#E8F0FE,stroke:#1A73E8,stroke-width:1.5px,color:#000;
    classDef ext fill:#FFF4E5,stroke:#E37400,stroke-width:2px,color:#000;
    classDef gui fill:#E6F4EA,stroke:#188038,stroke-width:2px,color:#000;
    class API,DM,DL,PM,PC,TC,SM,TM,BC mod;
    class TRK2,PEERS2 ext;
    class GUI2 gui;
```

---

## מקרא

- **כחול**: רכיב פנימי של המערכת (Python Engine).
- **ירוק**: רכיב פנימי של המערכת (Java GUI).
- **כתום**: רכיב חיצוני (Tracker, Peers).
- **חץ מלא (`──►`)**: תלות ישירה / קריאת מתודה.
- **חץ מקווקו (`-.->`)**: תקשורת רשת.
- **כוכבית ליד `PeerConnection *`**: ריבוי instances — אחד לכל peer פעיל.

## מקור לאימות (קוד)

| מודול בתרשים | קובץ מקור | מחלקה ראשית |
|---|---|---|
| Flask REST API | `python_engine/api_server.py` | (Flask app) |
| DownloadManager | `python_engine/download_manager.py` | `DownloadManager` (line 816) |
| Download | `python_engine/download_manager.py` | `Download` (line 87) |
| PieceManager | `python_engine/piece_manager.py` | `PieceManager` (line 148) |
| PeerConnection | `python_engine/peer_connection.py` | `PeerConnection` (line 98) |
| TrackerClient | `python_engine/tracker_client.py` | `TrackerClient` (line 135) |
| SecurityManager | `python_engine/security.py` | `SecurityManager` (line 79) |
| TorrentMetadata | `python_engine/torrent_metadata.py` | `TorrentMetadata` (line 31) |
| Bencode | `python_engine/bencode.py` | `encode` / `decode` |
