'use strict';
// A common time axis keeps independent reaction/manufacturing slots comparable.
const EveScheduleGraph=(()=>{
  const PAGE_SIZE=100;
  function related(data,selected){
    const before=new Map(),after=new Map();
    for(const job of data.jobs)for(const dep of job.dependencies||[]){
      if(!before.has(job.id))before.set(job.id,[]);before.get(job.id).push(dep.job_id);
      if(!after.has(dep.job_id))after.set(dep.job_id,[]);after.get(dep.job_id).push(job.id);
    }
    const result=new Set(selected===null?[]:[selected]);
    for(const adjacency of [before,after]){
      const pending=selected===null?[]:[selected],seen=new Set(pending);
      while(pending.length)for(const next of adjacency.get(pending.pop())||[])if(!seen.has(next)){seen.add(next);result.add(next);pending.push(next);}
    }
    return result;
  }
  function flow(data,layout=globalThis.EvePlanGraph){
    const products=new Map(),jobs=new Map(data.jobs.map(j=>[j.id,j])),edges=new Map();
    for(const j of data.jobs){
      if(!products.has(j.product_id))products.set(j.product_id,{id:j.product_id,name:j.name,activity:j.activity,required:0,runs:0,manufactured:0,stage:1,materials:[],job_ids:[],start:j.start,end:j.end});
      const n=products.get(j.product_id);n.runs+=j.runs;n.manufactured+=j.output;n.required+=j.output;n.job_ids.push(j.id);n.start=Math.min(n.start,j.start);n.end=Math.max(n.end,j.end);
      if(n.select_job===undefined||!jobs.get(n.select_job).dependencies?.length&&j.dependencies?.length)n.select_job=j.id;
    }
    for(const j of data.jobs)for(const dep of j.dependencies||[]){
      const producer=jobs.get(dep.job_id);if(!producer)continue;
      const key=producer.product_id+':'+j.product_id;
      if(!edges.has(key))edges.set(key,{from:producer.product_id,to:j.product_id,quantity:0,job_links:0});
      const edge=edges.get(key);edge.quantity+=dep.quantity;edge.job_links++;
    }
    const incoming=new Map([...products.keys()].map(id=>[id,0])),outgoing=new Map();
    for(const edge of edges.values()){
      products.get(edge.to).materials.push({id:edge.from,quantity:edge.quantity});incoming.set(edge.to,incoming.get(edge.to)+1);
      if(!outgoing.has(edge.from))outgoing.set(edge.from,[]);outgoing.get(edge.from).push(edge.to);
    }
    const roots=[...products.keys()].filter(id=>incoming.get(id)===0);
    for(let i=0;i<roots.length;i++)for(const next of outgoing.get(roots[i])||[]){
      products.get(next).stage=Math.max(products.get(next).stage,products.get(roots[i]).stage+1);
      incoming.set(next,incoming.get(next)-1);if(incoming.get(next)===0)roots.push(next);
    }
    const result=layout.build({rows:[...products.values()]});
    result.edges=result.edges.map(e=>({...e,job_links:edges.get(e.from+':'+e.to).job_links}));
    return result;
  }
  function build(data,page=0,selected=null){
    const all=data.jobs,pages=Math.max(1,Math.ceil(all.length/PAGE_SIZE));
    page=Math.max(0,Math.min(pages-1,page));
    const jobs=all.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE),laneMap=new Map();
    for(const j of jobs){const key=[j.activity,j.character_id,j.slot].join(':');if(!laneMap.has(key))laneMap.set(key,{key,activity:j.activity,character_id:j.character_id,name:j.character_name,slot:j.slot});}
    const lanes=[...laneMap.values()].sort((a,b)=>(a.activity==='reaction'?0:1)-(b.activity==='reaction'?0:1)||a.character_id-b.character_id||a.slot-b.slot);
    lanes.forEach((l,i)=>{l.y=65+i*38;});
    const start=data.start,end=Math.max(start+1,data.partial_finish||start,...all.map(j=>j.end)),left=240,width=1320,scale=(width-left-30)/(end-start),byId=new Map();
    const nodes=jobs.map(j=>{const lane=laneMap.get([j.activity,j.character_id,j.slot].join(':'));const n={...j,x:left+(j.start-start)*scale,y:lane.y,width:Math.max(2,(j.end-j.start)*scale)};byId.set(j.id,n);return n;});
    const links=[],branch=related(data,selected);
    for(const job of all)for(const dep of job.dependencies||[]){
      const a=byId.get(dep.job_id),b=byId.get(job.id);
      if(a&&b)links.push({...dep,from:a.id,to:b.id,highlight:branch.has(a.id)&&branch.has(b.id),path:`M ${a.x+a.width} ${a.y+12} C ${a.x+a.width+14} ${a.y+12}, ${b.x-14} ${b.y+12}, ${b.x} ${b.y+12}`});
    }
    return {nodes,lanes,links,width,height:Math.max(120,lanes.length*38+85),page,pages,start,end,left,
      ticks:Array.from({length:5},(_,i)=>({x:left+(width-left-30)*i/4,time:start+(end-start)*i/4}))};
  }
  return {build,flow,related,PAGE_SIZE};
})();
globalThis.EveScheduleGraph=EveScheduleGraph;
if(typeof module!=='undefined'&&module.exports)module.exports=EveScheduleGraph;
