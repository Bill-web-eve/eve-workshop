'use strict';
// Deterministic local topology layout; edges are CCP stargates, never inferred links.
const EveIntelMap=(()=>{
  function layout(nodes){
    if(!nodes.length)return [];
    const minX=Math.min(...nodes.map(n=>n.x)),maxX=Math.max(...nodes.map(n=>n.x)),minY=Math.min(...nodes.map(n=>n.y)),maxY=Math.max(...nodes.map(n=>n.y));
    const scale=Math.min(1050/Math.max(.01,maxX-minX),540/Math.max(.01,maxY-minY));
    const rows=nodes.map((n,index)=>({...n,lx:80+(n.x-minX)*scale,ly:75+(n.y-minY)*scale,index})).sort((a,b)=>a.id-b.id);
    // Keep the public map projection recognizable while separating labels.
    for(let pass=0;pass<35;pass++)for(let i=0;i<rows.length;i++)for(let j=i+1;j<rows.length;j++){
      const a=rows[i],b=rows[j],dx=b.lx-a.lx,dy=b.ly-a.ly;
      if(Math.abs(dx)<95&&Math.abs(dy)<30){const sign=dy===0?(i%2?1:-1):Math.sign(dy),move=(30-Math.abs(dy))*.26;a.ly-=sign*move;b.ly+=sign*move;}
    }
    const low=Math.min(...rows.map(n=>n.ly)),high=Math.max(...rows.map(n=>n.ly));
    for(const row of rows)row.ly=60+(row.ly-low)*Math.min(1,590/Math.max(1,high-low));
    return rows;
  }
  return {layout};
})();
globalThis.EveIntelMap=EveIntelMap;if(typeof module!=='undefined'&&module.exports)module.exports=EveIntelMap;
