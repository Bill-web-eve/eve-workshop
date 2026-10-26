"""Expected (non-random) T2 ship BPC cost and full-chain decryptor comparison.

CCP: /news/view/invention-updates and /news/view/eve-industry-all-you-want-to-know
One T1 licensed run and all consumables are spent for every attempt, including failures.
"""
from decimal import Decimal,ROUND_HALF_UP,ROUND_DOWN
import copy
from .planner import PlanningError,integer,decimal_number,Planner
from .production import profiles
D=lambda value:Decimal(str(value))
ENCRYPTION={21790,21791,23087,23121,52308,55025}


def defaults(store,catalog,product_id):
    f=store.settings()['manufacturing'];recipe=catalog.inventions.get(product_id,{})
    facility={'system_id':f.get('system_id'),'facility_tax':str(f.get('facility_tax',0)),'job_cost_role':'0','scc_surcharge':str(f.get('scc_surcharge',4)),'alpha_surcharge':str(f.get('alpha_surcharge',0))}
    return {'enabled':False,'product_id':product_id,'inventor_id':None,'decryptor_id':0,'prices':'jita:sell','attempts':100,
            'copy_runs':recipe.get('copy_limit',1),'copying':dict(facility),'invention':dict(facility)}


def validate(data,store,catalog):
    if data is None:return None
    fields={'enabled','product_id','inventor_id','decryptor_id','prices','attempts','copy_runs','copying','invention'}
    if not isinstance(data,dict) or set(data)!=fields:raise PlanningError('Hibás invention-beállítás.')
    product=integer(data['product_id'],'Termék',10**9,1)
    if product not in getattr(catalog,'inventions',{}):raise PlanningError('Ehhez a termékhez nincs T2 hajó invention-recept.')
    if type(data['enabled']) is not bool:raise PlanningError('Hibás invention-kapcsoló.')
    inventor=data['inventor_id']
    if inventor is not None:
        inventor=integer(inventor,'Karakter',2**53-1,1)
        if inventor not in {c['id'] for c in store.characters()}:raise PlanningError('Ismeretlen inventáló karakter.')
    decryptor=integer(data['decryptor_id'],'Decryptor',10**9)
    if decryptor and decryptor not in catalog.decryptors:raise PlanningError('Ismeretlen decryptor.')
    if data['prices'] not in [s+':'+m for s in ['jita','local'] for m in ['buy','sell','split']]:raise PlanningError('Ismeretlen árforrás.')
    result={**data,'product_id':product,'inventor_id':inventor,'decryptor_id':decryptor,
            'attempts':integer(data['attempts'],'Próbálkozások',10**6,1),
            'copy_runs':integer(data['copy_runs'],'Run/másolat',catalog.inventions[product]['copy_limit'],1)}
    for activity in ['copying','invention']:
        raw=data[activity]
        if not isinstance(raw,dict) or set(raw)!={'system_id','facility_tax','job_cost_role','scc_surcharge','alpha_surcharge'}:raise PlanningError('Hibás invention-létesítmény.')
        sid=raw['system_id']
        if sid is not None:
            sid=integer(sid,'Rendszer',2**31-1,1)
            if sid not in catalog.moon_systems:raise PlanningError('Ismeretlen rendszer.')
        result[activity]={'system_id':sid,**{k:format(decimal_number(raw[k],'Díj / bónusz',0,100),'f') for k in raw if k!='system_id'}}
    return result


def chance(recipe,levels,multiplier):
    science=[s for s in recipe['skills'] if s['typeID'] not in ENCRYPTION]
    encryption=[s for s in recipe['skills'] if s['typeID'] in ENCRYPTION]
    if len(science)!=2 or len(encryption)!=1:raise PlanningError('Hiányos invention-skillrecept; frissítsd a receptadatokat.')
    return min(D(1),D(recipe['base_probability'])*(1+sum(D(levels.get(s['typeID'],0)) for s in science)/30+D(levels.get(encryption[0]['typeID'],0))/40)*D(multiplier))


def cents(value):return str(int((value*100).quantize(D(1),rounding=ROUND_HALF_UP))) if value is not None else None


