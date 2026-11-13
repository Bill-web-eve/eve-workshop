"""Windows EVE previews using DWM thumbnails; no game memory or input injection.

The portable state is testable without Windows. Native objects stay on the STA;
only the low-level shortcut hook has a dedicated message-loop thread. Modifier
masks match the shared UI (Control=4096, Alt=2048, Win=256, Shift=512).
"""
from __future__ import annotations
import ctypes
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import queue
import threading
import time

LOG=logging.getLogger(__name__)
KINDS=('cargo_full','crystal_broken','rock_depleted','module_stopped')
MODIFIERS=4096|2048|256|512


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise ValueError('Invalid preview value')
    return value


def shortcut(value):
    if not isinstance(value,dict) or set(value)!={'code','modifiers'}:raise ValueError('Invalid shortcut')
    code=integer(value['code'],8,254);mods=integer(value['modifiers'],0,MODIFIERS)
    if mods&~MODIFIERS or code in {9,16,17,18,20,91,92,160,161,162,163,164,165}:raise ValueError('Unsupported shortcut')
    return {'code':code,'modifiers':mods}


class PreviewState:
    def __init__(self,folder,clock=time.time):
        self.path=Path(folder)/'windows-eve-preview.json';self.clock=clock
        self.enabled=False;self.editing=False;self.only_eve=True;self.fps=5
        self.next_key={'code':34,'modifiers':6144};self.previous_key={'code':33,'modifiers':6144}
        self.slots=[];self.sources={};self.mining={};self.capturing_key=False
        self.shortcut_count=0;self.error='';self.hotkeys_active=False
        try:
            saved=json.loads(self.path.read_text(encoding='utf-8'))
            self.configure(saved,persist=False)
        except (OSError,ValueError,TypeError,KeyError):pass

    def persist(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        data={k:getattr(self,k) for k in ('enabled','only_eve','fps','next_key','previous_key','slots')}
        temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(data),encoding='utf-8');os.replace(temp,self.path)

    @staticmethod
    def slot(row):
        if not isinstance(row,dict) or set(row)-{'key','title','label','enabled','width','screen','x','y'}:raise ValueError('Invalid preview window')
        for key,limit in [('key',200),('title',250),('label',80),('screen',200)]:
            if not isinstance(row.get(key,''),str) or len(row.get(key,''))>limit or any(ord(c)<32 for c in row.get(key,'')):raise ValueError('Invalid preview label')
        if not row.get('key') or type(row.get('enabled')) is not bool:raise ValueError('Invalid preview window')
        return {'key':row['key'],'title':row.get('title',''),'label':row.get('label',''),'enabled':row['enabled'],'width':integer(row.get('width'),100,900),
                'screen':row.get('screen',''),'x':integer(row.get('x',20),0,20000),'y':integer(row.get('y',20),0,20000)}

    def configure(self,options,persist=True):
        if not isinstance(options,dict) or set(options)-{'enabled','editing','only_eve','fps','next_key','previous_key','slots'}:raise ValueError('Invalid preview settings')
        values={k:getattr(self,k) for k in ('enabled','editing','only_eve','fps','next_key','previous_key','slots')}
        for key in ('enabled','editing','only_eve'):
            if key in options:
                if type(options[key]) is not bool:raise ValueError('Invalid preview switch')
                values[key]=options[key]
        if 'fps' in options:values['fps']=integer(options['fps'],1,10)
        for key in ('next_key','previous_key'):
            if key in options:values[key]=shortcut(options[key])
        if values['next_key']==values['previous_key']:raise ValueError('Previous and next shortcuts must differ')
        if 'slots' in options:
            if not isinstance(options['slots'],list) or len(options['slots'])>100:raise ValueError('Invalid preview window list')
            old={s['key']:s for s in self.slots}
            values['slots']=[self.slot({**old.get(s.get('key'),{}),**s}) if isinstance(s,dict) else self.slot(s) for s in options['slots']]
            if len({s['key'] for s in values['slots']})!=len(values['slots']):raise ValueError('Duplicate preview window')
            if persist and set(old)!=set(s['key'] for s in values['slots']):raise ValueError('Window list changed; refresh and try again')
        if not values['enabled']:values['editing']=False
        # Native tile callbacks retain these row objects. Validate everything
        # first, then update existing rows in place so dragging after a width,
        # label or order save writes into the live persisted configuration.
        if 'slots' in options:
            previous={row['key']:row for row in self.slots}
            rows=[]
            for row in values['slots']:
                current=previous.get(row['key'])
                if current is not None:current.update(row);rows.append(current)
                else:rows.append(row)
            values['slots']=rows
        for key,value in values.items():setattr(self,key,value)
        if persist:self.persist()

    def reconcile(self,sources):
        self.sources={r['key']:dict(r) for r in sources}
        known={s['key'] for s in self.slots};changed=False
        for r in sources:
            if r['key'] not in known:
                self.slots.append(self.slot({'key':r['key'],'title':r['title'],'label':'','width':260,'enabled':True,'y':min(20000,20+len(self.slots)*175)}));changed=True
        if changed:self.persist()

    def candidates(self):return [s for s in self.slots if s['enabled'] and s['key'] in self.sources]

    def next_slot(self,current,direction):
        integer(direction,-1,1)
        if not direction:raise ValueError('Invalid direction')
        rows=self.candidates()
        if not rows:return None
        index=next((i for i,r in enumerate(rows) if r['key']==current),-1 if direction==1 else 0)
        return rows[(index+direction)%len(rows)]

    def match(self,code,mods,eve_foreground):
        if not self.enabled or self.editing or self.capturing_key:return 0
        if not self.candidates():return 0
        if not eve_foreground and mods&~512==0:return 0
        for name,direction in [('next_key',1),('previous_key',-1)]:
            if getattr(self,name)=={'code':code,'modifiers':mods}:return direction
        return 0

    def sync_mining(self,data):
        if not isinstance(data,dict) or type(data.get('enabled')) is not bool or not isinstance(data.get('characters'),list) or len(data['characters'])>500:raise ValueError('Invalid mining data')
        rows={};now=self.clock()
        for row in data['characters']:
            if not isinstance(row,dict) or not isinstance(row.get('name'),str) or not 0<len(row['name'])<=200 or not isinstance(row.get('alerts'),list) or len(row['alerts'])>4:raise ValueError('Invalid mining character')
            alerts=[]
            for alert in row['alerts']:
                if not isinstance(alert,dict) or alert.get('kind') not in KINDS or not isinstance(alert.get('id'),str) or len(alert['id'])>100:raise ValueError('Invalid mining alert')
                safe={'kind':alert['kind'],'id':alert['id']}
                for key in ('module','crystal'):
                    value=alert.get(key,'')
                    if not isinstance(value,str) or len(value)>250:raise ValueError('Invalid mining detail')
                    safe[key]=value
                at=alert.get('at')
                if at is not None and (type(at) not in (float,int) or not math.isfinite(at) or not 0<=at<=now+2):raise ValueError('Invalid mining event time')
                safe['at']=at;alerts.append(safe)
            when=row.get('last_damage')
            if when is not None and (type(when) not in (float,int) or not math.isfinite(when) or not 0<=when<=now+2):raise ValueError('Invalid damage time')
            rows[row['name'].casefold()]={'alerts':alerts,'last_damage':when}
        self.mining=rows if data['enabled'] else {}

    def alerts(self,key):
        source=self.sources.get(key,{})
        return self.mining.get(source.get('title','').removeprefix('EVE - ').strip().casefold(),{'alerts':[],'last_damage':None})

    def flashing(self,key):
        when=self.alerts(key).get('last_damage');now=self.clock()
        return when is not None and 0<=now-when<10 and now%1<.5

    def place(self,slot,left,top,width,screens):
        screen=next((s for s in screens if s['left']<=left+width/2<s['left']+s['width'] and s['top']<=top+12<s['top']+s['height']),screens[0])
        slot.update(screen=screen['id'],x=max(0,min(20000,int(left-screen['left']))),y=max(0,min(20000,int(top-screen['top']))),width=max(100,min(900,int(width))))
        self.persist()

    def bounds(self,slot,screens,ratio):
        screen=next((s for s in screens if s['id']==slot['screen']),screens[0]);x,y,w,h=screen['work']
        width=min(slot['width'],w);height=min(round(width/max(.2,ratio))+24,h)
        return int(min(max(x,screen['left']+slot['x']),x+w-width)),int(min(max(y,screen['top']+slot['y']),y+h-height)),int(width),int(height)


