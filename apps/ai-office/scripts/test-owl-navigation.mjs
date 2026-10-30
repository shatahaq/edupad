import assert from 'node:assert/strict'
import { DEFAULT_LAYOUT, HOME_ROOM, OfficeNavigator, resolvePlacement, validatePlacement, workPoint, WALLS, ROOMS } from '../src/game/owlLayout.ts'

const nav=new OfficeNavigator(DEFAULT_LAYOUT)
for(const item of DEFAULT_LAYOUT) assert.equal(validatePlacement(item,DEFAULT_LAYOUT),null,item.id)
const agents=Object.keys(HOME_ROOM)
let count=0
for(const fromId of agents)for(const toId of agents){
  const start=workPoint(fromId,DEFAULT_LAYOUT),end=workPoint(toId,DEFAULT_LAYOUT)
  const path=nav.findPath(start,end)
  assert.ok(path,`${fromId} must reach ${toId}`)
  let current=start
  for(const point of path){assert.ok(nav.segmentFree(current,point),`${fromId}/${toId}: unsafe segment`);current=point}
  count++
}
const indexingPath=nav.findPath(workPoint('researcher',DEFAULT_LAYOUT),{x:1136,y:916})
assert.ok(indexingPath,'PIXEL must reach the Knowledge Server indexing station')
let indexingPoint=workPoint('researcher',DEFAULT_LAYOUT)
for(const next of indexingPath){assert.ok(nav.segmentFree(indexingPoint,next),'PIXEL indexing path crosses an obstacle');indexingPoint=next}
for(const wall of WALLS)assert.equal(nav.isFree({x:wall.x+wall.width/2,y:wall.y+wall.height/2}),false)
for(const room of ROOMS)assert.equal(nav.isFree(room.door),true,`${room.id} door is open`)
assert.match(validatePlacement({id:'blocked-door',frame:10,x:280,y:424},DEFAULT_LAYOUT),/pintu|tembok/)
assert.match(validatePlacement({id:'overlap',frame:1,x:280,y:238},DEFAULT_LAYOUT),/bertumpuk/)
assert.match(validatePlacement({id:'wall',frame:9,x:500,y:250},DEFAULT_LAYOUT),/tembok/)
assert.match(validatePlacement({id:'blocked-index',frame:9,x:1136,y:916},DEFAULT_LAYOUT),/indexing/)
const snapped=resolvePlacement({id:'near-wall',frame:9,x:496,y:248},DEFAULT_LAYOUT)
assert.ok(snapped.item&&snapped.adjusted,'Nearby floor is offered for a wall click')
assert.equal(validatePlacement(snapped.item,DEFAULT_LAYOUT),null,'Auto-placement keeps owl routes open')
assert.equal(validatePlacement({id:'safe-added',frame:9,x:950,y:550},DEFAULT_LAYOUT),null)
const changed=[...DEFAULT_LAYOUT,{id:'new-sofa',frame:10,x:900,y:540}]
assert.equal(validatePlacement(changed.at(-1),DEFAULT_LAYOUT),null)
const rerouted=new OfficeNavigator(changed),start={x:800,y:540},end={x:1080,y:540}
assert.equal(rerouted.segmentFree(start,end),false)
const path=rerouted.findPath(start,end)
assert.ok(path&&path.length>1,'Added sofa causes a detour')
let point=start
for(const next of path){assert.ok(rerouted.segmentFree(point,next));point=next}
assert.equal(rerouted.findPath({x:900,y:540},end),null,'No teleport from blocked furniture')
const patrolBlock=[...DEFAULT_LAYOUT,{id:'patrol-sofa',frame:10,x:160,y:510}]
assert.equal(validatePlacement(patrolBlock.at(-1),DEFAULT_LAYOUT),null,'Patrol furniture does not block work routes')
const patrolNav=new OfficeNavigator(patrolBlock)
assert.equal(patrolNav.findPath(workPoint('coordinator',patrolBlock),{x:160,y:510}),null,'Covered patrol point is skipped')
assert.ok(patrolNav.findPath(workPoint('coordinator',patrolBlock),{x:520,y:570}),'Alternative patrol point remains open')
console.log(`PASS: ${count} inter-room routes, doors, wall clearance, furniture overlap, live detour and blocked-start checks`)
