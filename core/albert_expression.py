"""Small, bounded expression descriptors for Albert's paper dot matrix.

These are contextual illustrations, never measurements or generated-image receipts.
The browser renders a fixed visual vocabulary without another inference request.
"""
import hashlib
import re

SCENES=('orbit','garden','waves','constellation','weave','pages','rain','paths')
TOPICS=(
    (r'\b(rain|weather|cloud|snow|storm)\b','rain','SKY'),
    (r'\b(book|books|reading|read|novel|poem|story|writing)\b','pages','READ'),
    (r'\b(music|song|audio|radio|listen|listening|sound)\b','waves','LISTEN'),
    (r'\b(garden|flower|flowers|plant|bloom|grow|nature)\b','garden','BLOOM'),
    (r'\b(space|stars|planet|orbit|moon|universe)\b','orbit','ORBIT'),
    (r'\b(fabric|home|project|projects|connect|network)\b','paths','CONNECT'),
    (r'\b(art|museum|painting|design|pattern|color)\b','weave','CREATE'),
)


def describe(prompt,answer):
    seed=hashlib.sha256((str(prompt)+'\n'+str(answer)).encode()).hexdigest()[:24]
    # Prefer the user's topic; the answer can supply context when the prompt is brief.
    for text in (str(prompt)[:2000].lower(),str(answer)[:2000].lower()):
        for pattern,scene,word in TOPICS:
            if re.search(pattern,text):return {'version':1,'seed':seed,'scene':scene,'word':word}
    return {'version':1,'seed':seed,'scene':SCENES[int(seed[:8],16)%len(SCENES)],'word':('IDEA','WONDER','HELLO','EXPLORE')[int(seed[8:12],16)%4]}
