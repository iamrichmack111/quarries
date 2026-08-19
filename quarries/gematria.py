from __future__ import annotations
import re
import unicodedata

STANDARD = {
    "א":1,"ב":2,"ג":3,"ד":4,"ה":5,"ו":6,"ז":7,"ח":8,"ט":9,
    "י":10,"כ":20,"ך":20,"ל":30,"מ":40,"ם":40,"נ":50,"ן":50,
    "ס":60,"ע":70,"פ":80,"ף":80,"צ":90,"ץ":90,"ק":100,"ר":200,"ש":300,"ת":400,
}
GADOL = dict(STANDARD)
GADOL.update({"ך":500,"ם":600,"ן":700,"ף":800,"ץ":900})
VALUES = GADOL  # backward compatibility

ALPHABET = list("אבגדהוזחטיכלמנסעפצקרשת")
ORDINAL = {ch:i+1 for i,ch in enumerate(ALPHABET)}
for final,normal in {"ך":"כ","ם":"מ","ן":"נ","ף":"פ","ץ":"צ"}.items():
    ORDINAL[final]=ORDINAL[normal]

LETTER_NAMES = {
    "א":"אלף","ב":"בית","ג":"גימל","ד":"דלת","ה":"הא","ו":"וו","ז":"זין","ח":"חית",
    "ט":"טית","י":"יוד","כ":"כף","ך":"כף","ל":"למד","מ":"מם","ם":"מם","נ":"נון",
    "ן":"נון","ס":"סמך","ע":"עין","פ":"פא","ף":"פא","צ":"צדי","ץ":"צדי",
    "ק":"קוף","ר":"ריש","ש":"שן","ת":"תו",
}

ATBASH = dict(zip(ALPHABET, reversed(ALPHABET)))
ALBAM = {ALPHABET[i]:ALPHABET[(i+11)%22] for i in range(22)}
AVGAD = {ALPHABET[i]:ALPHABET[(i+1)%22] for i in range(22)}
REV_AVGAD = {ALPHABET[i]:ALPHABET[(i-1)%22] for i in range(22)}
OFANIM = {ch: LETTER_NAMES[ch][-1] for ch in ALPHABET}

FINAL_TO_NORMAL={"ך":"כ","ם":"מ","ן":"נ","ף":"פ","ץ":"צ"}

def _nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text or "")

def hebrew_letters(text: str) -> str:
    return "".join(ch for ch in _nfd(text) if ch in GADOL)

def hebrew_words(text: str) -> list[str]:
    cleaned=[]
    for token in re.split(r"\s+", _nfd(text or "").strip()):
        letters="".join(ch for ch in token if ch in GADOL)
        if letters:
            cleaned.append(letters)
    return cleaned

def _normal(ch: str) -> str:
    return FINAL_TO_NORMAL.get(ch,ch)

def mispar_hechrachi(text: str) -> int:
    return sum(STANDARD[ch] for ch in hebrew_letters(text))

def mispar_gadol(text: str) -> int:
    return sum(GADOL[ch] for ch in hebrew_letters(text))

def mispar_siduri(text: str) -> int:
    return sum(ORDINAL[ch] for ch in hebrew_letters(text))

def mispar_katan(text: str) -> int:
    def reduce_digit(n:int)->int:
        return 0 if n==0 else 1 + ((n-1)%9)
    return sum(reduce_digit(STANDARD[ch]) for ch in hebrew_letters(text))

def mispar_perati(text: str) -> int:
    return sum(STANDARD[ch] ** 2 for ch in hebrew_letters(text))

def mispar_meshulash(text: str) -> int:
    return sum(STANDARD[ch] ** 3 for ch in hebrew_letters(text))

def mispar_musafi(text: str) -> int:
    letters=hebrew_letters(text)
    return mispar_hechrachi(letters)+len(letters)

def mispar_kolel(text: str) -> int:
    return mispar_hechrachi(text)+len(hebrew_words(text))

def mispar_boneh(text: str) -> int:
    vals=[STANDARD[ch] for ch in hebrew_letters(text)]
    running=0
    total=0
    for v in vals:
        running += v
        total += running
    return total

