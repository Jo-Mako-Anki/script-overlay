# -*- coding: utf-8 -*-
"""Japanese OCR with Tesseract (a copy sits in the Tesseract folder next to the app, else an installed one) and the
tessdata_best Japanese model (in data\tessdata, downloaded once if missing)."""
import os, shutil, subprocess, urllib.request

import cv2
import numpy as np

from .paths import ROOT, data

URL_JPN = 'https://github.com/tesseract-ocr/tessdata_best/raw/main/jpn.traineddata'
TESSERACT_HELP = 'https://github.com/UB-Mannheim/tesseract/wiki'


def find_tesseract(settings):
    cands = [os.path.join(ROOT, 'Tesseract', 'tesseract.exe'),  # the copy shipped with the app
             settings.get('tesseract'), shutil.which('tesseract')]
    for v in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        b = os.environ.get(v)
        if b:
            cands += [os.path.join(b, 'Tesseract-OCR', 'tesseract.exe'),
                      os.path.join(b, 'Programs', 'Tesseract-OCR', 'tesseract.exe')]
    cands += [r'C:\Tesseract-OCR\tesseract.exe', os.path.expandvars(r'%USERPROFILE%\scoop\apps\tesseract\current\tesseract.exe')]
    try:  # the UB Mannheim installer writes its folder in the registry
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for key in (r'SOFTWARE\Tesseract-OCR', r'SOFTWARE\WOW6432Node\Tesseract-OCR'):
                try:
                    with winreg.OpenKey(root, key) as k:
                        cands.append(os.path.join(winreg.QueryValueEx(k, 'InstallDir')[0], 'tesseract.exe'))
                except OSError:
                    pass
    except ImportError:
        pass
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def tessdata_dir():
    return os.path.dirname(data('tessdata', 'jpn.traineddata'))


def has_model():
    p = os.path.join(tessdata_dir(), 'jpn.traineddata')
    return os.path.exists(p) and os.path.getsize(p) > 1_000_000


def download_model(progress=None):
    dest = os.path.join(tessdata_dir(), 'jpn.traineddata')
    def hook(n, bs, total):
        if progress:
            progress(n * bs, total)
    urllib.request.urlretrieve(URL_JPN, dest + '.part', hook)
    os.replace(dest + '.part', dest)


def prepare(img, extra=0):
    """Black text on white, scaled so that characters are ~40 px high (Tesseract reads best around there)."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h = g.shape[0]
    f = min(4.0, max(1.0, 220.0 / max(h, 1))) + 0.5 * extra  # a dialogue box holds ~2-4 lines
    if f != 1:
        g = cv2.resize(g, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    _, b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if (b > 0).mean() < 0.5:  # mostly dark: light text on a dark box
        b = 255 - b
    return cv2.copyMakeBorder(b, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)


class Tesseract:
    def __init__(self, exe):
        self.exe = exe
        self.env = dict(os.environ, OMP_THREAD_LIMIT='1')
        self.flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    def read(self, img, extra=0):
        ok, buf = cv2.imencode('.png', prepare(img, extra))
        r = subprocess.run([self.exe, 'stdin', 'stdout', '--tessdata-dir', tessdata_dir(), '-l', 'jpn', '--psm', '6'],
                           input=buf.tobytes(), capture_output=True, env=self.env, creationflags=self.flags)
        return r.stdout.decode('utf-8', 'replace').replace('\r', '').strip().replace('\n', ' / ')
