from pathlib import Path
import importlib.util, io, sys

ROOT=Path(__file__).resolve().parents[1]

def load_renderer():
    p=ROOT/'look'/'look_renderer.py'
    spec=importlib.util.spec_from_file_location('look_renderer_760',p)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod

class TTYIn(io.StringIO):
    def isatty(self): return True
class TTYOut(io.StringIO):
    def isatty(self): return True

def test_iterm_uses_managed_kitty_protocol(monkeypatch):
    r=load_renderer()
    monkeypatch.setenv('TERM_PROGRAM','iTerm.app'); monkeypatch.delenv('KITTY_WINDOW_ID',raising=False)
    assert r._terminal_graphics_format()=='kitty'
    assert r._clear_native_preview()=='\x1b_Ga=d,d=A\x1b\\'

def test_each_interactive_frame_deletes_previous_graphic_before_fixed_right_portal(monkeypatch,tmp_path):
    r=load_renderer(); a=tmp_path/'a.png'; b=tmp_path/'b.png'; a.write_bytes(b'x'); b.write_bytes(b'x')
    seq=iter(['\x1b[B','\r'])
    monkeypatch.setattr(r,'read_key',lambda timeout=None: next(seq))
    monkeypatch.setattr(r,'_terminal_graphics_format',lambda:'kitty')
    monkeypatch.setattr(r,'_native_preview_block',lambda path,w,h:'PIXELS:'+path.name)
    monkeypatch.setattr(r.sys,'stdin',TTYIn()); out=TTYOut(); monkeypatch.setattr(r.sys,'stdout',out)
    def candidates(q): return [a,b]
    def rebuild(q,picked=None,w=None,marked=None): return [('>> ' if p==picked else '   ')+p.name for p in (a,b)]
    activated=[]
    r.pager(['LOOK'],20,120,rebuild=rebuild,filter_context=lambda q,w:['LOOK  ~/Desktop  0 dirs · 2 files','---'],
            candidates=candidates,on_activate=lambda p:activated.append(p),force_interactive=True,initial_query='png')
    screen=out.getvalue(); delete='\x1b_Ga=d,d=A\x1b\\'
    assert screen.count(delete)>=2
    assert '\x1b[3;73HPIXELS:a.png' in screen
    assert '\x1b[3;73HPIXELS:b.png' in screen
    assert activated==[b]

def test_pdf_uses_native_page_one_raster_in_same_portal(monkeypatch,tmp_path):
    r=load_renderer(); pdf=tmp_path/'sample.pdf'; pdf.write_bytes(b'%PDF-1.4')
    monkeypatch.setattr(r,'_PREVIEW_MODE','auto'); monkeypatch.setattr(r,'_terminal_graphics_format',lambda:'kitty')
    monkeypatch.setattr(r.shutil,'which',lambda name:'/usr/bin/'+name if name in {'chafa','pdftoppm'} else None)
    calls=[]
    class P:
        returncode=0; stdout='PIXELS\n'; stderr=''
    def run(args,**kwargs):
        calls.append(args)
        if args[0].endswith('pdftoppm'):
            Path(args[-1]+'.png').write_bytes(b'png')
            return type('Q',(),{'returncode':0,'stdout':'','stderr':''})()
        return P()
    monkeypatch.setattr(r.subprocess,'run',run)
    assert r._native_preview_block(pdf,60,20)=='PIXELS'
    assert any(str(c[0]).endswith('pdftoppm') for c in calls)
    chafa=next(c for c in calls if str(c[0]).endswith('chafa'))
    assert '--format=kitty' in chafa and '--relative' in chafa and 'on' in chafa
