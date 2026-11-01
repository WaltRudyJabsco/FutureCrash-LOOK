"""Bounded punctuation pacing; source book text and bookmarks stay unchanged."""
import html
import json
from pathlib import Path
import re
import sys
import wave

# Added silence at 1x; browser speed scales the whole recording normally.
PROFILES={'voice':(0,0),'natural':(350,200),'relaxed':(650,350)}
BOUNDARY=re.compile(r'[.!?]+[”’"\')\]]*(?=\s|$)|—|(?<=\s)–(?=\s)|(?<=\s)-{1,2}(?=\s)|:(?![/\d])')
ABBREVIATIONS={'mr','mrs','ms','dr','prof','sr','jr','st','vs','etc','fig','no','vol','rev'}
MAX_SEGMENTS=128


def segments(text,profile):
    if profile not in PROFILES:raise ValueError('Choose voice, natural or relaxed pauses')
    sentence,clause=PROFILES[profile]
    if not sentence:return [(text,0)]
    result=[];start=0
    for match in BOUNDARY.finditer(text):
        mark=match.group();prefix=text[:match.end()].rstrip('”’"\') ]')
        if mark.startswith('.'):
            token=re.search(r'([\w.]+)\.$',prefix)
            if token and (token[1].casefold() in ABBREVIATIONS or len(token[1])==1 or re.fullmatch(r'(?:[A-Za-z]\.)+[A-Za-z]',token[1])):continue
        part=text[start:match.end()].strip()
        if not any(c.isalnum() for c in part):continue
        result.append((part,sentence if mark[0] in '.!?' else clause));start=match.end()
        # A pathological punctuation-heavy paragraph stays one bounded job.
        if len(result)>=MAX_SEGMENTS-1:break
    tail=text[start:].strip()
    if tail:result.append((tail,0))
    return result or [(text,0)]


def say_text(text,profile):
    return ' '.join(part.replace('[[','[ [').replace(']]','] ]')+(f' [[slnc {pause}]]' if pause else '') for part,pause in segments(text,profile))


def espeak_text(text,profile):
    return '<speak>'+''.join(html.escape(part)+(f'<break time="{pause}ms"/>' if pause else '')+' ' for part,pause in segments(text,profile))+'</speak>'


def piper_wave(model,parts,destination,voice_loader=None):
    # One model load per paragraph, not a new process/load at every sentence.
    if voice_loader is None:
        from piper import PiperVoice
        voice_loader=PiperVoice.load
    voice=voice_loader(model)
    with wave.open(str(destination),'wb') as output:
        params=None
        for text,pause in parts:
            for chunk in voice.synthesize(text.replace('[[','[ [').replace(']]','] ]')):
                current=(chunk.sample_rate,chunk.sample_width,chunk.sample_channels)
                if params is None:
                    params=current;output.setframerate(params[0]);output.setsampwidth(params[1]);output.setnchannels(params[2])
                if current!=params:raise ValueError('Narration audio format changed')
                output.writeframes(chunk.audio_int16_bytes)
            if params and pause:output.writeframes(bytes(((params[0]*pause+500)//1000)*params[1]*params[2]))
        if params is None:raise ValueError('No narration audio was generated')


if __name__=='__main__':
    model,source,destination=sys.argv[1:]
    piper_wave(model,json.loads(Path(source).read_text()),destination)
