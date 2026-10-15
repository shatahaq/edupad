// Shared by Phaser, the editor, detail dialogs and the route validation tests.
export type Point = { x: number; y: number }
export type Rect = Point & { width: number; height: number }
export const WORLD = { width: 1448, height: 1086 }
export const BODY_RADIUS = 14
export const GRID = 8
export const LAYOUT_KEY = 'edupad-owl-furniture-v2'
export const INDEX_STATION: Point = { x: 1136, y: 916 }

export const ROOMS = [
  { id: 'command-center', label: 'Command Center', x: 84, y: 140, width: 388, height: 250, door: { x: 280, y: 424 }, home: { x: 280, y: 330 } },
  { id: 'research-lab', label: 'Research Lab', x: 534, y: 140, width: 378, height: 250, door: { x: 726, y: 424 }, home: { x: 726, y: 330 } },
  { id: 'tutor-room', label: 'Tutor Room', x: 970, y: 140, width: 390, height: 250, door: { x: 1164, y: 424 }, home: { x: 1164, y: 340 } },
  { id: 'planning-hub', label: 'Planning Hub', x: 84, y: 740, width: 278, height: 202, door: { x: 214, y: 688 }, home: { x: 220, y: 912 } },
  { id: 'analytics-room', label: 'Analytics Room', x: 424, y: 740, width: 278, height: 202, door: { x: 560, y: 688 }, home: { x: 558, y: 912 } },
  { id: 'finance-office', label: 'Finance Office', x: 758, y: 740, width: 270, height: 202, door: { x: 900, y: 688 }, home: { x: 900, y: 912 } },
  { id: 'knowledge-server', label: 'Knowledge Server', x: 1084, y: 740, width: 274, height: 202, door: { x: 1230, y: 688 }, home: { x: 1260, y: 922 } },
] as const

export const HOME_ROOM: Record<string, string> = {
  coordinator: 'command-center', researcher: 'research-lab', tutor: 'tutor-room',
  planner: 'planning-hub', analyst: 'analytics-room', finance: 'finance-office', keeper: 'knowledge-server',
}

// These strips match the visible wall/pillar footprints. Only actual doors are open.
export const WALLS: Rect[] = [
  { x: 0, y: 0, width: 1448, height: 142 },
  { x: 0, y: 946, width: 1448, height: 140 },
  { x: 0, y: 0, width: 86, height: 1086 },
  { x: 1360, y: 0, width: 88, height: 1086 },
  { x: 472, y: 100, width: 62, height: 315 },
  { x: 912, y: 100, width: 58, height: 315 },
  { x: 362, y: 690, width: 62, height: 280 },
  { x: 702, y: 690, width: 56, height: 280 },
  { x: 1028, y: 690, width: 56, height: 280 },
  ...[[0,244],[316,684],[766,1126],[1204,1448]].map(([left,right]) => ({ x: left, y: 392, width: right-left, height: 66 })),
  ...[[0,178],[250,522],[598,862],[942,1198],[1276,1448]].map(([left,right]) => ({ x: left, y: 648, width: right-left, height: 86 })),
]

