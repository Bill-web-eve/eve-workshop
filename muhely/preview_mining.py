"""Read local game-log events for preview badges and incoming damage; no ESI or game interaction."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, html, os, re, stat, threading, time
from .planner import PlanningError

FILE = re.compile(r'^\d{8}_\d{6}_(\d+)\.txt$', re.I)
LINE = re.compile(r'^\[\s*(\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d)\s*\]\s*\(([^)]+)\)\s*(.*)$')
INCOMING_DAMAGE = re.compile(r'^(?P<amount>\d(?:[\d\s,.]*\d)?) from \S.+$', re.I)
KINDS = ('cargo_full', 'crystal_broken', 'rock_depleted', 'module_stopped')
PATTERNS = [
 ('cargo_full', re.compile(r"^Your (?P<module>.+?) has completed operations\. Ship's (?:cargo|mining|ore) hold is full\.?$", re.I)),
 ('crystal_broken', re.compile(r'^(.+?) deactivates due to the destruction of the (.+?) it was fitted with\.$', re.I)),
 ('rock_depleted', re.compile(r'^(?P<module>.+?) deactivates as it finds the resource it was harvesting a pale shadow of its former glory\.$', re.I)),
]


def event(line, now):
    match = LINE.match(line.strip().lstrip('\ufeff'))
    if not match: return None
    stamp, category, body = match.groups()
    try: at = datetime.strptime(stamp, '%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
    except ValueError: return None
    if at > now + 60: return None
    body = html.unescape(re.sub(r'<[^>]*>', '', body)).strip()
    if len(body) > 2000: return None
    if category == 'combat':
        hit = INCOMING_DAMAGE.fullmatch(body)
        if hit and any(c in '123456789' for c in hit['amount']) and at <= now + 2:
            return {'kind':'damage', 'at':at}
        return None
    if category == 'mining' and re.match(r'^You mined [\d\s,.]+ units of .+', body):
        return {'kind':'mined', 'at':at}
    if category not in ('notify', 'hint', 'info'): return None
    for kind, pattern in PATTERNS:
        if found := pattern.fullmatch(body):
            module = found.group(1).strip()
            if len(module) > 160: return None
            return {'kind':kind, 'at':at, 'module':module,
                    'crystal':found.group(2).strip()[:160] if kind == 'crystal_broken' else ''}
    found = re.fullmatch(r'(.+?) is already active', body, re.I)
    if found and re.search(r'miner|harvester|mining laser', found[1], re.I):
        return {'kind':'module_active', 'at':at, 'module':found[1][:160]}
    if re.fullmatch(r'(?:The )?asteroid (?:is |has been )?depleted\.?', body, re.I):
        return {'kind':'rock_depleted', 'at':at, 'module':'', 'crystal':''}
    return None


class PreviewMining:
    def __init__(self, store, clock=None):
        self.store, self.clock = store, clock or time.time
        self.lock = threading.RLock()
        self.files, self.characters = {}, {}
        self.started, self.checked, self.error, self.file_errors = self.clock(), None, None, 0
        self.initialized, self.closed = False, False
        saved = store.settings().get('preview_mining', {})
        if not isinstance(saved, dict): saved = {}
        folder = saved.get('folder') if isinstance(saved, dict) else None
        if not folder:
            candidates = [Path.home()/'Documents/EVE/logs/Gamelogs']
            # Intel uses its own config table; selecting its sibling is optional.
            with store.db() as db:
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='intel_config'").fetchone():
                    row = db.execute('SELECT data FROM intel_config WHERE id=1').fetchone()
                    if row:
                        import json
                        configured = json.loads(row['data']).get('folder')
                        if configured: candidates.insert(0, Path(configured).parent/'Gamelogs')
            folder = str(next((p for p in candidates if p.is_dir()), candidates[-1]))
        self.config = {'enabled':saved.get('enabled', True) is True, 'folder':folder}

    def configure(self, data):
        if not isinstance(data, dict) or set(data) != {'enabled', 'folder'} or type(data['enabled']) is not bool:
            raise PlanningError('Hibás bányászatinapló-beállítás.')
        if not isinstance(data['folder'], str) or len(data['folder']) > 2000 or not data['folder'].strip():
            raise PlanningError('Válassz elérhető Gamelogs mappát.')
        root = Path(data['folder']).expanduser().resolve()
        if not root.is_dir(): raise PlanningError('A Gamelogs mappa nem érhető el.')
        with self.lock:
            config = {'enabled':data['enabled'], 'folder':str(root)}
            if config != self.config:
                self.config = config
                self.files, self.characters, self.initialized = {}, {}, False
                self.started, self.checked = self.clock(), None
            self.store.save_settings({'preview_mining':config})
        return self.snapshot(force=True)

    @staticmethod
    def open_log(path):
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        stream = os.fdopen(fd, 'rb')
        try:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode): raise ValueError('Not a regular log')
            head = stream.read(4096)
            enc = 'utf-16-le' if head.startswith(b'\xff\xfe') else 'utf-16-be' if head.startswith(b'\xfe\xff') else 'utf-8-sig'
            text = head[:len(head)//2*2].decode(enc, errors='replace') if enc.startswith('utf-16') else head.decode(enc, errors='replace')
            listener = re.search(r'^\s*Listener:\s*([^\r\n]+)', text, re.M)
            if 'Gamelog' not in text[:200] or not listener or not 1 <= len(listener[1].strip()) <= 100:
                raise ValueError('Wrong game-log header')
            return stream, info, enc, listener[1].strip()
        except Exception:
            stream.close()
            raise

    def scan(self):
        now = self.clock()
        self.checked, self.error, self.file_errors = now, None, 0
        try:
            root = Path(self.config['folder'])
            # Only the latest session for each character, never every historical file.
            latest = {}
            for p in root.iterdir():
                match = FILE.fullmatch(p.name)
                if not match or p.is_symlink() or not p.is_file(): continue
                cid = match[1]
                if cid not in latest or p.name > latest[cid].name: latest[cid] = p
            active = set()
            for cid, path in latest.items():
                try:
                    stream, info, enc, name = self.open_log(path)
                    with stream:
                        active.add(name.casefold())
                        identity = (path.name, info.st_dev, info.st_ino)
                        cursor = self.files.get(cid)
                        fresh = cursor is None or cursor['identity'] != identity or info.st_size < cursor['offset']
                        if not fresh and cursor.get('tail'):
                            stream.seek(max(0, cursor['offset']-64))
                            fresh = stream.read(min(64,cursor['offset'])) != cursor['tail']
                        if fresh:
                            cursor = {'identity':identity, 'offset':0, 'name':name, 'skip_partial':False}
                            self.files[cid] = cursor
                            self.characters[name.casefold()] = {'name':name, 'character_id':int(cid), 'alerts':{}, 'last_module':'', 'module_at':None, 'last_mined':None, 'last_damage':None}
                            if not self.initialized:
                                # Start at EOF: old errors must never look like a live problem.
                                sep = b'\n\x00' if enc == 'utf-16-le' else b'\x00\n' if enc == 'utf-16-be' else b'\n'
                                stream.seek(max(0, info.st_size-len(sep)))
                                cursor['skip_partial'] = bool(info.st_size and not stream.read().endswith(sep))
                                cursor['offset'] = info.st_size - (info.st_size % 2 if enc.startswith('utf-16') else 0)
                                stream.seek(max(0,cursor['offset']-64));cursor['tail']=stream.read(min(64,cursor['offset']))
                                continue
                        stream.seek(cursor['offset']); chunk = stream.read(256*1024)
                        sep = b'\n\x00' if enc == 'utf-16-le' else b'\x00\n' if enc == 'utf-16-be' else b'\n'
                        end = chunk.rfind(sep)
                        while end >= 0 and enc.startswith('utf-16') and end % 2: end = chunk.rfind(sep, 0, end)
                        if end < 0: continue
                        complete = chunk[:end+len(sep)]
                        cursor['offset'] += len(complete)
                        stream.seek(max(0,cursor['offset']-64));cursor['tail']=stream.read(min(64,cursor['offset']))
                        lines = complete.decode(enc, errors='replace').splitlines()
                        if cursor.pop('skip_partial', False) and lines: lines = lines[1:]
                        row = self.characters[name.casefold()]
                        for line in lines:
                            found = event(line, now)
                            if not found or found['at'] < self.started: continue
                            kind = found['kind']
                            if kind == 'damage':
                                row['last_damage'] = max(row['last_damage'] or 0, found['at'])
                                continue
                            if kind == 'mined':
                                row['last_mined'] = found['at']
                                stopped = row['alerts'].get('module_stopped')
                                if stopped and found['at'] > stopped['at']: row['alerts'].pop('module_stopped')
                                continue
                            if found.get('module') and (row['module_at'] is None or found['at'] >= row['module_at']):
                                row['last_module'], row['module_at'] = found['module'], found['at']
                            if kind == 'module_active':
                                stopped = row['alerts'].get('module_stopped')
                                if stopped and found['at'] > stopped['at'] and found['module'].casefold() == stopped['module'].casefold(): row['alerts'].pop('module_stopped')
                            if kind in KINDS:
                                found['id'] = hashlib.sha256((cid+'\0'+str(identity)+'\0'+line).encode()).hexdigest()[:24]
                                if kind == 'crystal_broken': row['alerts'].pop('module_stopped', None)
                                previous = row['alerts'].get(kind)
                                if previous is None or found['at'] >= previous['at']: row['alerts'][kind] = found
                except (OSError, ValueError, UnicodeError):
                    self.file_errors += 1
                    if old := self.files.get(cid): active.add(old['name'].casefold())
            self.initialized = True
            self.characters = {k:v for k,v in self.characters.items() if k in active}
        except OSError: self.error = 'folder_unavailable'

    def snapshot(self, force=False):
        with self.lock:
            if not self.closed and self.config['enabled'] and (force or self.checked is None or self.clock()-self.checked >= 1.5): self.scan()
            return {**self.config, 'checked':self.checked, 'started':self.started, 'error':self.error,
                    'file_errors':self.file_errors, 'characters':[dict(row, alerts=list(row['alerts'].values())) for row in sorted(self.characters.values(), key=lambda r:r['name'].casefold())] if self.config['enabled'] else []}

    def replace_crystal(self, data):
        if not isinstance(data, dict) or set(data) != {'name','id'} or not isinstance(data['name'],str) or not isinstance(data['id'],str) or not re.fullmatch('[a-f0-9]{24}',data['id']):
            raise PlanningError('Hibás bányászati jelzés.')
        with self.lock:
            # Read newer events first; an old icon click must not clear a new break.
            self.snapshot(force=True)
            row = self.characters.get(data['name'].casefold())
            current = row['alerts'].get('crystal_broken') if row else None
            if current and current['id'] == data['id']:
                row['alerts'].pop('crystal_broken')
                row['alerts']['module_stopped'] = {'kind':'module_stopped','at':self.clock(),'module':current['module'],'crystal':'','source':'manual',
                    'id':hashlib.sha256((current['id']+':replaced').encode()).hexdigest()[:24]}
        return self.snapshot()

    def acknowledge(self, data):
        if not isinstance(data, dict) or set(data) != {'name', 'ids'} or not isinstance(data['name'], str) or not isinstance(data['ids'], list) or len(data['ids']) > 4 or any(not isinstance(v, str) or not re.fullmatch('[a-f0-9]{24}', v) for v in data['ids']):
            raise PlanningError('Hibás bányászati jelzés.')
        with self.lock:
            if row := self.characters.get(data['name'].casefold()):
                row['alerts'] = {k:v for k,v in row['alerts'].items() if v['id'] not in data['ids']}
        return self.snapshot(force=True)