class Win32:
    """Explicit pointer-sized signatures; Windows x64 only."""
    def __init__(self):
        from ctypes import wintypes as W
        self.W=W;self.user=ctypes.WinDLL('user32',use_last_error=True);self.kernel=ctypes.WinDLL('kernel32',use_last_error=True);self.dwm=ctypes.WinDLL('dwmapi',use_last_error=True)
        self.enum_proc=ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
        self.hook_proc=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,W.WPARAM,W.LPARAM)
        class Keyboard(ctypes.Structure):_fields_=[('vkCode',W.DWORD),('scanCode',W.DWORD),('flags',W.DWORD),('time',W.DWORD),('extra',ctypes.c_size_t)]
        self.Keyboard=Keyboard
        class Props(ctypes.Structure):_fields_=[('flags',W.DWORD),('destination',W.RECT),('source',W.RECT),('opacity',ctypes.c_ubyte),('visible',W.BOOL),('client',W.BOOL)]
        self.Props=Props
        signatures={
            'EnumWindows':([self.enum_proc,W.LPARAM],W.BOOL),'GetWindowTextLengthW':([W.HWND],ctypes.c_int),
            'GetWindowTextW':([W.HWND,W.LPWSTR,ctypes.c_int],ctypes.c_int),'IsWindowVisible':([W.HWND],W.BOOL),
            'IsWindow':([W.HWND],W.BOOL),'IsIconic':([W.HWND],W.BOOL),'GetForegroundWindow':([],W.HWND),
            'GetWindowThreadProcessId':([W.HWND,ctypes.POINTER(W.DWORD)],W.DWORD),
            'SetForegroundWindow':([W.HWND],W.BOOL),'ShowWindow':([W.HWND,ctypes.c_int],W.BOOL),
            'GetWindowLongPtrW':([W.HWND,ctypes.c_int],ctypes.c_ssize_t),'SetWindowLongPtrW':([W.HWND,ctypes.c_int,ctypes.c_ssize_t],ctypes.c_ssize_t),
            'SetWindowPos':([W.HWND,W.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,W.UINT],W.BOOL),
            'ReleaseCapture':([],W.BOOL),'SendMessageW':([W.HWND,W.UINT,W.WPARAM,W.LPARAM],ctypes.c_ssize_t),
            'SetWindowsHookExW':([ctypes.c_int,self.hook_proc,W.HINSTANCE,W.DWORD],W.HHOOK),
            'CallNextHookEx':([W.HHOOK,ctypes.c_int,W.WPARAM,W.LPARAM],ctypes.c_ssize_t),'UnhookWindowsHookEx':([W.HHOOK],W.BOOL),
            'GetMessageW':([ctypes.POINTER(W.MSG),W.HWND,W.UINT,W.UINT],W.BOOL),
            'PeekMessageW':([ctypes.POINTER(W.MSG),W.HWND,W.UINT,W.UINT,W.UINT],W.BOOL),
            'PostThreadMessageW':([W.DWORD,W.UINT,W.WPARAM,W.LPARAM],W.BOOL),'GetAsyncKeyState':([ctypes.c_int],ctypes.c_short),
            'RegisterHotKey':([W.HWND,ctypes.c_int,W.UINT,W.UINT],W.BOOL),'UnregisterHotKey':([W.HWND,ctypes.c_int],W.BOOL),
        }
        for name,(args,result) in signatures.items():fn=getattr(self.user,name);fn.argtypes=args;fn.restype=result
        for name,args,result in [('OpenProcess',[W.DWORD,W.BOOL,W.DWORD],W.HANDLE),('CloseHandle',[W.HANDLE],W.BOOL),('QueryFullProcessImageNameW',[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)],W.BOOL),('GetModuleHandleW',[W.LPCWSTR],W.HMODULE),('GetCurrentThreadId',[],W.DWORD)]:
            fn=getattr(self.kernel,name);fn.argtypes=args;fn.restype=result
        for name,args in [('DwmRegisterThumbnail',[W.HWND,W.HWND,ctypes.POINTER(W.HANDLE)]),('DwmUnregisterThumbnail',[W.HANDLE]),('DwmQueryThumbnailSourceSize',[W.HANDLE,ctypes.POINTER(W.SIZE)]),('DwmUpdateThumbnailProperties',[W.HANDLE,ctypes.POINTER(Props)])]:
            fn=getattr(self.dwm,name);fn.argtypes=args;fn.restype=ctypes.c_long

    def discover(self):
        found=[]
        @self.enum_proc
        def visit(hwnd,_):
            if not self.user.IsWindowVisible(hwnd):return True
            size=self.user.GetWindowTextLengthW(hwnd)
            if not 6<size<250:return True
            title=ctypes.create_unicode_buffer(size+1);self.user.GetWindowTextW(hwnd,title,size+1)
            if not title.value.startswith('EVE - '):return True
            pid=self.W.DWORD();self.user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            handle=self.kernel.OpenProcess(0x1000,False,pid.value)
            if not handle:return True
            try:
                image=ctypes.create_unicode_buffer(32768);length=self.W.DWORD(len(image))
                if not self.kernel.QueryFullProcessImageNameW(handle,0,image,ctypes.byref(length)) or Path(image.value).name.lower()!='exefile.exe':return True
            finally:self.kernel.CloseHandle(handle)
            found.append({'title':title.value,'hwnd':int(hwnd),'pid':pid.value})
            return True
        self.user.EnumWindows(visit,0)
        counts={}
        for row in sorted(found,key=lambda r:r['hwnd']):
            title=row['title'];index=counts.get(title,0);counts[title]=index+1
            row['key']=hashlib.sha256(title.encode()).hexdigest()[:24]+(':'+str(row['pid']) if index else '')
        return found

    def modifiers(self):
        return sum(mask for keys,mask in [((0x11,),4096),((0x12,),2048),((0x5b,0x5c),256),((0x10,),512)] if any(self.user.GetAsyncKeyState(k)&0x8000 for k in keys))

    def check_shortcuts(self,keys):
        # Probe registered/reserved global combinations without keeping a global
        # registration: plain letters must remain usable outside EVE.
        for index,key in enumerate(keys):
            key=shortcut(key);mods=key['modifiers']
            if not mods&~512:continue
            native=sum(bit for mask,bit in [(4096,2),(2048,1),(256,8),(512,4)] if mods&mask)
            ident=0x6900+index
            if not self.user.RegisterHotKey(None,ident,native|0x4000,key['code']):return False
            self.user.UnregisterHotKey(None,ident)
        return True