export type FurnitureKind = {
  frame: number; name: string; description: string; width: number; ratio: number; category: string
}
export const FURNITURE: FurnitureKind[] = [
  { frame: 0, name: 'Konsol komando', description: 'Meja pusat koordinasi NOVA dengan tiga layar pemantauan.', width: 210, ratio: 186/343, category: 'Meja kerja' },
  { frame: 1, name: 'Meja riset', description: 'Tempat PIXEL menelaah dokumen dan menyiapkan materi kuliah.', width: 172, ratio: 163/246, category: 'Meja kerja' },
  { frame: 2, name: 'Meja tutor', description: 'Meja belajar dengan buku untuk penjelasan materi bersama SORA.', width: 174, ratio: 175/261, category: 'Meja kerja' },
  { frame: 3, name: 'Meja perencanaan', description: 'Meja TEMPO untuk menata jadwal dan prioritas tugas.', width: 146, ratio: 167/262, category: 'Meja kerja' },
  { frame: 4, name: 'Konsol analisis', description: 'Layar kerja METRIC untuk membaca perkembangan belajar.', width: 174, ratio: 196/341, category: 'Meja kerja' },
  { frame: 5, name: 'Meja keuangan', description: 'Meja KOIN dengan buku transaksi dan kalkulator anggaran.', width: 148, ratio: 182/280, category: 'Meja kerja' },
  { frame: 6, name: 'Rak server', description: 'Representasi penyimpanan pengetahuan EduPad. Menambah objek ini tidak menambah kapasitas server.', width: 44, ratio: 250/100, category: 'Perangkat' },
  { frame: 7, name: 'Terminal data', description: 'Workstation NEXUS untuk memantau sumber pengetahuan.', width: 96, ratio: 169/239, category: 'Meja kerja' },
  { frame: 8, name: 'Rak buku', description: 'Rak buku untuk melengkapi sudut belajar dan ruang riset.', width: 36, ratio: 252/117, category: 'Pelengkap' },
  { frame: 9, name: 'Tanaman', description: 'Tanaman kecil untuk memberi suasana nyaman tanpa memenuhi ruangan.', width: 35, ratio: 153/104, category: 'Pelengkap' },
  { frame: 10, name: 'Sofa santai', description: 'Sofa untuk sudut istirahat owl saat tidak ada pekerjaan.', width: 115, ratio: 168/271, category: 'Istirahat' },
  { frame: 11, name: 'Kursi kantor', description: 'Kursi terpisah yang dapat ditempatkan di area kosong.', width: 35, ratio: 184/129, category: 'Pelengkap' },
  { frame: 12, name: 'Papan belajar', description: 'Papan diagram untuk ruang tutor atau ruang diskusi.', width: 130, ratio: 179/269, category: 'Pelengkap' },
  { frame: 13, name: 'Dispenser', description: 'Sudut minum untuk jeda singkat di sela kegiatan belajar.', width: 35, ratio: 235/98, category: 'Istirahat' },
  { frame: 14, name: 'Taman kecil', description: 'Satu titik hijau di koridor dengan ruang berjalan di sekelilingnya.', width: 100, ratio: 227/303, category: 'Istirahat' },
  { frame: 15, name: 'Meja baca', description: 'Meja rendah untuk membaca santai saat tidak ada tugas.', width: 96, ratio: 147/247, category: 'Istirahat' },
]
export type FurnitureItem = { id: string; frame: number; x: number; y: number; owner?: string }
export const furnitureUrl = (frame: number) => `/assets/office/furniture-muted/${frame}.png`
export const DEFAULT_LAYOUT: FurnitureItem[] = [
  { id: 'nova-desk', frame: 0, x: 280, y: 238, owner: 'coordinator' },
  { id: 'pixel-desk', frame: 1, x: 726, y: 238, owner: 'researcher' },
  { id: 'sora-desk', frame: 2, x: 1164, y: 245, owner: 'tutor' },
  { id: 'tempo-desk', frame: 3, x: 220, y: 822, owner: 'planner' },
  { id: 'metric-desk', frame: 4, x: 558, y: 832, owner: 'analyst' },
  { id: 'koin-desk', frame: 5, x: 900, y: 820, owner: 'finance' },
  { id: 'nexus-desk', frame: 7, x: 1264, y: 846, owner: 'keeper' },
  { id: 'server-a', frame: 6, x: 1124, y: 826 },
  { id: 'server-b', frame: 6, x: 1180, y: 826 },
  { id: 'research-books', frame: 8, x: 578, y: 230 },
  { id: 'planning-books', frame: 8, x: 114, y: 808 },
  { id: 'lobby-tree', frame: 14, x: 724, y: 552 },
  { id: 'lobby-sofa', frame: 10, x: 350, y: 546 },
  { id: 'lobby-plant', frame: 9, x: 1000, y: 548 },
]

export function furnitureRect(item: FurnitureItem): Rect {
  const spec = FURNITURE[item.frame]
  return { x: item.x - spec.width/2, y: item.y - spec.width*spec.ratio/2, width: spec.width, height: spec.width*spec.ratio }
}
export function intersects(a: Rect, b: Rect, gap = 0) {
  return a.x < b.x+b.width+gap && a.x+a.width+gap > b.x && a.y < b.y+b.height+gap && a.y+a.height+gap > b.y
}
export function contains(rect: Rect, point: Point, margin = 0) {
  return point.x >= rect.x-margin && point.x <= rect.x+rect.width+margin && point.y >= rect.y-margin && point.y <= rect.y+rect.height+margin
}
export function roomAt(point: Point) { return ROOMS.find(room => contains(room, point)) }
export function workPoint(agentId: string, items: FurnitureItem[]): Point {
  const item = items.find(item => item.owner === agentId)
  if (item) return { x: item.x, y: item.y + FURNITURE[item.frame].width*FURNITURE[item.frame].ratio/2 + 36 }
  return ROOMS.find(room => room.id === HOME_ROOM[agentId])?.home ?? ROOMS[0].home
}

