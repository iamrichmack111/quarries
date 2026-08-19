from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
import math

try:
    import swisseph as swe
except ImportError:  # pragma: no cover
    swe = None

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_META = {
    "Aries": ("Fire","Cardinal","Yang"), "Taurus": ("Earth","Fixed","Yin"),
    "Gemini": ("Air","Mutable","Yang"), "Cancer": ("Water","Cardinal","Yin"),
    "Leo": ("Fire","Fixed","Yang"), "Virgo": ("Earth","Mutable","Yin"),
    "Libra": ("Air","Cardinal","Yang"), "Scorpio": ("Water","Fixed","Yin"),
    "Sagittarius": ("Fire","Mutable","Yang"), "Capricorn": ("Earth","Cardinal","Yin"),
    "Aquarius": ("Air","Fixed","Yang"), "Pisces": ("Water","Mutable","Yin"),
}


SIGN_FACTS_BLOCK = """IMMUTABLE SIGN FACTS — DO NOT OVERRIDE
Aries = Fire / Cardinal / Yang
Taurus = Earth / Fixed / Yin
Gemini = Air / Mutable / Yang
Cancer = Water / Cardinal / Yin
Leo = Fire / Fixed / Yang
Virgo = Earth / Mutable / Yin
Libra = Air / Cardinal / Yang
Scorpio = Water / Fixed / Yin
Sagittarius = Fire / Mutable / Yang
Capricorn = Earth / Cardinal / Yin
Aquarius = Air / Fixed / Yang
Pisces = Water / Mutable / Yin
"""

HOUSE_SYSTEMS = {
    "Placidus": b"P", "Whole Sign": b"W", "Equal": b"E", "Koch": b"K",
    "Campanus": b"C", "Regiomontanus": b"R", "Porphyry": b"O",
}

HOUSE_DOMAINS = {
    1: "self, identity, body, approach to life",
    2: "personal resources, possessions, values",
    3: "communication, learning, siblings, local travel",
    4: "home, family, roots, private foundation",
    5: "creativity, romance, children, pleasure",
    6: "daily work, service, routines, health",
    7: "partnerships, contracts, one-to-one relationships",
    8: "shared resources, inheritance, intimacy, transformation",
    9: "higher learning, philosophy, religion, long-distance travel",
    10: "career, public reputation, vocation, authority",
    11: "friends, groups, networks, long-range hopes",
    12: "seclusion, retreat, hidden matters, inner life",
}
SIDEREAL_MODES = {
    "Fagan/Bradley": "SIDM_FAGAN_BRADLEY", "Lahiri": "SIDM_LAHIRI",
    "Raman": "SIDM_RAMAN", "Krishnamurti": "SIDM_KRISHNAMURTI",
}

# Standard traditional essential-dignity map. Modern bodies are intentionally not assigned.
DOMICILE = {
    "Sun":{"Leo"}, "Moon":{"Cancer"}, "Mercury":{"Gemini","Virgo"},
    "Venus":{"Taurus","Libra"}, "Mars":{"Aries","Scorpio"},
    "Jupiter":{"Sagittarius","Pisces"}, "Saturn":{"Capricorn","Aquarius"},
}
EXALTATION = {"Sun":"Aries","Moon":"Taurus","Mercury":"Virgo","Venus":"Pisces","Mars":"Capricorn","Jupiter":"Cancer","Saturn":"Libra"}
OPPOSITE = {SIGNS[i]: SIGNS[(i+6)%12] for i in range(12)}
FALL_SIGN = {planet: OPPOSITE[sign] for planet, sign in EXALTATION.items()}

ASPECTS = [
    ("Conjunction",0,8), ("Opposition",180,8), ("Trine",120,7), ("Square",90,7),
    ("Sextile",60,5), ("Quincunx",150,3), ("Semisextile",30,2),
    ("Semisquare",45,2), ("Sesquiquadrate",135,2),
]

@dataclass
class BodyPosition:
    name: str
    longitude: float
    speed: float
    sign: str
    degree: float
    house: int
    retrograde: bool
    element: str
    modality: str
    polarity: str
    dignity: str

@dataclass
class Chart:
    local_dt: datetime
    latitude: float
    longitude: float
    timezone_name: str
    zodiac_mode: str
    house_system: str
    ascendant: float
    mc: float
    cusps: list[float]
    bodies: list[BodyPosition]
    aspects: list[dict]
    sunrise: datetime | None
    sunset: datetime | None
    moon_phase: str
    moon_illumination: float


def _norm(x: float) -> float:
    return x % 360.0


