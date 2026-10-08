"""Date selection for location-local daily forecast receipts."""
from datetime import date, timedelta
import re


def selection(request,forecast):
    text=str(request or '').casefold()
    if not forecast: return []
    today=date.fromisoformat(forecast[0]['date'])
    start=today+timedelta(days=1 if 'tomorrow' in text else 0)
    count=5 if 'forecast' in text and not re.search(r'\b(today|tonight|tomorrow)\b',text) else 1
    match=re.search(r'\b([1-7]|five|seven)[ -]days?\b',text)
    if match: count={'five':5,'seven':7}.get(match.group(1),int(match.group(1)) if match.group(1).isdigit() else 1)
    elif 'weekend' in text:
        start=today+timedelta(days=(5-today.weekday())%7)
        if today.weekday()==6: start=today
        count=1 if today.weekday()==6 else 2
    elif 'week' in text:
        count=7
        if 'next week' in text: start=today+timedelta(days=7-today.weekday())
    dates={(start+timedelta(days=n)).isoformat() for n in range(count)}
    return [row for row in forecast if row.get('date') in dates]


def requested(request):
    return bool(re.search(r'\b(tomorrow|weekend|week|[1-7][ -]days?|five[ -]days?|seven[ -]days?|forecast)\b',str(request or '').casefold()))


def format_forecast(row,condition):
    selected=selection(row.get('requested',''),row.get('forecast') or [])
    place=row.get('location') or {}
    label=', '.join(str(value) for value in (place.get('name'),place.get('admin1') or place.get('region')) if value)
    lines=[f"{label} · forecast · {row.get('timezone') or place.get('timezone') or 'location-local dates'}"]
    if not selected: return lines[0]+'\nThe requested dates are not available in this forecast.'
    for day in selected:
        stamp=date.fromisoformat(day['date']).strftime('%a %Y-%m-%d')
        high=day.get('high_f'); low=day.get('low_f'); rain=day.get('precip_probability_pct')
        temps=f'High {high:.1f}°F · low {low:.1f}°F' if high is not None and low is not None else 'high/low unavailable'
        precip=f' · precipitation {rain:.0f}%' if rain is not None else ''
        lines.append(f"{stamp} · {condition(day.get('weather_code')) or 'conditions unavailable'} · {temps}{precip}")
    return '\n'.join(lines)