export class OfficeNavigator {
  readonly obstacles: Rect[]
  private cols = Math.floor(WORLD.width/GRID)
  private rows = Math.floor(WORLD.height/GRID)
  private blocked: Uint8Array
  constructor(items: FurnitureItem[]) {
    this.obstacles = [...WALLS, ...items.map(furnitureRect)]
    this.blocked = new Uint8Array(this.cols*this.rows)
    for(let y=0;y<this.rows;y++) for(let x=0;x<this.cols;x++) {
      if(!this.isFree({ x:x*GRID+GRID/2, y:y*GRID+GRID/2 })) this.blocked[y*this.cols+x] = 1
    }
  }
  isFree(point: Point) { return !this.obstacles.some(rect => contains(rect, point, BODY_RADIUS)) }
  segmentFree(from: Point, to: Point) {
    const steps = Math.max(1, Math.ceil(Math.hypot(to.x-from.x, to.y-from.y)/4))
    for(let i=0;i<=steps;i++) if(!this.isFree({ x:from.x+(to.x-from.x)*i/steps, y:from.y+(to.y-from.y)*i/steps })) return false
    return true
  }
  private point(index: number): Point { return { x:(index%this.cols)*GRID+GRID/2, y:Math.floor(index/this.cols)*GRID+GRID/2 } }
  private node(point: Point) {
    const cx=Math.floor(point.x/GRID), cy=Math.floor(point.y/GRID)
    let best=-1, distance=Infinity
    for(let y=cy-2;y<=cy+2;y++) for(let x=cx-2;x<=cx+2;x++) {
      if(x<0||y<0||x>=this.cols||y>=this.rows) continue
      const index=y*this.cols+x, target=this.point(index)
      const d=Math.hypot(point.x-target.x, point.y-target.y)
      if(!this.blocked[index] && d<distance && this.segmentFree(point,target)){ best=index;distance=d }
    }
    return best
  }
  findPath(from: Point, to: Point): Point[] | null {
    if(!this.isFree(from)||!this.isFree(to)) return null
    if(this.segmentFree(from,to)) return [to]
    const start=this.node(from), goal=this.node(to)
    if(start<0||goal<0) return null
    const size=this.blocked.length, scores=new Float64Array(size).fill(Infinity)
    const parent=new Int32Array(size).fill(-1), closed=new Uint8Array(size)
    const heap: { index:number; score:number }[]=[]
    const heuristic=(index:number)=>Math.abs(index%this.cols-goal%this.cols)+Math.abs(Math.floor(index/this.cols)-Math.floor(goal/this.cols))
    const push=(index:number,score:number)=>{
      heap.push({index,score}); let i=heap.length-1
      while(i>0){const p=(i-1)>>1;if(heap[p].score<=score)break;[heap[p],heap[i]]=[heap[i],heap[p]];i=p}
    }
    const pop=()=>{
      const result=heap[0],last=heap.pop()!
      if(heap.length){heap[0]=last;let i=0;while(true){let n=i;const a=i*2+1,b=a+1;if(a<heap.length&&heap[a].score<heap[n].score)n=a;if(b<heap.length&&heap[b].score<heap[n].score)n=b;if(n===i)break;[heap[i],heap[n]]=[heap[n],heap[i]];i=n}}
      return result.index
    }
    scores[start]=0;push(start,heuristic(start))
    while(heap.length){
      const current=pop();if(closed[current])continue
      if(current===goal){
        const path: Point[]=[to];let n=goal
        while(n!==start){path.push(this.point(n));n=parent[n]}
        path.push(this.point(start));path.push(from);path.reverse()
        const simplified:Point[]=[];let anchor=0
        while(anchor<path.length-1){let end=anchor+1;while(end+1<path.length&&this.segmentFree(path[anchor],path[end+1]))end++;simplified.push(path[end]);anchor=end}
        return simplified
      }
      closed[current]=1
      const x=current%this.cols, y=Math.floor(current/this.cols)
      for(const [nx,ny] of [[x-1,y],[x+1,y],[x,y-1],[x,y+1]]){
        if(nx<0||ny<0||nx>=this.cols||ny>=this.rows)continue
        const next=ny*this.cols+nx
        if(this.blocked[next]||closed[next]||scores[current]+1>=scores[next])continue
        scores[next]=scores[current]+1;parent[next]=current;push(next,scores[next]+heuristic(next))
      }
    }
    return null
  }
}