def mispar_kidmi(text: str) -> int:
    return sum(n*(n+1)//2 for n in (ORDINAL[ch] for ch in hebrew_letters(text)))

def mispar_haachor(text: str) -> int:
    return sum((i+1)*STANDARD[ch] for i,ch in enumerate(hebrew_letters(text)))

def digital_root(n: int) -> int:
    return 0 if n == 0 else 1 + ((n-1) % 9)

def mispar_katan_mispari(text: str) -> int:
    return digital_root(mispar_hechrachi(text))

def mispar_shemi(text: str) -> int:
    return sum(mispar_hechrachi(LETTER_NAMES[ch]) for ch in hebrew_letters(text))

def mispar_neelam(text: str) -> int:
    total=0
    for ch in hebrew_letters(text):
        name=LETTER_NAMES[ch]
        total += mispar_hechrachi(name[1:])
    return total

def transform(text: str, mapping: dict[str,str]) -> str:
    out=[]
    for ch in _nfd(text):
        base=_normal(ch)
        out.append(mapping.get(base,ch))
    return "".join(out)

def method_results(text: str) -> list[dict[str,object]]:
    letters=hebrew_letters(text)
    if not letters:
        return []
    transformed = {
        "AtBash": transform(letters, ATBASH),
        "Albam": transform(letters, ALBAM),
        "Ofanim": transform(letters, OFANIM),
        "Avgad": transform(letters, AVGAD),
        "Reverse Avgad": transform(letters, REV_AVGAD),
    }
    rows=[
        ("Mispar Hechrachi","מספר הכרחי",mispar_hechrachi(text),"Standard/absolute letter values",""),
        ("Mispar Gadol","מספר גדול",mispar_gadol(text),"Final forms use 500–900",""),
        ("Mispar Siduri","מספר סידורי",mispar_siduri(text),"Ordinal positions 1–22",""),
        ("Mispar Katan","מספר קטן",mispar_katan(text),"Each standard letter value reduced to 1–9",""),
        ("Mispar Perati","מספר הפרטי",mispar_perati(text),"Square each standard letter value, then sum",""),
        ("Mispar Shemi","מספר שמי מילוי",mispar_shemi(text),"Letter-name values using the source chart spellings",""),
        ("Mispar Musafi","מספר מוספי",mispar_musafi(text),"Hechrachi + number of Hebrew letters",""),
        ("Mispar Bone'eh","מספר בונה",mispar_boneh(text),"Sum cumulative prefixes",""),
        ("Mispar Kidmi","מספר קדמי",mispar_kidmi(text),"Triangular ordinal value of each letter",""),
        ("Mispar Ne'elam","מספר נעלם",mispar_neelam(text),"Letter-name value excluding the letter itself; source spellings",""),
        ("Mispar Meshulash","מספר משולש",mispar_meshulash(text),"Cube each standard value, then sum",""),
        ("Mispar Ha'achor","מספר האחור",mispar_haachor(text),"Standard value × position in the word/phrase",""),
        ("Mispar Katan Mispari","מספר קטן מספרי",mispar_katan_mispari(text),"Digital root of Hechrachi total",""),
        ("Mispar Kolel","מספר כלל",mispar_kolel(text),"Hechrachi + number of Hebrew words",""),
    ]
    for name,heb in [("AtBash","אתב״ש"),("Albam","אלב״ם"),("Ofanim","אופנים"),
                     ("Avgad","אבג״ד"),("Reverse Avgad","אבג״ד הפוך")]:
        t=transformed[name]
        rows.append((name,heb,mispar_hechrachi(t),"Transform letters, then total with standard values",t))
    return [
        {"method":name,"hebrew_name":heb,"value":value,"rule":rule,"transformed":xform}
        for name,heb,value,rule,xform in rows
    ]


def hebrew_numeral(n: int) -> str:
    """Render a positive integer with conventional Hebrew numeral letters.

    Thousands are separated with a geresh; 15/16 use ט״ו/ט״ז to avoid
    spelling divine names. This is a numeral representation, not a gloss.
    """
    if n <= 0:
        return "—"
    ones = [(9,"ט"),(8,"ח"),(7,"ז"),(6,"ו"),(5,"ה"),(4,"ד"),(3,"ג"),(2,"ב"),(1,"א")]
    tens = [(90,"צ"),(80,"פ"),(70,"ע"),(60,"ס"),(50,"נ"),(40,"מ"),(30,"ל"),(20,"כ"),(10,"י")]
    hundreds = [(400,"ת"),(300,"ש"),(200,"ר"),(100,"ק")]

    def under_1000(value: int) -> str:
        letters=[]
        while value >= 400:
            letters.append("ת"); value -= 400
        for amount, letter in hundreds[1:]:
            if value >= amount:
                letters.append(letter); value -= amount
        if value == 15:
            letters += ["ט","ו"]; value = 0
        elif value == 16:
            letters += ["ט","ז"]; value = 0
        else:
            for amount, letter in tens:
                if value >= amount:
                    letters.append(letter); value -= amount
            for amount, letter in ones:
                if value >= amount:
                    letters.append(letter); value -= amount
        if not letters:
            return ""
        return letters[0] + "׳" if len(letters)==1 else "".join(letters[:-1]) + "״" + letters[-1]

    if n < 1000:
        return under_1000(n)
    thousands, rest = divmod(n, 1000)
    prefix = under_1000(thousands).replace("״", "").replace("׳", "") + "׳"
    return prefix + (" " + under_1000(rest) if rest else "")


def prime_factorization(n: int) -> list[tuple[int,int]]:
    if n < 2:
        return []
    out=[]
    d=2
    while d*d <= n:
        exp=0
        while n%d==0:
            n//=d
            exp+=1
        if exp:
            out.append((d,exp))
        d += 1 if d==2 else 2
    if n>1:
        out.append((n,1))
    return out

def factorization_text(n: int) -> str:
    factors=prime_factorization(n)
    if not factors:
        return str(n)
    return " × ".join(str(p) if e==1 else f"{p}^{e}" for p,e in factors)

def reduction_chain(n: int) -> list[int]:
    out=[n]
    while n>=10:
        n=sum(int(d) for d in str(abs(n)))
        out.append(n)
    return out

def number_explanation(n: int) -> str:
    chain=" → ".join(map(str,reduction_chain(n)))
    factors=factorization_text(n)
    return (
        f"[b]Number structure[/b]\n"
        f"Digit reduction: {chain} (repeatedly add decimal digits).\n"
        f"Prime factorization: {n} = {factors}. "
        "This shows the unique prime building blocks of the number; it is arithmetic metadata, "
        "not a separate gematria method."
    )

def breakdown(text: str) -> str:
    letters=hebrew_letters(text)
    if not letters:
        return "—"
    return " + ".join(f"{ch}({GADOL[ch]})" for ch in letters) + f" = {mispar_gadol(letters)}"
