#!/usr/bin/env python3
# -*- coding : utf-8 -*-

import os
import sys
import time
import queue
from threading import Event, Thread
from concurrent.futures import ThreadPoolExecutor

from gtts import gTTS
from tempfile import NamedTemporaryFile
import pygame
from pygame import mixer

from util import load_config

_msg_len = 0

CMD_HEAD = 'TTS> '

TMP_DIR = None

INDEX_ITER = 0

EXIT_EVENT = Event()

TARGET_FILE_NAME = None
TARGET_FILE_OFFSET = 0

VOICE_QUEUE = queue.Queue(maxsize=3)

MAIN_SPLITER = set([
    u'。', u'！', u'？', '\n',
    '.', '!', '?'
])

SUB_SPLITER = set([
    u'，', '》', ' ', 
    ',', '>'
])

def _state_print(msg, cmd=True):
    global _msg_len
    sys.stdout.write('\r%s' %(' '*_msg_len)) #clean the last msg use space.
    sys.stdout.write('\r%s' %msg)
    if cmd:
        sys.stdout.write('\n%s' %CMD_HEAD)
        _msg_len = len(CMD_HEAD) #update last msg len
    else:
        msg_len = len(msg) #update last msg len

def get_file_size(fn):
    info = os.stat(fn)
    return info.st_size

def exit_notify():
    EXIT_EVENT.set()
    try:
        VOICE_QUEUE.get_nowait()
    except queue.Empty:
        pass
    try:
        VOICE_QUEUE.put_nowait((None, None))
    except queue.Full:
        pass

def voice_to_file(text, lang='zh-cn'):
    tts = gTTS(text, lang)
    with NamedTemporaryFile(suffix='.mp3', dir=TMP_DIR, delete=False) as f:
        tts.write_to_fp(f)
        f.flush()
    return f.name
    
def play(fname, delete=True):
    interrupted = False
    with open(fname, 'rb') as fp:
        mixer.music.load(fp)
        mixer.music.play()
        while mixer.music.get_busy(): 
            time.sleep(0.5)
            #pygame.time.Clock().tick(10)
        mixer.music.stop()
    if delete:
        os.remove(fname)
    return interrupted
    
def split_text(text, max_len=50):
    max_len = min(len(text), max_len)
    for i, c in enumerate(reversed(text[:max_len])):
        if c in MAIN_SPLITER:
            split_index = max_len - i
            return text[:split_index], text[split_index:]
    
    for i, c in enumerate(reversed(text[:max_len])):
        if c in SUB_SPLITER:
            split_index = max_len - i
            return text[:split_index], text[split_index:]
    
    return '', text
    
def voice_work_entry():
    global TARGET_FILE_NAME
    global TARGET_FILE_OFFSET
    with open(TARGET_FILE_NAME, 'r', encoding='utf-8') as f:
        f.seek(TARGET_FILE_OFFSET)
        old_line = ''
        while not EXIT_EVENT.is_set():
            line = f.readline()
            if not line: break
            line = old_line + line
            while not EXIT_EVENT.is_set():
                new_line, line = split_text(line)
                if not new_line: break
                #print('text: %s' %new_line)
                
                if (new_line in MAIN_SPLITER
                        or new_line in SUB_SPLITER): 
                    VOICE_QUEUE.put((None, new_line))
                    continue
                
                fname = voice_to_file(new_line)
                
                VOICE_QUEUE.put((fname, new_line))
                
            old_line = line
    VOICE_QUEUE.put((None, 'END'))
    print('voice work exit.')
    #_state_print('%s kick end.\n' %TARGET_FILE_NAME)

def play_work_entry():
    global TARGET_FILE_OFFSET
    while not EXIT_EVENT.is_set():
        fname, text = VOICE_QUEUE.get()
        #print('play: %s' %fname)
        if EXIT_EVENT.is_set(): break
        if fname:
            _state_print('%s' %text)
            play(fname)
        elif text == 'END':
            _state_print('kick the end.')
            break
        TARGET_FILE_OFFSET += len(text.encode('utf-8'))# use bytes len
    print('play work exit.')
        
def start_threads():
    voice_thr = Thread(target=voice_work_entry, name='voice_work')
    voice_thr.start()
    play_thr = Thread(target=play_work_entry, name='play_work')
    play_thr.start()
    return voice_thr, play_thr

if __name__ == '__main__':
    config = load_config()
    TMP_DIR = config.get('tmp_dir', '.')
    mixer.init()
    
    TARGET_FILE_NAME = sys.argv[1]
    if len(sys.argv) > 2: 
        TARGET_FILE_OFFSET = int(sys.argv[2])
    
    thr_tuple = start_threads()
    
    while True:
        msg = input('TTS> ')
        if msg in ('exit', 'quit'):
            exit_notify()
            for thr in thr_tuple:
                thr.join()
            _state_print('%s %s/%sbytes\n' %(TARGET_FILE_NAME, TARGET_FILE_OFFSET,
                                get_file_size(TARGET_FILE_NAME)), False)
            break
        elif msg in ('start'):
            thr_tuple = start_threads()
    
    