function placementGeometryError(item: FurnitureItem, others: FurnitureItem[], agents: Point[] = []): string | null {
  if(!Number.isInteger(item.frame)||!FURNITURE[item.frame]||!Number.isFinite(item.x)||!Number.isFinite(item.y)) return 'Objek tidak valid.'
  const rect=furnitureRect(item)
  if(WALLS.some(wall=>intersects(rect,wall,2)))return 'Sisakan jarak dari tembok.'
  if(others.some(other=>other.id!==item.id&&intersects(rect,furnitureRect(other),4)))return 'Posisi ini bertumpuk dengan furnitur lain.'
  if(ROOMS.some(room=>intersects(rect,{x:room.door.x-42,y:room.door.y-74,width:84,height:148})))return 'Area pintu harus tetap kosong.'
  if(agents.some(point=>contains(rect,point,BODY_RADIUS+4)))return 'Ada owl di posisi ini. Pilih tempat lain.'
  if(item.owner){const room=roomAt(item);if(room?.id!==HOME_ROOM[item.owner])return 'Meja utama tetap berada di ruangan pemiliknya.'}
  return null
}

export function validatePlacement(item: FurnitureItem, others: FurnitureItem[], agents: Point[] = []): string | null {
  const geometryError=placementGeometryError(item,others,agents)
  if(geometryError)return geometryError
  const layout=[...others.filter(other=>other.id!==item.id),item],nav=new OfficeNavigator(layout)
  const hub={x:600,y:540}
  for(const agentId of Object.keys(HOME_ROOM)) if(!nav.findPath(hub,workPoint(agentId,layout)))return 'Posisi ini menutup jalur menuju meja kerja.'
  if(!nav.findPath(hub,INDEX_STATION))return 'Posisi ini menutup jalur menuju tempat indexing.'
  for(const point of agents) if(!nav.findPath(point,hub))return 'Posisi ini mengurung owl yang sedang berada di kantor.'
  return null
}

// Let the user choose any floor area; when a click lands on an obstacle, find the
// closest usable 8px position instead of forcing them to guess the collision box.
export function resolvePlacement(item: FurnitureItem, others: FurnitureItem[], agents: Point[] = []) {
  const originalError=validatePlacement(item,others,agents)
  if(!originalError)return {item,adjusted:false,error:null}
  if(originalError==='Objek tidak valid.')return {item:null,adjusted:false,error:originalError}
  const candidates: Array<{x:number;y:number;distance:number}>=[]
  for(let dy=-20;dy<=20;dy++)for(let dx=-20;dx<=20;dx++){
    if(dx===0&&dy===0)continue
    const x=item.x+dx*GRID,y=item.y+dy*GRID
    if(x<0||x>WORLD.width||y<0||y>WORLD.height)continue
    candidates.push({x,y,distance:dx*dx+dy*dy})
  }
  candidates.sort((a,b)=>a.distance-b.distance)
  let routeChecks=0
  for(const candidate of candidates){
    const next={...item,x:candidate.x,y:candidate.y}
    if(placementGeometryError(next,others,agents))continue
    if(!validatePlacement(next,others,agents))return {item:next,adjusted:true,error:null}
    if(++routeChecks>=24)break
  }
  return {item:null,adjusted:false,error:'Tidak ada ruang aman di dekat titik ini. Coba area lantai lain.'}
}

export function loadLayout(): FurnitureItem[] {
  try {
    const raw=JSON.parse(localStorage.getItem(LAYOUT_KEY)??'null')
    if(Array.isArray(raw)&&raw.length<=80&&raw.every(item=>item&&typeof item.id==='string'&&Number.isInteger(item.frame)&&FURNITURE[item.frame]&&Number.isFinite(item.x)&&Number.isFinite(item.y)&&(!item.owner||HOME_ROOM[item.owner]))){
      if(new Set(raw.map(item=>item.id)).size!==raw.length)return structuredClone(DEFAULT_LAYOUT)
      if(raw.every(item=>!validatePlacement(item,raw)))return raw
    }
  } catch { /* Storage can be disabled; the default layout remains usable. */ }
  return structuredClone(DEFAULT_LAYOUT)
}