class ShortcutHook:
    def __init__(self,api,state,events):
        self.api=api;self.state=state;self.events=events;self.thread=None;self.thread_id=0;self.handle=None;self.ready=threading.Event();self.swallowed=set();self.callback=None

    def process(self,code,down,mods,eve,injected=False):
        if injected:return False
        if not down:
            if code in self.swallowed:self.swallowed.discard(code);return True
            return False
        if code in self.swallowed:return True
        direction=self.state.match(code,mods,eve)
        if not direction:return False
        self.swallowed.add(code);self.events.put(direction);return True

    def start(self):
        if self.thread and self.thread.is_alive():return
        self.ready.clear();self.thread=threading.Thread(target=self._run,name='eve-preview-shortcuts',daemon=True);self.thread.start()
        if not self.ready.wait(1) or not self.handle:self.state.error='hotkey_unavailable'

    def _run(self):
        api=self.api;self.thread_id=api.kernel.GetCurrentThreadId();message=api.W.MSG()
        api.user.PeekMessageW(ctypes.byref(message),None,0,0,0)  # Create message queue before shutdown may post WM_QUIT.
        @api.hook_proc
        def callback(code,kind,data):
            if code>=0 and kind in {0x100,0x101,0x104,0x105}:
                try:
                    key=ctypes.cast(data,ctypes.POINTER(api.Keyboard)).contents
                    eve=any(r['hwnd']==api.user.GetForegroundWindow() for r in tuple(self.state.sources.values()))
                    if self.process(key.vkCode,kind in {0x100,0x104},api.modifiers(),eve,bool(key.flags&0x10)):return 1
                except Exception:LOG.exception('Preview shortcut failed')
            return api.user.CallNextHookEx(self.handle,code,kind,data)
        self.callback=callback
        self.handle=api.user.SetWindowsHookExW(13,callback,api.kernel.GetModuleHandleW(None),0)
        self.state.hotkeys_active=bool(self.handle)
        if self.handle and self.state.error=='hotkey_unavailable':self.state.error=''
        self.ready.set()
        try:
            if self.handle:
                while api.user.GetMessageW(ctypes.byref(message),None,0,0)>0:pass
        finally:
            if self.handle:api.user.UnhookWindowsHookEx(self.handle)
            self.handle=None;self.state.hotkeys_active=False;self.swallowed.clear()

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.api.user.PostThreadMessageW(self.thread_id,0x12,0,0);self.thread.join(1)
        self.swallowed.clear()


