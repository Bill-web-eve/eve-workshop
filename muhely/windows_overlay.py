"""Click-through intel cards on Windows. Native objects live on the shell's UI thread.

Only placement is persisted; reports and character information stay in memory.
The model is independent of pythonnet so expiry and monitor handling can be tested
on every platform. WinForms/.NET imports are intentionally lazy.
"""
from __future__ import annotations

import ctypes
import json
import logging
import math
import os
from pathlib import Path
import time

LOG=logging.getLogger(__name__)


def number(value,low,high,*,integer=False):
    if type(value) not in (int,float) or not low<=value<=high or not math.isfinite(value) or (integer and int(value)!=value):
        raise ValueError('Invalid intel overlay value')
    return int(value)


class OverlayState:
    def __init__(self,folder,clock=time.time):
        self.path=Path(folder)/'windows-intel-overlay.json';self.clock=clock
        self.placements={};self.screen_id='';self.editing=False
        self.enabled=False;self.seconds=60;self.items=[]
        try:
            saved=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(saved,dict):return
            if isinstance(saved.get('screen_id'),str):self.screen_id=saved['screen_id'][:200]
            for ident,pos in saved.get('placements',{}).items():
                if isinstance(ident,str) and len(ident)<=200:self.placements[ident]=self.validate_placement(pos)
        except (OSError,ValueError,TypeError,AttributeError):pass

    @staticmethod
    def validate_placement(pos):
        if not isinstance(pos,dict):raise ValueError('Invalid overlay placement')
        return {key:number(pos.get(key),260 if key=='width' else 0,600 if key=='width' else 20000) for key in ('x','y','width')}

    def selected(self,screens):
        if not screens:raise ValueError('No display is available')
        return next((s for s in screens if s['id']==self.screen_id),next((s for s in screens if s.get('primary')),screens[0]))

    def placement(self,screen):
        return dict(self.placements.get(screen['id'],{'x':max(0,screen['width']-350),'y':80,'width':330}))

    def settings(self,screens):
        selected=self.selected(screens)
        return {'available':True,'screens':[{**{k:s[k] for k in ('id','name','width','height')},'placement':self.placement(s)} for s in screens],
                'screen_id':selected['id'],'placement':self.placement(selected),'editing':self.editing}

    def persist(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'screen_id':self.screen_id,'placements':self.placements}),encoding='utf-8')
        os.replace(temporary,self.path)

    def configure(self,options,screens):
        if not isinstance(options,dict) or set(options)-{'screen_id','x','y','width','editing'}:
            raise ValueError('Invalid overlay options')
        screen=self.selected(screens)
        if 'screen_id' in options:
            screen=next((s for s in screens if s['id']==options['screen_id']),None)
            if screen is None:raise ValueError('The selected display is no longer available')
        if 'editing' in options and type(options['editing']) is not bool:raise ValueError('Invalid overlay edit mode')
        pos=self.validate_placement({**self.placement(screen),**{k:options[k] for k in ('x','y','width') if k in options}})
        self.screen_id=screen['id'];self.placements[self.screen_id]=pos
        if 'editing' in options:self.editing=options['editing']
        self.persist()

    def dragged(self,left,top,width,screens):
        # Windows desktops can have negative coordinates. Store monitor-relative values.
        cx=left+width/2;cy=top+50
        screen=next((s for s in screens if s['left']<=cx<s['left']+s['width'] and s['top']<=cy<s['top']+s['height']),self.selected(screens))
        self.screen_id=screen['id']
        self.placements[self.screen_id]={'x':max(0,min(20000,left-screen['left'])),'y':max(0,min(20000,top-screen['top'])),'width':width}
        self.persist()

    def sync(self,data):
        if not isinstance(data,dict) or type(data.get('enabled')) is not bool or not isinstance(data.get('items'),list) or len(data['items'])>3000:
            raise ValueError('Invalid overlay reports')
        seconds=number(data.get('seconds'),1,3600,integer=True);items=[]
        for row in data['items']:
            if not isinstance(row,dict):raise ValueError('Invalid overlay report')
            for key in ('key','system','pilots','ships','character'):
                if not isinstance(row.get(key),str) or len(row[key])>2000:raise ValueError('Invalid overlay report text')
            when=row.get('when')
            if type(when) not in (int,float) or not -2**53<=when<=2**53 or not math.isfinite(when):raise ValueError('Invalid overlay report time')
            jumps=row.get('jumps')
            if jumps is not None:number(jumps,0,10000,integer=True)
            items.append({k:row.get(k) for k in ('key','system','pilots','ships','character','when','jumps')})
        self.enabled=data['enabled'];self.seconds=seconds;self.items=items if self.enabled else []

    def cards(self):
        now=self.clock();unique={}
        if self.enabled:
            for row in self.items:
                if not row['when']<=now<row['when']+self.seconds:continue
                old=unique.get(row['key'])
                if old is None or (row['jumps'] if row['jumps'] is not None else math.inf)<(old['jumps'] if old['jumps'] is not None else math.inf):unique[row['key']]=row
        return sorted(unique.values(),key=lambda r:(-r['when'],r['key']))[:5]

    def bounds(self,screen,height):
        pos=self.placement(screen);work=screen.get('work',(screen['left'],screen['top'],screen['width'],screen['height']))
        left,top,w,h=work;width=min(pos['width'],w);height=min(height,h)
        x=min(max(screen['left']+pos['x'],left),left+w-width)
        y=min(max(screen['top']+pos['y'],top),top+h-height)
        return int(x),int(y),int(width),int(height)


