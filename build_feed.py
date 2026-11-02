"""Build the Reality Drop Days calendar feed (drop-days.ics) from the page's SCHEDULE data.

Usage: python3 -I build_feed.py <index.html> <out.ics>

One event per streaming drop day at 9:00 AM Pacific, and one event per
Inside the NBA night from pregame start through the postgame. Each event's
UID is stable (show key + date), so when the page's schedule changes and
the feed is republished, subscribed calendars update events in place
instead of duplicating them. Re-run this every time SCHEDULE changes and
publish the output as drop-days.ics alongside the page.
"""
import datetime as dt
import json
import re
import sys

PRODID = "-//Reality Drop Days//Live feed//EN"
VTIMEZONE = """BEGIN:VTIMEZONE
TZID:America/Los_Angeles
BEGIN:DAYLIGHT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE"""


def esc(s):
    return (str(s).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        limit = 75 if not out else 74
        if len(cur) + len(b) > limit:
            out.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


def local(date_iso, minutes):
    d = dt.datetime.strptime(date_iso, "%Y-%m-%d") + dt.timedelta(minutes=minutes)
    return d.strftime("%Y%m%dT%H%M%S")


def tip_minutes(when):
    """'4:00 & 6:30 PM PT' -> [960, 1110]; '9:00 AM to 7:30 PM PT' -> [540, 1170]."""
    toks = re.findall(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", when)
    mins, pending = [], []
    for h, m, ap in toks:
        pending.append((int(h), int(m)))
        if ap:
            for hh, mm in pending:
                hh = hh % 12 + (12 if ap == "PM" else 0)
                mins.append(hh * 60 + mm)
            pending = []
    return mins


def svc_name(show):
    return show.get("service") or show.get("network") or ""


def streaming_event(show, ep, stamp):
    date = ep["available_date"]
    title, service = show["title"], svc_name(show)
    bits = [f"{title}, {show.get('season', '')}.".replace(", .", ".")]
    line = ep.get("label", "")
    if ep.get("title"):
        line += f": {ep['title']}"
    if line:
        bits.append(line + ".")
    bits.append(f"New episodes: {show['availability']['label']}.")
    if ep.get("note"):
        bits.append(ep["note"] + ".")
    if ep.get("projected"):
        bits.append(f"Expected date. {show.get('network', 'The network')} has not confirmed it yet.")
    return [
        "BEGIN:VEVENT",
        f"UID:{show['key']}-{date}@reality-drop-days",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID=America/Los_Angeles:{local(date, 9 * 60)}",
        f"DTEND;TZID=America/Los_Angeles:{local(date, 9 * 60 + 15)}",
        f"SUMMARY:{esc(f'{title} is on {service} today')}",
        f"DESCRIPTION:{esc(' '.join(bits))}",
        f"LOCATION:{esc(service)}",
        f"URL:{show.get('service_url', '')}",
        "TRANSP:TRANSPARENT",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{esc(f'{title} is on {service} today')}",
        "TRIGGER:PT0S",
        "END:VALARM",
        "END:VEVENT",
    ]


def live_event(show, ep, stamp):
    date = ep["available_date"]
    tips = tip_minutes(ep.get("when", ""))
    net = ep.get("network") or show.get("network", "")
    if not tips:
        tips = [17 * 60]
    lead = 30 if net == "ABC" else 60
    start = tips[0] - lead
    end = tips[-1] + 180
    title = show["title"]
    summary = f"{title} live on {net}"
    bits = [ep.get("label", "")]
    if ep.get("title"):
        bits[0] += f": {ep['title']}"
    bits[0] += "."
    bits.append(f"Tip-off {ep.get('when', '')}.")
    bits.append("Pregame starts an hour before the first tip on ESPN (30 minutes on ABC), and the full postgame runs after the last game.")
    if ep.get("note"):
        bits.append(ep["note"] + ".")
    return [
        "BEGIN:VEVENT",
        f"UID:{show['key']}-{date}@reality-drop-days",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID=America/Los_Angeles:{local(date, start)}",
        f"DTEND;TZID=America/Los_Angeles:{local(date, end)}",
        f"SUMMARY:{esc(summary)}",
        f"DESCRIPTION:{esc(' '.join(bits))}",
        f"LOCATION:{esc(net)}",
        f"URL:{show.get('service_url', '')}",
        "TRANSP:TRANSPARENT",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{esc(summary + ' now')}",
        "TRIGGER:PT0S",
        "END:VALARM",
        "END:VEVENT",
    ]


def build(schedule):
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH", "X-WR-CALNAME:Reality Drop Days", "X-WR-TIMEZONE:America/Los_Angeles",
        "X-WR-CALDESC:A reminder each morning a new episode is up to stream\\, and on every Inside the NBA night. Updates on its own when the schedule changes.",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H",
    ]
    lines += VTIMEZONE.split("\n")
    count = 0
    for show in schedule["shows"]:
        for ep in show.get("episodes", []):
            ev = live_event(show, ep, stamp) if (show.get("live") or ep.get("live")) else streaming_event(show, ep, stamp)
            lines += ev
            count += 1
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n", count


if __name__ == "__main__":
    html = open(sys.argv[1], encoding="utf-8").read()
    schedule = json.loads(re.search(r"var SCHEDULE = (\{.*?\});\n", html, re.S).group(1))
    ics, n = build(schedule)
    with open(sys.argv[2], "w", encoding="utf-8", newline="") as f:
        f.write(ics)
    print(f"{n} events, {len(ics.encode('utf-8'))} bytes")
