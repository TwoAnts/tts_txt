#!/usr/bin/env python3
# -*- coding : utf-8 -*-

import os
import sys

from gtts import gTTS
from tempfile import NamedTemporaryFile
import pygame
from pygame import mixer

from util import load_config

TMP_DIR = None

def voice_to_file(text, lang='zh-cn'):
    tts = gTTS(text, lang)
    with NamedTemporaryFile(suffix='.mp3', dir=TMP_DIR, delete=False) as f:
        tts.write_to_fp(f)
        f.flush()
    return f.name
    
def play(fname):
    with open(fname, 'rb') as fp:
        mixer.music.load(fp)
        mixer.music.play()
        while mixer.music.get_busy(): 
            pygame.time.Clock().tick(10)
        mixer.music.stop()
    os.remove(f.name)


if __name__ == '__main__':
    config = load_config()
    TMP_DIR = config.get('tmp_dir', '.')
    mixer.init()
    voice(sys.argv[1])