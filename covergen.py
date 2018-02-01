#!/usr/bin/env python3
from datetime import datetime, date, time, timedelta
from pytz import timezone
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw
from icalendar import cal
import locale
import errno
import requests
import os
import sys

locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')
MONTHS = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli',
          'augustus', 'september', 'oktober', 'november', 'december']


def build_events(month):
    now = datetime.now()

    ical = requests.get('https://calendar.google.com/calendar/ical/'
                        'via.uvastudent.org_rdn1ffk47v0gmla0oni69egmhk%40'
                        'group.calendar.google.com/public/basic.ics').text
    calendar = cal.Calendar().from_ical(ical)

    events = []
    for event in calendar.walk('VEVENT'):
        ev = {
            'dtstart': event['DTSTART'].dt,
            'dtend': event['DTEND'].dt,
            'title': str(event['SUMMARY'])
        }
        tz = timezone('Europe/Amsterdam')
        if type(ev['dtstart']) is datetime:
            ev['dtstart'] = ev['dtstart'].astimezone(tz)
        if type(ev['dtend']) is datetime:
            ev['dtend'] = ev['dtend'].astimezone(tz)

        datestart = datetime.combine(ev['dtstart'], time.max)
        dateend = datetime.combine(ev['dtend'], time.max)

        if 'vergadering' in ev['title'].lower() or \
           ev['title'].lower() == 'kelder-bestelling' or \
           ev['title'].lower() == 'tentamenweek':
            continue

        if (ev['dtstart'].month >= month or ev['dtend'].month >= month) and (datestart >= now or dateend >= now) and \
           ev['dtstart'].month < month % 12 + 1:
            events.append(ev)

    events.sort(key=lambda x: x['dtstart'].timetuple())
    return events


FONT_SIZE = 18

EVENT_X_DATE_ICON = 100
EVENT_X_DATE_TEXT = 122
EVENT_X_NAME      = 275
EVENT_X_TIME_ICON = 812
EVENT_X_TIME_TEXT = 835

EVENT_HEIGHT = 27

def generate_cover_img():
    now = datetime.now()

    print('importing calendar...', file=sys.stderr)
    events = build_events(now.month)

    print('\n'.join('{}: {}'.format(e['dtstart'], e['title']) for e in events), file=sys.stderr)

    print('generating image...', file=sys.stderr)

    img = Image.open('resources/cover_template.png').convert('RGB')
    draw = ImageDraw.Draw(img)

    font_awesome = ImageFont.truetype('resources/font-awesome.otf',          FONT_SIZE)
    font_regular = ImageFont.truetype('resources/SourceSansPro-Regular.ttf', FONT_SIZE)
    font_bold    = ImageFont.truetype('resources/SourceSansPro-Bold.ttf',    FONT_SIZE)

    # Draw the title
    current_y = 185
    for i, event in enumerate(events):
        if event['dtstart'].month != now.month:
            continue

        if len(events) > 9 and i == 8:
            text = '+{} activiteiten in deze maand'.format(len(events) - i)
            w, _ = draw.textsize(text)
            draw.text(((860 - w) / 2 + 50, current_y + 5), text, (255, 255, 255), font=font_bold)
            break

        is_date = type(event['dtstart']) is date or type(event['dtend']) is date
        if is_date:
            event['dtend'] -= timedelta(days=1)

        # Draw the date
        draw.text((EVENT_X_DATE_ICON, current_y), '\uf274', (255, 255, 255), font=font_awesome)
        if event['dtstart'].day == event['dtend'].day:
            date_string = event['dtstart'].strftime('%-d %B')
        else:
            date_string = '{} \u2013 {} {}'.format(event['dtstart'].strftime('%-d'), event['dtend'].strftime('%-d'),
                                                   event['dtstart'].strftime('%B'))
        draw.text((EVENT_X_DATE_TEXT, current_y - 3), date_string, font=font_bold)

        # Draw the event name
        draw.text((EVENT_X_NAME, current_y - 3), event['title'], (255, 255, 255), font=font_regular)

        # Draw the time, if available
        if event['dtstart'].day == event['dtend'].day and not is_date:
            draw.text((EVENT_X_TIME_ICON, current_y), '\uf017', (255, 255, 255), font=font_awesome)
            draw.text((EVENT_X_TIME_TEXT, current_y - 3), event['dtstart'].strftime('%H:%M'),
                      (255, 255, 255), font=font_bold)

        current_y += EVENT_HEIGHT

    print('writing image...', file=sys.stderr)
    with BytesIO() as output:
        img.save(output, format='JPEG', quality=99, optimize=True,
                 subsampling='4:4:4')
        return output.getvalue()


def create_folder(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def main():
    cover = generate_cover_img()

    create_folder('output')

    filename = datetime.now().strftime('via_fbcover_%y%m%d%H%M%S.jpg')
    path = os.path.join('output', filename)
    with open(path, 'wb') as image_file:
        image_file.write(cover)

    print(file=sys.stderr)
    print(path)


if __name__ == '__main__':
    main()
