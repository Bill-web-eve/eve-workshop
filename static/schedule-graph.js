'use strict';
// A common time axis keeps independent reaction/manufacturing slots comparable.
const EveScheduleGraph=(()=>{
  const PAGE_SIZE=100;
  function build(data,page=0){
    const all=data.jobs,pages=Math.max(1,Math.ceil(all.length/PAGE_SIZE));
    page=Math.max(0,Math.min(pages-1,page));
    const jobs=all.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE),laneMap=new Map();
    for(const j of jobs){const key=[j.activity,j.character_id,j.slot].join(':');if(!laneMap.has(key))laneMap.set(key,{key,activity:j.activity,character_id:j.character_id,name:j.character_name,slot:j.slot});}
    const lanes=[...laneMap.values()].sort((a,b)=>(a.activity==='reaction'?0:1)-(b.activity==='reaction'?0:1)||a.character_id-b.character_id||a.slot-b.slot);
    lanes.forEach((l,i)=>{l.y=65+i*38;});
    const start=data.start,end=Math.max(start+1,data.partial_finish||start,...all.map(j=>j.end)),left=240,width=1320,scale=(width-left-30)/(end-start);
    const nodes=jobs.map(j=>{const lane=laneMap.get([j.activity,j.character_id,j.slot].join(':'));const n={...j,x:left+(j.start-start)*scale,y:lane.y,width:Math.max(2,(j.end-j.start)*scale)};return n;});
    return {nodes,lanes,width,height:Math.max(120,lanes.length*38+85),page,pages,start,end,left,
      ticks:Array.from({length:5},(_,i)=>({x:left+(width-left-30)*i/4,time:start+(end-start)*i/4}))};
  }
  return {build,PAGE_SIZE};
})();
globalThis.EveScheduleGraph=EveScheduleGraph;
if(typeof module!=='undefined'&&module.exports)module.exports=EveScheduleGraph;
