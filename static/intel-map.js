'use strict';
// Deterministic local topology layout; edges are CCP stargates, never inferred links.
const EveIntelMap=(()=>{
  function layout(nodes,{width=1200,height=720}={}){
    if(!nodes.length)return [];
    const minX=Math.min(...nodes.map(n=>n.x)),maxX=Math.max(...nodes.map(n=>n.x)),minY=Math.min(...nodes.map(n=>n.y)),maxY=Math.max(...nodes.map(n=>n.y));
    // Schematic placement stays near the CCP projection while keeping system labels apart.
    const columns=Math.max(2,Math.floor((width-100)/72)),rows=Math.max(2,Math.floor((height-70)/20),Math.ceil(nodes.length/columns)),slots=[];
    for(let y=0;y<rows;y++)for(let x=0;x<columns;x++)slots.push({x:50+x*(width-130)/(columns-1),y:35+y*(height-75)/(rows-1)});
    const result=[];
    for(const node of [...nodes].sort((a,b)=>a.id-b.id)){
      const x=50+(node.x-minX)/Math.max(.001,maxX-minX)*(width-130),y=35+(node.y-minY)/Math.max(.001,maxY-minY)*(height-75);
      let best=0,cost=Infinity;for(let i=0;i<slots.length;i++){const d=(slots[i].x-x)**2+(slots[i].y-y)**2;if(d<cost){best=i;cost=d;}}
      const slot=slots.splice(best,1)[0];result.push({...node,lx:slot.x,ly:slot.y});
    }
    return result;
  }
  function callouts(nodes,{width:viewWidth=1200,height:viewHeight=720}={}){
    const cards=[],overlap=(a,b)=>Math.max(0,Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x))*Math.max(0,Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y));
    for(const node of [...nodes].filter(n=>n.contacts?.length||n.kill_groups?.length).sort((a,b)=>Math.max(b.reported_at||0,...(b.kill_groups||[]).map(g=>g.received))-Math.max(a.reported_at||0,...(a.kill_groups||[]).map(g=>g.received))||a.id-b.id)){
      const width=190,height=Math.min(viewHeight-15,180,28+(node.contacts||[]).reduce((sum,r)=>sum+19+Math.max(1,r.pilots.length)*14+((r.ships||[]).length?22*Math.ceil(r.ships.length/2):0)+(r.pilots.length>1&&(r.ships||[]).length?12:0),0)+(node.kill_groups?.length?105:0));
      const offsets=[[20,-20],[-width-20,-20],[15,25],[15,-height-20],[-width-20,25],[-width-20,-height-20]];
      const candidates=offsets.map(([x,y])=>({node,x:Math.max(4,Math.min(viewWidth-10-width,node.lx+x)),y:Math.max(4,Math.min(viewHeight-10-height,node.ly+y)),width,height}));
      const cost=box=>cards.reduce((s,c)=>s+overlap(box,c)*3,0)+nodes.filter(n=>n.id!==node.id).reduce((s,n)=>s+overlap(box,{x:n.lx-8,y:n.ly-10,width:95,height:30}),0);
      candidates.sort((a,b)=>cost(a)-cost(b));cards.push(candidates[0]);
    }
    return cards;
  }
  return {layout,callouts};
})();
globalThis.EveIntelMap=EveIntelMap;if(typeof module!=='undefined'&&module.exports)module.exports=EveIntelMap;
