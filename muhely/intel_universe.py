"""Public CCP topology. Distances use stargates only, never geometric proximity."""
from collections import defaultdict,deque
from functools import lru_cache
from pathlib import Path
import json,re,zipfile


def build(archive,target,build_number=None):
    with zipfile.ZipFile(archive) as z:
        if not {'mapSolarSystems.jsonl','mapStargates.jsonl'}.issubset(z.namelist()):return False
        def rows(name):
            return (json.loads(line) for line in z.open(name) if line.strip())
        regions={r['_key']:r['name']['en'] for r in rows('mapRegions.jsonl')}
        systems={r['_key']:{'id':r['_key'],'name':r['name']['en'],'region_id':r['regionID'],'region':regions.get(r['regionID'],''),'security':r.get('securityStatus',0),'x':r.get('position2D',{}).get('x',r['position']['x'])/1e16,'y':r.get('position2D',{}).get('y',-r['position']['z'])/1e16} for r in rows('mapSolarSystems.jsonl')}
        edges=sorted({tuple(sorted((r['solarSystemID'],r['destination']['solarSystemID']))) for r in rows('mapStargates.jsonl') if r['solarSystemID'] in systems and r['destination']['solarSystemID'] in systems and r['solarSystemID']!=r['destination']['solarSystemID']})
        groups={r['_key'] for r in rows('groups.jsonl') if r.get('categoryID')==6}
        ship_types={r['name']['en']:r['_key'] for r in rows('types.jsonl') if r.get('groupID') in groups and r.get('published') and 'en' in r.get('name',{})}
        ships=sorted(ship_types)
        data={'schema':2,'build':build_number,'source':'https://developers.eveonline.com/docs/services/static-data/','systems':list(systems.values()),'edges':edges,'ships':ships,'ship_types':ship_types}
        assert len(systems)>5000 and len(edges)>5000
        p=Path(target);p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix('.building.json');temp.write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False));temp.replace(p)
        return True


class Universe:
    def __init__(self,data):
        self.build=data.get('build');self.systems={r['id']:r for r in data['systems']};self.edges=[tuple(e) for e in data['edges']]
        self.names={r['name'].casefold():r['id'] for r in self.systems.values()};self.adj={sid:set() for sid in self.systems};self.prefix=defaultdict(set)
        for a,b in self.edges:self.adj[a].add(b);self.adj[b].add(a)
        for name,sid in self.names.items():
            for size in range(3,len(name)):self.prefix[name[:size]].add(sid)
        self.pattern=re.compile(r'(?<![\w-])(?:'+('|'.join(re.escape(r['name']) for r in sorted(self.systems.values(),key=lambda r:-len(r['name']))))+r')(?![\w-])',re.I)
        self.ship_names={name.casefold():name for name in data.get('ships',[])}
        self.ship_types={name.casefold():tid for name,tid in data.get('ship_types',{}).items()}
        self.ship_aliases={'caracal ni':'Caracal Navy Issue','caracal navy':'Caracal Navy Issue','carcacal':'Caracal','carcacal ni':'Caracal Navy Issue','vni':'Vexor Navy Issue','cheeta':'Cheetah','drek':'Drekavac','hecates':'Hecate',"hecate's":'Hecate','pod':'Capsule'}
        ships=sorted(set(data.get('ships',[]))|set(self.ship_aliases)|{'shuttle','loki','dscan','capsule','ships','fleet','gang','neuts','neutral','neutrals','hostile','hostiles'},key=lambda s:-len(s))
        self.ship_pattern=re.compile(r'(?<![\w-])(?:'+'|'.join(map(re.escape,ships))+r')(?![\w-])',re.I)
    def reported_ships(self,text):
        found={}
        for match in self.ship_pattern.finditer(text):
            key=match.group().casefold();name=self.ship_aliases.get(key) or self.ship_names.get(key)
            if not name and key=='shuttle':name='Shuttle'
            if not name:continue
            tid=self.ship_types.get(name.casefold());found[name]={'name':name,'type_id':tid}
        return list(found.values())
    def resolve(self,value):return self.names.get(value.strip().casefold())
    def mentions(self,text,regions=()):
        found=[(self.names[m.group().casefold()],m.span(),False) for m in self.pattern.finditer(text)]
        occupied=[span for _,span,_ in found]
        for m in re.finditer(r'(?<![\w-])[A-Z0-9][A-Z0-9-]{2,5}(?![\w-])',text):
            if not any(c.isdigit() or c=='-' for c in m.group()) or any(a<=m.start()<b for a,b in occupied):continue
            choices=self.prefix.get(m.group().casefold(),set())
            if regions:choices={sid for sid in choices if self.systems[sid]['region_id'] in regions}
            if len(choices)==1:found.append((next(iter(choices)),m.span(),True))
        return sorted(found,key=lambda row:row[1])
    @lru_cache(maxsize=128)
    def distances(self,origin):
        if origin not in self.systems:return {}
        result={origin:0};queue=deque([origin])
        while queue:
            sid=queue.popleft()
            for other in self.adj[sid]:
                if other not in result:result[other]=result[sid]+1;queue.append(other)
        return result
    def route(self,origin,target):
        distances=self.distances(target)
        if origin not in distances:return []
        path=[origin]
        while path[-1]!=target:path.append(min(n for n in self.adj[path[-1]] if distances.get(n)==distances[path[-1]]-1))
        return path

@lru_cache(maxsize=4)
def _load(path,modified):return Universe(json.loads(Path(path).read_text()))

def load(store=None):
    bundled=Path(__file__).resolve().parents[1]/'data/intel_universe.json'
    p=(store.folder/'intel_universe.json') if store and (store.folder/'intel_universe.json').exists() else bundled
    return _load(str(p),p.stat().st_mtime_ns)
