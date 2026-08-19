from datetime import datetime
from zoneinfo import ZoneInfo
from quarries.observatory import calculate_chart, format_chart

def test_observatory_chart_core():
    dt=datetime(2026,8,18,21,0,tzinfo=ZoneInfo("America/New_York"))
    c=calculate_chart(local_dt=dt,latitude=33.7490,longitude=-84.3880,timezone_name="America/New_York")
    names={b.name for b in c.bodies}
    assert {"Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","True Node","South Node"} <= names
    assert len(c.cusps)==12
    assert 0 <= c.ascendant < 360
    assert c.sunrise is not None and c.sunset is not None
    assert 0 <= c.moon_illumination <= 100
    assert "PLANETS / POINTS" in format_chart(c)

def test_sidereal_whole_sign():
    dt=datetime(2026,8,18,21,0,tzinfo=ZoneInfo("America/New_York"))
    c=calculate_chart(local_dt=dt,latitude=33.7490,longitude=-84.3880,timezone_name="America/New_York",zodiac_mode="Sidereal",sidereal_mode="Lahiri",house_system="Whole Sign")
    assert c.zodiac_mode=="Sidereal"
    assert c.house_system=="Whole Sign"
