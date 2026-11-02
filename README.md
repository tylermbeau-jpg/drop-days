# Drop Days calendar feed

A subscribable calendar for the Reality Drop Days tracker: a 9 AM reminder each morning a new episode of a followed show is up to stream, and an event for every Inside the NBA night from pregame through postgame.

Subscribe with this link:

```
https://raw.githubusercontent.com/tylermbeau-jpg/drop-days/main/drop-days.ics
```

- iPhone: Calendar app, then Calendars, Add Calendar, Add Subscription Calendar. Turn off Remove Alerts.
- Mac: Calendar, File, New Calendar Subscription.
- Google Calendar: Other calendars, plus, From URL.

## Updating

`drop-days.ics` is generated from the `SCHEDULE` data embedded in the Reality Drop Days page:

```
python3 build_feed.py index.html drop-days.ics
```

Every event has a stable ID (show plus date), so a regenerated feed updates subscribed calendars in place instead of adding duplicates. Commit the new file and subscribers pick it up on their next refresh.
