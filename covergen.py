from datetime import datetime, date, time, timedelta
from pytz import timezone
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw
from icalendar import cal
import errno
import requests
import os
import sys

MONTHS = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli',
          'augustus', 'september', 'oktober', 'november', 'december']


def build_events(month):
    now = datetime.now()

    print('importing calendar...', file=sys.stderr)
    ical = requests.get('https://calendar.google.com/calendar/ical/'
                        'via.uvastudent.org_rdn1ffk47v0gmla0oni69egmhk%40'
                        'group.calendar.google.com/public/basic.ics').text
    calendar = cal.Calendar().from_ical(ical)

    print('processing events...', file=sys.stderr)
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

        if (ev['dtstart'].month >= month or ev['dtend'].month >= month) and \
           (datestart >= now or dateend >= now):
            events.append(ev)

    events.sort(key=lambda x: x['dtstart'].timetuple())
    return events


def generate_cover_img():
    now = datetime.now()
    events = build_events(now.month)[:9]

    print('generating image...', file=sys.stderr)

    img = Image.open('resources/cover_template.png')
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype('resources/via-consistent-font.otf', 20)

    # Draw the title
    month = MONTHS[now.month - 1]
    title = f'Activiteitenagenda {month} {now.year}'
    title_w, title_h = font.getsize(title)
    title_x, title_y = (img.width - title_w) // 2, 110
    draw.text((title_x, title_y), title, (255, 255, 255), font=font)

    current_y = title_y + title_h + 6
    for event in events:
        if event['dtstart'].month != now.month:
            continue

        is_date = type(event['dtstart']) is date \
            or type(event['dtend']) is date

        if is_date:
            event['dtend'] -= timedelta(days=1)

        if event['dtstart'].day == event['dtend'].day \
           or (not is_date and event['dtend'].hour < 6):
            draw.text((10, current_y), event['dtstart'].strftime('%d'),
                      (255, 255, 255), font=font)
            if not is_date:
                draw.text((70, current_y), event['dtstart'].strftime('%H:%M'),
                          (255, 255, 255), font=font)
        else:
            draw.text((10, current_y), event['dtstart'].strftime('%d') +
                      ' t/m ' + event['dtend'].strftime('%d'), font=font)

        draw.text((160, current_y), event['title'], (255, 255, 255), font=font)
        current_y += title_h

    more = 'meer informatie op svia.nl'
    more_w, more_h = font.getsize(more)
    more_x, more_y = img.width - title_w, img.height - title_h - 110
    draw.text((more_x, more_y), more, (255, 255, 255), font=font)

    print('writing image...', file=sys.stderr)
    with BytesIO() as output:
        img.save(output, format='JPEG', quality=95, optimize=True,
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

    filename = datetime.now().strftime('via_fbcover_%y%M%d%H%M%S.jpg')
    path = os.path.join('output', filename)
    with open(path, 'wb') as image_file:
        image_file.write(cover)

    print(file=sys.stderr)
    print(path)


if __name__ == '__main__':
    main()
