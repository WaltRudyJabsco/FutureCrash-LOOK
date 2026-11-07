"""Image inspection in the shared graphics runtime, independent of CLI Pillow."""
import json
from pathlib import Path
import subprocess
import sys

MAX_INPUT = 64 * 1024 * 1024
MAX_PIXELS = 100_000_000
PRINT_WIDTH = 2048


def process(path, *, output=None, limit=3*1024*1024):
    import saver
    python=saver.interpreter()
    if not python:raise ValueError('Image preview needs the shared graphics runtime: lk saver setup')
    result=subprocess.run([str(python),str(Path(__file__).resolve()),'--worker'],
        input=json.dumps(dict(path=str(path),output=str(output) if output else '',limit=limit)),text=True,capture_output=True,timeout=30)
    if result.returncode:raise ValueError(result.stdout.strip() or result.stderr.strip() or 'Image processing failed')
    return json.loads(result.stdout)


def worker(job):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImageReader
    path=Path(job['path'])
    if not 0<path.stat().st_size<=MAX_INPUT:raise ValueError('Clipboard image must be at most 64 MiB')
    QImageReader.setAllocationLimit(384)
    reader=QImageReader(str(path));size=reader.size()
    if size.width()*size.height()>MAX_PIXELS:raise ValueError('Image dimensions exceed the capture limit')
    image=reader.read()
    if image.isNull():raise ValueError('Image could not be decoded: '+reader.errorString())
    original=[image.width(),image.height()]
    if job.get('output'):
        image=image.scaled(PRINT_WIDTH,PRINT_WIDTH,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation) if max(original)>PRINT_WIDTH else image
        while True:
            if not image.save(job['output'],'PNG'):raise ValueError('Could not prepare image for printing')
            if Path(job['output']).stat().st_size<=job['limit']:break
            if min(image.width(),image.height())<64:raise ValueError('Image cannot fit the print transfer limit')
            image=image.scaled(max(1,int(image.width()*.8)),max(1,int(image.height()*.8)),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    thumb=image.scaled(48,18,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    shades='@%#*+=-:. ';rows=[]
    for y in range(thumb.height()):
        row=''
        for x in range(thumb.width()):
            color=thumb.pixelColor(x,y);alpha=color.alpha()/255
            light=(.299*color.red()+.587*color.green()+.114*color.blue())*alpha+255*(1-alpha)
            row+=shades[min(9,int(light*10/256))]
        rows.append(row)
    return dict(original=original,size=[image.width(),image.height()],preview='\n'.join(rows))


if __name__=='__main__':
    try:print(json.dumps(worker(json.loads(sys.stdin.read()))))
    except Exception as exc:print(str(exc));raise SystemExit(1)