class NativePreview:
    def __init__(self,folder,owner,callback,theme='dark',language='hu'):
        from System.Windows.Forms import Timer
        self.state=PreviewState(folder);self.api=Win32();self.owner=owner;self.callback=callback
        self.theme=theme;self.language=language;self.tiles={};self.events=queue.SimpleQueue();self.hook=ShortcutHook(self.api,self.state,self.events)
        self.disposed=False;self.failure=None;self.last_scan=0;self.last_poll=0;self.last_phase=None;self.current=None;self.last_foreground=None
        self.timer=Timer();self.timer.Interval=100;self.timer.Tick+=self._tick
        try:self.refresh();self.timer.Start()
        except Exception:
            self.dispose();raise

    def preferences(self,theme,language):
        self.theme=theme;self.language=language
        for tile in self.tiles.values():tile['form'].Invalidate()

    def refresh(self):
        self.state.reconcile(self.api.discover());self.last_scan=time.monotonic();self._render();return self.status()

    def status(self):
        state=self.state;foreground=self.api.user.GetForegroundWindow()
        return {**{k:getattr(state,k) for k in ('enabled','editing','only_eve','fps','next_key','previous_key','shortcut_count','hotkeys_active','error')},
                'supported':True,'screen_permission':True,'accessibility_permission':True,'refreshing':False,
                'windows':[{**s,'title':state.sources.get(s['key'],{}).get('title',s['title']),
                            'online':s['key'] in state.sources,'active':state.sources.get(s['key'],{}).get('hwnd')==foreground,
                            'has_frame':bool(self.tiles.get(s['key'],{}).get('thumbnail')),
                            'capturing':bool(self.tiles.get(s['key'],{}).get('thumbnail')),
                            'screen':s['screen']} for s in state.slots]}

    def configure(self,options):
        if isinstance(options,dict) and any(k in options for k in ('next_key','previous_key')):
            if not self.api.check_shortcuts([options.get('next_key',self.state.next_key),options.get('previous_key',self.state.previous_key)]):
                raise ValueError('The shortcut is already in use. Choose another.' if self.language=='en' else 'A gyorsbillentyű már foglalt. Válassz másikat.')
        self.state.configure(options)
        if not self.state.enabled:self.state.error=''
        self._render();return self.status()

    def capture_key(self,capturing):
        if type(capturing) is not bool:raise ValueError('Invalid key capture')
        self.state.capturing_key=capturing;return self.status()

    def sync(self,data):
        self.state.sync_mining(data)
        for tile in self.tiles.values():tile['form'].Invalidate()
        return True

    def activate(self,key):
        row=self.state.sources.get(key);slot=next((s for s in self.state.slots if s['key']==key),None)
        if not row or not slot or not slot['enabled'] or not self.api.user.IsWindow(row['hwnd']):raise ValueError('This EVE window is no longer available' if self.language=='en' else 'Ez az EVE-ablak már nem érhető el')
        if self.api.user.IsIconic(row['hwnd']):self.api.user.ShowWindow(row['hwnd'],9)
        if not self.api.user.SetForegroundWindow(row['hwnd']):
            self.state.error='activate_failed';raise ValueError('Windows could not activate the EVE window' if self.language=='en' else 'A Windows nem tudta előrehozni az EVE-ablakot')
        self.current=key;self.state.error='';return self.status()

    def cycle(self,direction):
        foreground=self.api.user.GetForegroundWindow();current=next((k for k,s in self.state.sources.items() if s['hwnd']==foreground),self.current)
        slot=self.state.next_slot(current,direction)
        return self.activate(slot['key']) if slot else self.status()

    def _tick(self,*_):
        if self.disposed:return
        try:
            if any(tile['dragging'] for tile in self.tiles.values()):return
            while not self.events.empty():
                direction=self.events.get_nowait()
                if self.state.enabled and not self.state.editing and not self.state.capturing_key:
                    self.state.shortcut_count+=1;self.cycle(direction)
            now=time.monotonic()
            if now-self.last_scan>=2:self.refresh()
            else:self._visibility()
            if self.state.enabled and now-self.last_poll>=2:
                self.last_poll=now;self.callback('poll')
            phase=int(time.time()*2)
            if phase!=self.last_phase:
                self.last_phase=phase
                for tile in self.tiles.values():tile['form'].Invalidate()
        except Exception as exc:self.failure=exc;LOG.exception('Windows preview update failed')

    def _remove(self,key):
        tile=self.tiles.pop(key)
        if tile.get('thumbnail'):self.api.dwm.DwmUnregisterThumbnail(tile['thumbnail'])
        tile['tooltip'].Dispose();tile['form'].Dispose();tile['font'].Dispose()

    def _render(self):
        if self.state.error=='capture_failed':self.state.error=''
        live={s['key']:s for s in self.state.candidates()} if self.state.enabled else {}
        for key in list(self.tiles):
            if key not in live or self.tiles[key]['source']!=self.state.sources[key]['hwnd'] or not self.tiles[key]['thumbnail']:self._remove(key)
        for key,slot in live.items():
            if key not in self.tiles:self._create(slot)
            self._bounds(slot,self.tiles[key])
        if self.state.enabled:self.hook.start()
        else:self.hook.stop()
        self._visibility()

    def _visibility(self):
        foreground=self.api.user.GetForegroundWindow()
        changed=foreground!=self.last_foreground;self.last_foreground=foreground
        visible=self.state.editing or not self.state.only_eve or any(s['hwnd']==foreground for s in self.state.sources.values())
        for tile in self.tiles.values():
            form=tile['form'];hwnd=form.Handle.ToInt64()
            shown=bool(self.api.user.IsWindowVisible(hwnd))
            if visible and not shown:
                self.api.user.ShowWindow(hwnd,4);self.api.user.SetWindowPos(hwnd,ctypes.c_void_p(-1),0,0,0,0,0x13)
            elif visible and changed:self.api.user.SetWindowPos(hwnd,ctypes.c_void_p(-1),0,0,0,0,0x13)
            elif not visible and shown:self.api.user.ShowWindow(hwnd,0)

    def _create(self,slot):
        from System.Windows.Forms import Form,FormBorderStyle,ToolTip,FormStartPosition,AutoScaleMode
        from System.Drawing import Color,Font,FontStyle,Size
        form=Form();form.FormBorderStyle=getattr(FormBorderStyle,'None');form.ShowInTaskbar=False;form.TopMost=True
        form.StartPosition=FormStartPosition.Manual;form.AutoScaleMode=getattr(AutoScaleMode,'None');form.MinimumSize=Size(100,40)
        form.BackColor=Color.FromArgb(12,24,33);form.Text='eve-preview'
        font=Font('Segoe UI',9,FontStyle.Bold);tooltip=ToolTip()
        tile={'form':form,'source':self.state.sources[slot['key']]['hwnd'],'thumbnail':None,'font':font,'tooltip':tooltip,'dragging':False}
        self.tiles[slot['key']]=tile;hwnd=form.Handle.ToInt64()
        style=self.api.user.GetWindowLongPtrW(hwnd,-20)
        self.api.user.SetWindowLongPtrW(hwnd,-20,style|0x80|0x8000000)  # Tool window, never activate on click.
        self.api.user.SetWindowPos(hwnd,ctypes.c_void_p(-1),0,0,0,0,0x33)  # Apply cached extended styles without activation.
        form.Paint+=lambda sender,event:self._paint(slot,tile,event)
        form.MouseDown+=lambda sender,event:self._mouse(slot,tile,event)
        form.MouseMove+=lambda sender,event:self._hover(slot,tile,event)
        handle=self.api.W.HANDLE()
        if self.api.dwm.DwmRegisterThumbnail(hwnd,tile['source'],ctypes.byref(handle))<0:self.state.error='capture_failed'
        else:tile['thumbnail']=handle
        self._bounds(slot,tile)

    def _bounds(self,slot,tile):
        from .windows_overlay import NativeOverlay
        from System.Drawing import Rectangle
        size=self.api.W.SIZE();ratio=16/9
        if tile['thumbnail'] and self.api.dwm.DwmQueryThumbnailSourceSize(tile['thumbnail'],ctypes.byref(size))>=0 and size.cy:ratio=size.cx/size.cy
        left,top,width,height=self.state.bounds(slot,NativeOverlay.screens(),ratio)
        tile['form'].Bounds=Rectangle(left,top,width,height)
        if tile['thumbnail']:
            props=self.api.Props();props.flags=1|4|8|16;props.destination=self.api.W.RECT(0,24,width,height);props.opacity=255;props.visible=True;props.client=True
            if self.api.dwm.DwmUpdateThumbnailProperties(tile['thumbnail'],ctypes.byref(props))<0:self.state.error='capture_failed'
        tile['form'].Invalidate()

    def _icons(self,slot,tile):
        width=tile['form'].ClientSize.Width
        return [(a,width-24-22*i) for i,a in enumerate(reversed(self.state.alerts(slot['key'])['alerts']))]

    def _paint(self,slot,tile,event):
        try:
            from System.Drawing import Color,Rectangle,SolidBrush,Pen
            from System.Windows.Forms import TextRenderer,TextFormatFlags
            g=event.Graphics;width=tile['form'].ClientSize.Width;dark=self.theme=='dark'
            back=Color.FromArgb(26,45,57) if dark else Color.FromArgb(224,234,240)
            brush=SolidBrush(back)
            try:g.FillRectangle(brush,Rectangle(0,0,width,24))
            finally:brush.Dispose()
            icons=self._icons(slot,tile);end=min((x for _,x in icons),default=width)-6
            title=slot['label'] or self.state.sources[slot['key']]['title']
            color=Color.FromArgb(255,85,85) if self.state.flashing(slot['key']) else (Color.FromArgb(229,239,244) if dark else Color.FromArgb(21,42,55))
            TextRenderer.DrawText(g,title,tile['font'],Rectangle(7,2,max(0,end-7),20),color,TextFormatFlags.NoPrefix|TextFormatFlags.EndEllipsis|TextFormatFlags.SingleLine)
            for alert,x in icons:
                kind=alert['kind'];color={'cargo_full':Color.FromArgb(255,100,90),'crystal_broken':Color.FromArgb(255,193,79),'rock_depleted':Color.FromArgb(180,194,204),'module_stopped':Color.FromArgb(105,206,240)}[kind]
                pen=Pen(color,2)
                try:
                    if kind=='cargo_full':g.DrawRectangle(pen,x+3,6,14,12);g.DrawLine(pen,x+3,10,x+17,10);g.DrawLine(pen,x+10,6,x+10,17)
                    elif kind=='crystal_broken':
                        g.DrawLine(pen,x+10,3,x+17,11);g.DrawLine(pen,x+17,11,x+10,20);g.DrawLine(pen,x+10,20,x+3,11);g.DrawLine(pen,x+3,11,x+10,3);g.DrawLine(pen,x+2,20,x+18,3)
                    elif kind=='rock_depleted':g.DrawLine(pen,x+2,18,x+9,5);g.DrawLine(pen,x+9,5,x+18,18);g.DrawLine(pen,x+2,18,x+18,18);g.DrawLine(pen,x+2,3,x+18,21)
                    else:g.DrawLine(pen,x+7,5,x+7,19);g.DrawLine(pen,x+13,5,x+13,19)
                finally:pen.Dispose()
            if self.state.editing:
                pen=Pen(Color.FromArgb(100,205,236),2)
                try:
                    h=tile['form'].Height;g.DrawLine(pen,width-13,h-2,width-2,h-13);g.DrawLine(pen,width-7,h-2,width-2,h-7)
                finally:pen.Dispose()
        except Exception as exc:self.failure=exc;LOG.exception('Preview painting failed')

    def _hover(self,slot,tile,event):
        names={'cargo_full':('Megtelt raktér','Cargo full'),'crystal_broken':('Kristály cserélve — kattints','Crystal replaced — click'),'rock_depleted':('Elfogyott kő','Asteroid depleted'),'module_stopped':('Modul nem fut — kattints a törléshez','Module stopped — click to clear')}
        alert=next((a for a,x in self._icons(slot,tile) if event.Y<24 and x<=event.X<x+20),None)
        text=names[alert['kind']][self.language=='en'] if alert else ''
        if alert:
            text+=' · '+' · '.join(v for v in (alert.get('module'),alert.get('crystal'),time.strftime('%H:%M:%S',time.localtime(alert['at'])) if alert.get('at') is not None else '') if v)
        if tile.get('tip')!=text:tile['tooltip'].SetToolTip(tile['form'],text);tile['tip']=text

    def _mouse(self,slot,tile,event):
        from System.Windows.Forms import MouseButtons
        from .windows_overlay import NativeOverlay
        if event.Button!=MouseButtons.Left:return
        if not self.state.editing:
            alert=next((a for a,x in self._icons(slot,tile) if event.Y<24 and x<=event.X<x+20 and a['kind'] in {'crystal_broken','module_stopped'}),None)
            if alert:
                try:self.activate(slot['key'])
                except ValueError:pass
                self.callback('mining',{'name':self.state.sources[slot['key']]['title'].removeprefix('EVE - ').strip(),'kind':alert['kind'],'id':alert['id']});return
            try:self.activate(slot['key'])
            except ValueError:pass
            return
        form=tile['form'];hwnd=form.Handle.ToInt64()
        resize=event.X>=form.Width-20 and event.Y>=form.Height-20
        tile['dragging']=True
        try:
            self.api.user.ReleaseCapture();self.api.user.SendMessageW(hwnd,0xA1,17 if resize else 2,0)
            self.state.place(slot,form.Left,form.Top,form.Width,NativeOverlay.screens());self._bounds(slot,tile)
        finally:tile['dragging']=False

    def dispose(self):
        if self.disposed:return
        self.disposed=True;self.state.enabled=False;self.hook.stop();self.timer.Stop();self.timer.Dispose()
        for key in list(self.tiles):self._remove(key)
