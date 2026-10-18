'use strict';
// A common time axis keeps independent reaction/manufacturing slots comparable.
const EveScheduleGraph=(()=>{
  const PAGE_SIZE=100,DAY=86400,DEFAULT_DAYS=7,MAX_DAYS=3650;
  const validDays=value=>value===null||(Number.isInteger(value)&&value>=1&&value<=MAX_DAYS);
  const allJobs=data=>[...(data.running_jobs||[]),...data.jobs];
  function range(data,viewport={}){
    const fullStart=data.running_jobs?.length?Math.min(data.start,data.calculated_at??data.start):data.start,fullEnd=Math.max(fullStart+1,data.partial_finish||fullStart,...allJobs(data).map(j=>j.end));
    const days=validDays(viewport.days)?viewport.days:null;
    const span=days?days*DAY:fullEnd-fullStart,windows=Math.max(1,Math.ceil((fullEnd-fullStart)/span));
    const window=Math.max(0,Math.min(windows-1,Number.isInteger(viewport.window)?viewport.window:0));
    const start=fullStart+window*span,end=Math.min(fullEnd,start+span);
    return {fullStart,fullEnd,days,window,windows,start,end};
  }
  function visibleJobs(data,characterId=null,viewport={}){
    const {start,end}=range(data,viewport);
    return allJobs(data).filter(j=>(characterId===null||j.character_id===characterId)&&j.end>start&&j.start<end);
  }
  function build(data,page=0,characterId=null,viewport={}){
    const bounds=range(data,viewport),filtered=visibleJobs(data,characterId,viewport),pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));
    page=Math.max(0,Math.min(pages-1,page));
    const jobs=filtered.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE),laneMap=new Map();
    for(const j of jobs){const key=[j.activity,j.character_id,j.existing?'eve':'plan',j.slot].join(':');if(!laneMap.has(key))laneMap.set(key,{key,activity:j.activity,character_id:j.character_id,name:j.character_name,slot:j.slot,existing:!!j.existing});}
    const lanes=[...laneMap.values()].sort((a,b)=>(a.activity==='reaction'?0:1)-(b.activity==='reaction'?0:1)||a.character_id-b.character_id||Number(b.existing)-Number(a.existing)||a.slot-b.slot);
    lanes.forEach((l,i)=>{l.y=65+i*38;});
    const {start,end}=bounds,left=240,width=1320,scale=(width-left-30)/(end-start);
    const nodes=jobs.map(j=>{
      const lane=laneMap.get([j.activity,j.character_id,j.existing?'eve':'plan',j.slot].join(':')),visibleStart=Math.max(start,j.start),visibleEnd=Math.min(end,j.end);
      const x=left+(visibleStart-start)*scale;
      return {...j,x,y:lane.y,width:Math.min(width-30-x,Math.max(2,(visibleEnd-visibleStart)*scale)),continues_before:j.start<start,continues_after:j.end>end};
    });
    return {...bounds,nodes,lanes,width,height:Math.max(120,lanes.length*38+85),page,pages,left,total_jobs:filtered.length,
      ticks:Array.from({length:5},(_,i)=>({x:left+(width-left-30)*i/4,time:start+(end-start)*i/4}))};
  }
  return {build,range,visibleJobs,allJobs,validDays,PAGE_SIZE,DAY,DEFAULT_DAYS,MAX_DAYS};
})();
globalThis.EveScheduleGraph=EveScheduleGraph;
if(typeof module!=='undefined'&&module.exports)module.exports=EveScheduleGraph;
