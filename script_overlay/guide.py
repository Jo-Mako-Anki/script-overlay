# -*- coding: utf-8 -*-
"""Day-by-day calendar read from the GameFAQs walkthrough pages the user saved (Ctrl+S); nothing is downloaded.

guide(folder) -> [{'m': 'April', 'j': 'Tue 4/12', 'c': [['Class', ['text', ...]], ...]}, ...]
(taken from 3_Captures_sous_titres\\Sous-titres_script\\guide_jeu.py)
"""
import glob, html, os, re

MONTHS = ['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January',
          'February', 'March']


def _text(h):
    """Text of an <li>, keeping only the bold."""
    h = re.sub(r'<(/?)(b|strong)\b[^>]*>', lambda m: '\x01' if not m.group(1) else '\x02', h)
    t = html.unescape(re.sub(r'<[^>]+>', '', h)).strip()
    return html.escape(t).replace('\x01', '<b>').replace('\x02', '</b>')


def read_page(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    i = s.find('<h2>Walkthrough</h2>')
    if i < 0:
        return []
    s = s[i:]
    end = re.search(r'<div[^>]+class="[^"]*ftoc', s)  # bottom of the page (contents, comments)
    s = s[:end.start()] if end else s
    days = []; month = None
    for block in re.split(r'(?=<h[34]>)', s):
        m3 = re.match(r'<h3>(.*?)</h3>', block)
        if m3:
            month = html.unescape(re.sub(r'<[^>]+>', '', m3.group(1))).strip(); continue
        m4 = re.match(r'<h4>(.*?)</h4>', block, re.S)
        if not m4:
            continue
        day = html.unescape(re.sub(r'<[^>]+>', '', m4.group(1))).strip()
        slots = []
        for c in re.split(r'(?=<h5>)', block[m4.end():]):
            m5 = re.match(r'<h5>(.*?)</h5>', c, re.S)
            name = html.unescape(re.sub(r'<[^>]+>', '', m5.group(1))).strip() if m5 else ''
            items = [_text(li) for li in re.findall(r'<li>(.*?)</li>', c, re.S)]
            items = [x for x in items if x and 'Musical notes shown during stat gains' not in x
                     and not re.match(r'(Previous|Next):', x)]
            if items:
                slots.append([name, items])
        days.append({'m': month, 'j': day, 'c': slots})
    return days


def guide(folder):
    pages = [p for p in (read_page(f) for f in glob.glob(os.path.join(folder, '*.htm*'))) if p]
    pages.sort(key=lambda p: MONTHS.index(p[0]['m']) if p[0]['m'] in MONTHS else 99)
    return [x for p in pages for x in p]
