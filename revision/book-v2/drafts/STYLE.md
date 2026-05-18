# Drafting style — book sections

All prose written into `revision/book-v2/drafts/*.md` and from there
into the .docx must follow these rules.

## Rules

1. **No first-person possessives or plurals.** Never write:
   * `שלנו` / `שלי` / `שלכם`
   * `אנחנו` / `אני` / `אצלנו` / `אצלי`
   * `היינו` / `נבנינו` / `בנינו`
   * `בפרויקט שלנו` / `המערכת שלנו` / `המימוש שלנו`

   Instead, use impersonal phrasing:
   * `שלנו` → drop entirely, or use `הזה` / `הנוכחי` / a definite
     article (`ה-...`) / or restate the noun:
     * "המימוש שלנו של rarest-first" → "המימוש של rarest-first"
     * "ה-`PeerConnection` שלנו" → "ה-`PeerConnection`"
     * "המערכת שלנו" → "המערכת" / "הפרויקט"
   * `אנחנו רוצים למדוד` → `הנמדד` / `הנבדק`
   * `היינו צריכים` → `נדרשת` / `נדרש`
   * `שלא בנינו` / `שלא נבנתה` → `שאינו כלול בפרויקט`

2. **Hebrew as the body language.** English only for: code identifiers
   (`PeerConnection`, `bencode.encode`), file paths, BEP numbers,
   wire-protocol terms (handshake, bitfield, request, piece, unchoke,
   tit-for-tat, rarest-first), and standard CS terms with no concise
   Hebrew equivalent (event loop, sliding window).

3. **Pain points are welcome.** Concrete failures and the fix that
   resolved them are a feature, not a bug — they're what the teacher
   said was missing. State them in third person:
   *"בגרסה ראשונה, ..."* / *"בלי מנגנון X, ..."* — not
   *"בהתחלה ניסיתי..."*.

4. **Every algorithmic claim cites a `file:line`.** Format:
   `cite: download_manager.py:537`. Inside a sentence:
   *"...ב-`download_manager.py:537`"*.

5. **No bravado.** Avoid: "מערכת חזקה", "production-grade",
   "advanced", "robust", "מתקדם". Replace with what was actually
   measured, or with "תוכננה לתמוך ב..." when not measured.