def sign_degree(lon: float) -> tuple[str,float]:
    lon=_norm(lon); idx=int(lon//30)
    return SIGNS[idx], lon%30


def fmt_lon(lon: float) -> str:
    sign, deg=sign_degree(lon); d=int(deg); minutes=int(round((deg-d)*60))
    if minutes == 60: d += 1; minutes = 0
    return f"{d:02d}°{minutes:02d}′ {sign}"


def _house_for(lon: float, cusps: list[float]) -> int:
    lon=_norm(lon)
    for i in range(12):
        start=_norm(cusps[i]); end=_norm(cusps[(i+1)%12])
        span=(end-start)%360; pos=(lon-start)%360
        if pos < span or math.isclose(pos, span, abs_tol=1e-9):
            return i+1
    return 12


def _dignity(name: str, sign: str) -> str:
    if name not in DOMICILE:
        return "—"
    if sign in DOMICILE[name]: return "Domicile"
    if EXALTATION.get(name)==sign: return "Exaltation"
    if FALL_SIGN.get(name)==sign: return "Fall"
    if any(OPPOSITE[s]==sign for s in DOMICILE[name]): return "Detriment"
    return "Peregrine"


def _jd_from_utc(dt: datetime) -> float:
    u=dt.astimezone(timezone.utc)
    hour=u.hour + u.minute/60 + (u.second + u.microsecond/1e6)/3600
    return swe.julday(u.year,u.month,u.day,hour,swe.GREG_CAL)


def _utc_from_jd(jd: float) -> datetime:
    y,m,d,h=swe.revjul(jd,swe.GREG_CAL); hh=int(h); mm=int((h-hh)*60); ss=int(round((((h-hh)*60)-mm)*60))
    if ss==60: ss=59
    return datetime(y,m,d,hh,mm,ss,tzinfo=timezone.utc)


def _sun_event(day: date, lat: float, lon: float, tz: ZoneInfo, event: int) -> datetime | None:
    local_midnight=datetime.combine(day,time.min,tzinfo=tz)
    jd=_jd_from_utc(local_midnight)
    try:
        res,tret=swe.rise_trans(jd,swe.SUN,event,(lon,lat,0.0),0.0,15.0,swe.FLG_SWIEPH)
        if res != 0: return None
        return _utc_from_jd(tret[0]).astimezone(tz)
    except Exception:
        return None


def _phase_name(angle: float) -> str:
    names=["New Moon","Waxing Crescent","First Quarter","Waxing Gibbous","Full Moon","Waning Gibbous","Last Quarter","Waning Crescent"]
    return names[int((angle+22.5)//45)%8]


def calculate_chart(*, local_dt: datetime, latitude: float, longitude: float,
                    timezone_name: str, zodiac_mode: str="Tropical",
                    sidereal_mode: str="Lahiri", house_system: str="Placidus") -> Chart:
    if swe is None: raise RuntimeError("pyswisseph is not installed")
    if not (-90 <= latitude <= 90): raise ValueError("Latitude must be between -90 and 90")
    if not (-180 <= longitude <= 180): raise ValueError("Longitude must be between -180 and 180")
    tz=ZoneInfo(timezone_name)
    if local_dt.tzinfo is None: local_dt=local_dt.replace(tzinfo=tz)
    else: local_dt=local_dt.astimezone(tz)
    jd=_jd_from_utc(local_dt)
    flags=swe.FLG_SWIEPH|swe.FLG_SPEED
    hflags=0
    if zodiac_mode == "Sidereal":
        sid_const=getattr(swe,SIDEREAL_MODES.get(sidereal_mode,"SIDM_LAHIRI"))
        swe.set_sid_mode(sid_const)
        flags |= swe.FLG_SIDEREAL; hflags |= swe.FLG_SIDEREAL
    hcode=HOUSE_SYSTEMS.get(house_system,b"P")
    cusps,ascmc=swe.houses_ex(jd,latitude,longitude,hcode,hflags)
    cusps=list(cusps); ascendant=_norm(ascmc[0]); mc=_norm(ascmc[1])
    specs=[("Sun",swe.SUN),("Moon",swe.MOON),("Mercury",swe.MERCURY),("Venus",swe.VENUS),("Mars",swe.MARS),("Jupiter",swe.JUPITER),("Saturn",swe.SATURN),("Uranus",swe.URANUS),("Neptune",swe.NEPTUNE),("Pluto",swe.PLUTO),("True Node",swe.TRUE_NODE),("Chiron",swe.CHIRON)]
    bodies=[]
    for name,pid in specs:
        try:
            xx,_=swe.calc_ut(jd,pid,flags); lon=_norm(xx[0]); speed=xx[3]
        except Exception:
            continue
        sign,degree=sign_degree(lon); element,modality,polarity=SIGN_META[sign]
        bodies.append(BodyPosition(name,lon,speed,sign,degree,_house_for(lon,cusps),speed<0,element,modality,polarity,_dignity(name,sign)))
    # South Node is exactly opposite the True Node for this display.
    node=next((b for b in bodies if b.name=="True Node"),None)
    if node:
        lon=_norm(node.longitude+180); sign,degree=sign_degree(lon); element,modality,polarity=SIGN_META[sign]
        bodies.append(BodyPosition("South Node",lon,node.speed,sign,degree,_house_for(lon,cusps),node.retrograde,element,modality,polarity,"—"))
    aspects=[]
    for i,a in enumerate(bodies):
        for b in bodies[i+1:]:
            separation=abs((a.longitude-b.longitude+180)%360-180)
            for name,angle,orb in ASPECTS:
                delta=abs(separation-angle)
                if delta <= orb:
                    aspects.append({"a":a.name,"b":b.name,"aspect":name,"angle":angle,"orb":delta,"separation":separation})
                    break
    aspects.sort(key=lambda x:x["orb"])
    sun=next(b for b in bodies if b.name=="Sun"); moon=next(b for b in bodies if b.name=="Moon")
    elongation=_norm(moon.longitude-sun.longitude); illumination=(1-math.cos(math.radians(elongation)))/2*100
    sunrise=_sun_event(local_dt.date(),latitude,longitude,tz,swe.CALC_RISE|swe.BIT_DISC_CENTER)
    sunset=_sun_event(local_dt.date(),latitude,longitude,tz,swe.CALC_SET|swe.BIT_DISC_CENTER)
    return Chart(local_dt,latitude,longitude,timezone_name,zodiac_mode,house_system,ascendant,mc,cusps,bodies,aspects,sunrise,sunset,_phase_name(elongation),illumination)


def format_chart(chart: Chart) -> str:
    def dtfmt(v): return v.strftime("%Y-%m-%d %I:%M:%S %p %Z") if v else "No event at this latitude/date"
    lines=[
        f"OBSERVATORY — {chart.zodiac_mode} / {chart.house_system}",
        f"Local time: {dtfmt(chart.local_dt)}",
        f"Location: {chart.latitude:.5f}, {chart.longitude:.5f}  •  {chart.timezone_name}",
        "",
        f"Sunrise: {dtfmt(chart.sunrise)}",
        f"Sunset:  {dtfmt(chart.sunset)}",
        f"Moon: {chart.moon_phase} • {chart.moon_illumination:.1f}% illuminated",
        "",
        f"ASC: {fmt_lon(chart.ascendant)}    DSC: {fmt_lon(chart.ascendant+180)}",
        f"MC:  {fmt_lon(chart.mc)}    IC:  {fmt_lon(chart.mc+180)}",
        "",
        "PLANETS / POINTS",
    ]
    for b in chart.bodies:
        motion=" ℞" if b.retrograde else ""
        lines.append(
            f"{b.name:<11} {fmt_lon(b.longitude):<20} H{b.house:<2} {motion:<2} "
            f"{b.element}/{b.modality}/{b.polarity} • {b.dignity} "
            f"• House domain: {HOUSE_DOMAINS.get(b.house, '—')}"
        )
    lines += ["", "HOUSE CUSPS"]
    for i,c in enumerate(chart.cusps,1): lines.append(f"House {i:>2}: {fmt_lon(c)}")
    lines += ["", "ASPECTS"]
    if not chart.aspects: lines.append("No configured aspects within orb.")
    else:
        for a in chart.aspects[:40]: lines.append(f"{a['a']} {a['aspect']} {a['b']}  • orb {a['orb']:.2f}°")
    lines += [
        "",
        "AUTHORITATIVE CALCULATION NOTES",
        "The planet/sign/degree, house number, retrograde state, and dignity above are calculated by Quarries.",
        "Do not substitute a different dignity or house meaning when interpreting this report.",
        "Traditional dignity rules used here:",
        "Sun: domicile Leo; exaltation Aries; detriment Aquarius; fall Libra.",
        "Moon: domicile Cancer; exaltation Taurus; detriment Capricorn; fall Scorpio.",
        "Mercury: domicile Gemini/Virgo; exaltation Virgo; detriment Sagittarius/Pisces; fall Pisces.",
        "Venus: domicile Taurus/Libra; exaltation Pisces; detriment Scorpio/Aries; fall Virgo.",
        "Mars: domicile Aries/Scorpio; exaltation Capricorn; detriment Libra/Taurus; fall Cancer.",
        "Jupiter: domicile Sagittarius/Pisces; exaltation Cancer; detriment Gemini/Virgo; fall Capricorn.",
        "Saturn: domicile Capricorn/Aquarius; exaltation Libra; detriment Cancer/Leo; fall Aries.",
        "",
        "HOUSE DOMAINS",
    ]
    for n in range(1, 13):
        lines.append(f"House {n}: {HOUSE_DOMAINS[n]}")
    lines += [
        "",
        "OBSERVATORY GUIDE",
        "Ascendant: zodiac degree rising on the eastern horizon.",
        "MC / Midheaven: zodiac degree on the local meridian near the chart top.",
        "House: one of twelve chart sectors; systems differ in how boundaries are calculated.",
        "Retrograde: apparent backward motion against the background stars.",
        "Dignity: traditional condition such as domicile, exaltation, detriment, fall, or peregrine.",
        "Aspect: angular relationship between two bodies.",
        "Orb: distance from the exact aspect angle; smaller means closer to exact.",
        "Applying / separating: moving toward or away from an exact aspect.",
        "",
        "Interpretive note: planetary positions and angles are calculated astronomical data. "
        "Astrological meanings are traditional symbolic interpretations.",
    ]
    return "\n".join(lines)