def unit(quote,mode):
    def price(v):
        try:
            n=D(v)
            return n if n.is_finite() and n>0 else None
        except Exception:return None
    buy=price((quote or {}).get('buy'));sell=price((quote or {}).get('sell'))
    return buy if mode=='buy' else sell if mode=='sell' else ((buy+sell)/2).quantize(D('.0001'),rounding=ROUND_DOWN) if buy is not None and sell is not None else None


def material_cost(rows,quotes,mode):
    total=D(0);missing=[];stale=False
    for row in rows:
        p=unit(quotes.get(str(row['id'])),mode)
        if p is None:missing.append(row['id'])
        else:total+=D(cents(p*row['quantity']))/100
        stale|=bool((quotes.get(str(row['id'])) or {}).get('stale'))
    return (None if missing else total),missing,stale


def fee(industry,catalog,product_ids,activity,facility,runs=1):
    data={k:industry.cached(k) for k in ['prices','systems']};prices=(data['prices'] or {}).get('data',{}).get('values',{})
    indices=(data['systems'] or {}).get('data',{}).get('values',{}).get(str(facility['system_id']),{})
    index=indices.get(activity);values=[];missing=[]
    for tid in product_ids:
        recipe=catalog.recipes.get(tid)
        if not recipe:missing.append(tid);continue
        value=D(0)
        for material in recipe['materials']:
            adjusted=prices.get(str(material['typeID']))
            if adjusted is None:missing.append(material['typeID'])
            else:value+=D(adjusted)*material['quantity']
        values.append(value)
    base=sum(values,D(0))/len(values)*D('.02') if values else None
    complete=base is not None and index is not None and not missing
    rates={'system':D(index or 0)*(1-D(facility['job_cost_role'])/100),**{k:D(facility[field])/100 for k,field in [('facility','facility_tax'),('scc','scc_surcharge'),('alpha','alpha_surcharge')]}}
    parts={k:cents(base*runs*rate) for k,rate in rates.items()} if complete else None
    cost=sum((D(v)/100 for v in parts.values()),D(0)) if parts else None
    return {'cost':cost,'cents':cents(cost),'eiv_per_run':format(base,'f') if base is not None and not missing else None,
            'components':parts,'system_index':index,'system_id':facility['system_id'],'missing_prices':sorted(set(missing)),
            'complete':complete,'stale':any(r and r['data']['expires']<=industry.clock() for r in data.values())}