class NativeOverlay:
    """A small WinForms surface, with no WebView or browser security exceptions."""
    def __init__(self,folder,theme='dark',language='hu'):
        from System.Windows.Forms import Timer
        self.state=OverlayState(folder);self.theme=theme;self.language=language
        self.form=None;self._cards=[];self._signature=None;self.disposed=False;self.failure=None
        self._fonts=[];self._dragging=False
        from ctypes import wintypes
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        signatures={
            'GetWindowLongPtrW':([wintypes.HWND,ctypes.c_int],ctypes.c_ssize_t),
            'SetWindowLongPtrW':([wintypes.HWND,ctypes.c_int,ctypes.c_ssize_t],ctypes.c_ssize_t),
            'SetWindowPos':([wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT],wintypes.BOOL),
            'ShowWindow':([wintypes.HWND,ctypes.c_int],wintypes.BOOL),
            'IsWindowVisible':([wintypes.HWND],wintypes.BOOL),
            'ReleaseCapture':([],wintypes.BOOL),
            'SendMessageW':([wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM],ctypes.c_ssize_t),
        }
        for name,(args,result) in signatures.items():
            fn=getattr(self.user,name);fn.argtypes=args;fn.restype=result
        self.timer=Timer();self.timer.Interval=250;self.timer.Tick+=self._tick;self.timer.Start()

    @staticmethod
    def screens():
        from System.Windows.Forms import Screen
        return [{'id':str(s.DeviceName),'name':str(s.DeviceName),'width':s.Bounds.Width,'height':s.Bounds.Height,
                 'left':s.Bounds.Left,'top':s.Bounds.Top,'primary':bool(s.Primary),
                 'work':(s.WorkingArea.Left,s.WorkingArea.Top,s.WorkingArea.Width,s.WorkingArea.Height)} for s in Screen.AllScreens]

    def settings(self):
        return self.state.settings(self.screens())

    def configure(self,options):
        self.state.configure(options,self.screens());self.refresh();return self.settings()

    def sync(self,data):
        self.state.sync(data);self.refresh();return True

    def preferences(self,theme,language):
        self.theme=theme;self.language=language;self.refresh()

    def _ensure_form(self):
        if self.form is not None:return
        from System.Drawing import Color,Font,FontStyle
        from System.Windows.Forms import Form,FormBorderStyle,FormStartPosition,AutoScaleMode
        self.form=Form();self.form.Text='EVE Intel Overlay'
        self.form.FormBorderStyle=getattr(FormBorderStyle,'None');self.form.StartPosition=FormStartPosition.Manual
        self.form.AutoScaleMode=getattr(AutoScaleMode,'None');self.form.ShowInTaskbar=False;self.form.TopMost=True
        self.form.BackColor=Color.Magenta;self.form.TransparencyKey=Color.Magenta
        self._fonts=[Font('Segoe UI',10,FontStyle.Bold),Font('Segoe UI',9,FontStyle.Regular),Font('Segoe UI',8,FontStyle.Regular)]
        self.form.Paint+=self._on_paint;self.form.MouseDown+=self._mouse_down
        self.form.HandleCreated+=lambda *_:self._styles()
        self._styles()

    def _styles(self):
        if self.form is None:return
        hwnd=self.form.Handle.ToInt64();style=self.user.GetWindowLongPtrW(hwnd,-20)
        # Layered windows with WS_EX_TRANSPARENT pass mouse events to windows below.
        style|=0x00080000|0x08000000|0x00000080  # LAYERED, NOACTIVATE, TOOLWINDOW
        style=style&~0x20 if self.state.editing else style|0x20
        ctypes.set_last_error(0)
        if not self.user.SetWindowLongPtrW(hwnd,-20,style) and ctypes.get_last_error():raise ctypes.WinError(ctypes.get_last_error())

    def _tick(self,*_):
        # Do not move the surface underneath an active Windows drag loop.
        try:
            if not self._dragging:self.refresh()
        except Exception as error:self._failed(error)

    def _failed(self,error):
        self.failure=error;LOG.exception('Windows intel overlay failed')
        self.timer.Stop()
        if self.form is not None:self.user.ShowWindow(self.form.Handle.ToInt64(),0)

    def _on_paint(self,sender,event):
        try:self._paint(sender,event)
        except Exception as error:self._failed(error)

    def refresh(self):
        if self.disposed:return
        if self.failure is not None:raise RuntimeError('Windows intel overlay failed; see launcher.log') from self.failure
        cards=self.state.cards()
        if not self.state.editing and not cards:
            if self.form is not None:self.user.ShowWindow(self.form.Handle.ToInt64(),0)
            self._signature=None;self._cards=[];return
        screens=self.screens();screen=self.state.selected(screens)
        height=112 if self.state.editing else sum((86 if r['ships'] else 68)+6 for r in cards)-6
        bounds=self.state.bounds(screen,height)
        signature=(self.state.editing,self.theme,self.language,bounds,cards)
        self._ensure_form();self._cards=cards
        if signature!=self._signature:
            self._styles();self._signature=signature
            # SWP_NOACTIVATE | SWP_NOOWNERZORDER; HWND_TOPMOST, not foreground activation.
            if not self.user.SetWindowPos(self.form.Handle.ToInt64(),-1,*bounds,0x10|0x200):raise ctypes.WinError(ctypes.get_last_error())
            self.form.Invalidate()
        if not self.user.IsWindowVisible(self.form.Handle.ToInt64()):self.user.ShowWindow(self.form.Handle.ToInt64(),4)  # SW_SHOWNOACTIVATE

    def _paint(self,_sender,event):
        from System.Drawing import Color,Rectangle,SolidBrush,Pen
        from System.Windows.Forms import TextRenderer,TextFormatFlags
        g=event.Graphics;width=self.form.ClientSize.Width;english=self.language=='en';light=self.theme=='light'
        paper=Color.FromArgb(247,249,250) if light else Color.FromArgb(19,39,52)
        ink=Color.FromArgb(31,51,65) if light else Color.FromArgb(225,235,242)
        muted=Color.FromArgb(80,105,120) if light else Color.FromArgb(170,190,202)
        accent=Color.FromArgb(18,114,141) if light else Color.FromArgb(125,205,225)
        flags=TextFormatFlags.NoPrefix|TextFormatFlags.EndEllipsis|TextFormatFlags.SingleLine|TextFormatFlags.NoPadding
        def text(value,x,y,w,font=1,color=None):
            TextRenderer.DrawText(g,value,self._fonts[font],Rectangle(x,y,max(1,w),20),color or ink,flags)
        def box(y,height):
            brush=SolidBrush(paper);pen=Pen(Color.FromArgb(225,133,114))
            try:g.FillRectangle(brush,0,y,width,height);g.DrawRectangle(pen,0,y,width-1,height-1)
            finally:brush.Dispose();pen.Dispose()
        if self.state.editing:
            box(0,112)
            text('Intel overlay · positioning' if english else 'Inteljelző · elhelyezés',10,10,width-87,0)
            text('Done' if english else 'Kész',width-65,10,58,0,accent)
            text('Drag this panel to any monitor.' if english else 'Húzd az ablakot a kívánt monitorra.',10,44,width-20,1,accent)
            text('Done saves the position.' if english else 'A Kész elmenti a pozíciót.',10,76,width-20,2,muted)
            return
        y=0
        for row in self._cards:
            height=86 if row['ships'] else 68;box(y,height)
            text(row['system'],10,y+6,width-70,0)
            text('–' if row['jumps'] is None else str(row['jumps'])+'j',width-48,y+7,40,1,muted)
            text(row['pilots'],10,y+27,width-20,0,accent)
            if row['ships']:text(row['ships'],10,y+46,width-20)
            text(row['character'],10,y+height-19,width-20,2,muted);y+=height+6

    def _mouse_down(self,_sender,event):
        from System.Windows.Forms import MouseButtons
        if not self.state.editing or event.Button!=MouseButtons.Left:return
        if event.X>=self.form.Width-75 and event.Y<36:
            self.state.editing=False;self.refresh();return
        self._dragging=True
        try:
            self.user.ReleaseCapture();self.user.SendMessageW(self.form.Handle.ToInt64(),0xA1,2,0)
            self.state.dragged(self.form.Left,self.form.Top,self.form.Width,self.screens())
        finally:self._dragging=False
        self.refresh()

    def dispose(self):
        if self.disposed:return
        self.disposed=True;self.timer.Stop();self.timer.Dispose()
        if self.form is not None:self.form.Dispose()
        for font in self._fonts:font.Dispose()
