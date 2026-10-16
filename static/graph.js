/* A dependency graph of the already calculated, net production plan. */
(function (root) {
  'use strict';
  const CARD_W=260, CARD_H=150, GAP_X=90, GAP_Y=28, PAD=28, HEAD=48;
  function build(plan, options={}) {
    const nodes=plan.rows.filter(r=>r.required>0 &&
      (r.runs>0 || (options.purchases && r.buy>0) ||
       (options.covered && !r.runs && !r.buy && (r.activity!=='buy' || options.purchases))))
      .map(r=>({...r, kind:r.runs?r.activity:r.buy?'buy':'covered'}));
    const byId=new Map(nodes.map(n=>[n.id,n])), edges=[];
    for(const parent of nodes) for(const material of parent.materials || []) {
      if(material.quantity>0 && byId.has(material.id))
        edges.push({from:material.id,to:parent.id,quantity:material.quantity});
    }
    const stages=[...new Set(nodes.map(n=>n.stage))].sort((a,b)=>a-b);
    const layers=stages.map(stage=>nodes.filter(n=>n.stage===stage).sort((a,b)=>a.name.localeCompare(b.name,'hu')));
    const links=new Map(nodes.map(n=>[n.id,{before:[],after:[]}]));
    for(const edge of edges) {
      links.get(edge.to).before.push(edge.from);
      links.get(edge.from).after.push(edge.to);
    }
    // Shared ingredients appear once; order each column to reduce crossings.
    for(let sweep=0;sweep<6;sweep++) {
      const positions=new Map(layers.flatMap(layer=>layer.map((n,i)=>[n.id,(i+.5)/layer.length])));
      const direction=sweep%2?'before':'after';
      for(const layer of layers) {
        const score=n=>{
          const adjacent=links.get(n.id)[direction];
          return adjacent.length?adjacent.reduce((sum,id)=>sum+positions.get(id),0)/adjacent.length:positions.get(n.id);
        };
        layer.sort((a,b)=>score(a)-score(b)||a.name.localeCompare(b.name,'hu'));
      }
    }
    const height=PAD*2+HEAD+Math.max(1,...layers.map(l=>l.length))*(CARD_H+GAP_Y)-GAP_Y;
    layers.forEach((layer,col)=>{
      const top=PAD+HEAD+(height-PAD*2-HEAD-(layer.length*(CARD_H+GAP_Y)-GAP_Y))/2;
      layer.forEach((n,i)=>Object.assign(n,{x:PAD+col*(CARD_W+GAP_X),y:top+i*(CARD_H+GAP_Y),width:CARD_W,height:CARD_H}));
    });
    return {nodes,edges,layers:layers.map((layer,i)=>({stage:stages[i],x:PAD+i*(CARD_W+GAP_X),count:layer.length})),
      width:PAD*2+Math.max(1,layers.length)*CARD_W+Math.max(0,layers.length-1)*GAP_X,height};
  }
  function branch(graph,id) {
    const result=new Set([id]);
    // Traverse each direction independently: siblings of an ancestor are not
    // dependencies of the selected product, even if they share its raw input.
    for(const direction of ['from','to']) {
      const seen=new Set([id]), pending=[id];
      while(pending.length) {
        const current=pending.pop();
        for(const edge of graph.edges) {
          if(edge[direction]!==current)continue;
          const next=edge[direction==='from'?'to':'from'];
          if(!seen.has(next)){seen.add(next);result.add(next);pending.push(next);}
        }
      }
    }
    return result;
  }
  function path(graph,edge) {
    const a=graph.nodes.find(n=>n.id===edge.from), b=graph.nodes.find(n=>n.id===edge.to);
    const x1=a.x+a.width,y1=a.y+a.height/2,x2=b.x,y2=b.y+b.height/2;
    const bend=Math.max(35,(x2-x1)*.45);
    return `M ${x1} ${y1} C ${x1+bend} ${y1}, ${x2-bend} ${y2}, ${x2} ${y2}`;
  }
  function wrap(name,limit=29) {
    const lines=[''];
    for(const word of String(name).split(/\s+/)) {
      const i=lines.length-1;
      if(lines[i] && (lines[i]+' '+word).length>limit)lines.push(word);
      else lines[i]+=(lines[i]?' ':'')+word;
    }
    const clipped=line=>line.length>limit?line.slice(0,limit-1)+'…':line;
    if(lines.length>2)return [clipped(lines[0]),clipped(lines.slice(1).join(' '))];
    return lines.map(clipped);
  }
  const api={build,branch,path,wrap};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.EvePlanGraph=api;
})(typeof window!=='undefined'?window:globalThis);