def compare(store,catalog,industry,config,quantity,quote_provider,manufacturing_prices,parameters=None,blueprints=None):
    config=validate(config,store,catalog);quantity=integer(quantity,'Mennyiség',10**6,1);tid=config['product_id'];recipe=catalog.inventions[tid]
    character=next((c for c in profiles(store,store.settings()) if c['id']==config['inventor_id']),None)
    skills=[{'id':s['typeID'],'name':catalog.name(s['typeID']),'required':s['level'],'active':(character or {}).get('levels',{}).get(s['typeID'],0)} for s in recipe['skills']]
    ready=bool(character and character['available'] and all(s['active']>=s['required'] for s in skills))
    copy_fee=fee(industry,catalog,[recipe['base_product_id']],'copying',config['copying'],config['copy_runs'])
    invention_fee=fee(industry,catalog,recipe['eiv_products'],'invention',config['invention'])
    copy_unit=copy_fee['cost']/config['copy_runs'] if copy_fee['cost'] is not None else None
    variants=[{'id':0,'name':'Nincs decryptor','probability_multiplier':1,'runs':0,'me':0,'te':0},*catalog.decryptors.values()]
    plans={};all_ids={m['typeID'] for m in recipe['materials']}|{v['id'] for v in variants if v['id']}
    settings=store.settings()
    for variant in variants:
        params=copy.deepcopy(parameters or {});params[tid]={'source':'manual','me':2+variant['me'],'te':4+variant['te'],'job_runs':recipe['runs']+variant['runs']}
        plan=Planner(catalog).calculate(tid,quantity,settings,parameters=params,blueprints=blueprints or [])
        mats=[{'id':r['id'],'quantity':(r['used_stock']+r['used_wip']) if r['runs'] else r['required']} for r in plan['rows'] if r['id']!=tid]
        mats=[m for m in mats if m['quantity']>0];all_ids.update(m['id'] for m in mats)
        formula=[] # Reusable BPOs/formulas are capital assets, not per-ship consumption.
        jobs=industry.estimate([{'id':r['id'],'batches':r['batches']} for r in plan['queue']],settings,catalog)
        plans[variant['id']]={'plan':plan,'materials':mats,'formulas':formula,'jobs':jobs}
    source,mode=config['prices'].split(':');ms,mm=manufacturing_prices.split(':')
    books={s:quote_provider(s,sorted(all_ids)) for s in set([source,ms])};rows=[]
    for variant in variants:
        p=chance(recipe,(character or {}).get('levels',{}),variant['probability_multiplier']) if ready else None
        runs=recipe['runs']+variant['runs'];consumables=[{'id':m['typeID'],'quantity':m['quantity']} for m in recipe['materials']]
        if variant['id']:consumables.append({'id':variant['id'],'quantity':1})
        materials,missing,stale=material_cost(consumables,books[source].get('quotes',{}),mode)
        attempt=materials+copy_unit+invention_fee['cost'] if materials is not None and copy_unit is not None and invention_fee['cost'] is not None else None
        per_run=attempt/p/runs if attempt is not None and p else None
        item_output=catalog.recipes[tid]['output'];per_item=per_run/item_output if per_run is not None else None
        production=plans[variant['id']];mfg,unpriced,mfg_stale=material_cost(production['materials']+production['formulas'],books[ms].get('quotes',{}),mm)
        job=D(production['jobs']['cents'])/100 if production['jobs']['complete'] else None
        mfg_total=mfg+job if mfg is not None and job is not None else None
        bpc_total=per_item*quantity if per_item is not None else None
        total=mfg_total+bpc_total if mfg_total is not None and bpc_total is not None else None
        rows.append({'decryptor_id':variant['id'],'name':variant['name'],'probability':format(p,'f') if p is not None else None,
            'me':2+variant['me'],'te':4+variant['te'],'runs_per_bpc':runs,
            'expected_successes':format(D(config['attempts'])*p,'f') if p is not None else None,
            'expected_runs':format(D(config['attempts'])*p*runs,'f') if p is not None else None,
            'attempt_cents':cents(attempt),'attempts_cents':cents(attempt*config['attempts']) if attempt is not None else None,
            'materials_cents':cents(materials),'copy_per_attempt_cents':cents(copy_unit),'invention_job_cents':invention_fee['cents'],
            'per_run_isk':format(per_run,'f') if per_run is not None else None,'per_item_isk':format(per_item,'f') if per_item is not None else None,
            'per_run_cents':cents(per_run),'bpc_total_cents':cents(bpc_total),'manufacturing_materials_cents':cents(mfg),
            'manufacturing_jobs_cents':cents(job),'total_cents':cents(total),'per_ship_cents':cents(total/quantity) if total is not None else None,
            'missing_prices':sorted(set(missing+unpriced)),'missing_jobs':not production['jobs']['complete'],'stale':stale or mfg_stale,
            'manufacturing_runs':next(r['runs'] for r in production['plan']['rows'] if r['id']==tid)})
    complete=[r for r in rows if r['total_cents'] is not None]
    best=min(complete,key=lambda r:int(r['total_cents']))['decryptor_id'] if complete else None
    for row in rows:row['saving_cents']=str(max(int(row['total_cents'])-min(int(r['total_cents']) for r in complete),0)) if row['total_cents'] is not None else None
    clean=lambda f:{k:v for k,v in f.items() if k!='cost'}
    return {'product_id':tid,'quantity':quantity,'config':config,'skills':skills,'character':{k:character.get(k) for k in ['id','name','available','as_of','stale']} if character else None,
            'skills_ready':ready,'rows':rows,'best_decryptor_id':best,'selected':next(r for r in rows if r['decryptor_id']==config['decryptor_id']),
            'copying':clean(copy_fee),'invention':clean(invention_fee),'price_ids':sorted(all_ids),'industry':industry.status(),
            'stale':bool(character and character['stale']) or copy_fee['stale'] or invention_fee['stale'] or any(r['stale'] for r in rows),'price_sources':sorted(set([source,ms])),'price_running':any(b.get('running') for b in books.values())}
