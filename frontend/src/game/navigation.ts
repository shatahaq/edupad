import type { Point } from './workstations'

// Ordered from the walkable interior of each room to the shared main corridor.
// Routes deliberately use right-angle turns at doorway thresholds so agents never
// take a diagonal shortcut through a wall or pillar.
const ROOM_TO_CORRIDOR: Record<string, Point[]> = {
  'command-center': [
    { x: 260, y: 232 },
    { x: 260, y: 278 },
    { x: 260, y: 322 },
  ],
  'research-lab': [
    { x: 580, y: 220 },
    { x: 580, y: 278 },
    { x: 580, y: 322 },
  ],
  'tutor-room': [
    { x: 680, y: 232 },
    { x: 680, y: 278 },
    { x: 680, y: 322 },
  ],
  'planning-hub': [
    { x: 240, y: 548 },
    { x: 240, y: 420 },
    { x: 260, y: 420 },
    { x: 260, y: 382 },
    { x: 260, y: 322 },
  ],
  'analytics-room': [
    { x: 440, y: 548 },
    { x: 440, y: 452 },
    { x: 410, y: 452 },
    { x: 390, y: 452 },
    { x: 390, y: 322 },
  ],
  'knowledge-server': [
    { x: 738, y: 548 },
    { x: 716, y: 548 },
    { x: 690, y: 548 },
    { x: 690, y: 322 },
  ],
}

export const IDLE_PATROLS: Record<string, Point[]> = {
  'command-center': [
    { x: 220, y: 220 }, { x: 260, y: 220 }, { x: 260, y: 278 },
    { x: 260, y: 322 }, { x: 330, y: 322 }, { x: 390, y: 322 },
    { x: 390, y: 350 }, { x: 330, y: 350 }, { x: 330, y: 322 },
    { x: 260, y: 322 }, { x: 260, y: 278 }, { x: 260, y: 220 },
    { x: 168, y: 218 },
  ],
  'research-lab': [
    { x: 520, y: 220 }, { x: 580, y: 220 }, { x: 580, y: 278 },
    { x: 580, y: 322 }, { x: 630, y: 322 }, { x: 630, y: 350 },
    { x: 580, y: 350 }, { x: 580, y: 322 }, { x: 580, y: 278 },
    { x: 580, y: 220 }, { x: 480, y: 218 },
  ],
  'tutor-room': [
    { x: 730, y: 220 }, { x: 680, y: 220 }, { x: 680, y: 278 },
    { x: 680, y: 322 }, { x: 740, y: 322 }, { x: 810, y: 322 },
    { x: 810, y: 350 }, { x: 730, y: 350 }, { x: 680, y: 322 },
    { x: 680, y: 278 }, { x: 680, y: 220 }, { x: 792, y: 218 },
  ],
  'planning-hub': [
    { x: 220, y: 548 }, { x: 240, y: 548 }, { x: 240, y: 420 },
    { x: 260, y: 420 },
    { x: 260, y: 382 }, { x: 260, y: 322 }, { x: 330, y: 322 },
    { x: 390, y: 322 }, { x: 390, y: 350 }, { x: 330, y: 350 },
    { x: 260, y: 322 }, { x: 260, y: 382 }, { x: 260, y: 420 },
    { x: 240, y: 420 }, { x: 240, y: 548 }, { x: 220, y: 548 },
    { x: 168, y: 548 },
  ],
  'analytics-room': [
    { x: 440, y: 548 }, { x: 440, y: 452 }, { x: 410, y: 452 },
    { x: 390, y: 452 }, { x: 390, y: 322 }, { x: 340, y: 322 },
    { x: 340, y: 350 }, { x: 390, y: 350 }, { x: 390, y: 452 },
    { x: 410, y: 452 }, { x: 440, y: 452 }, { x: 440, y: 548 },
    { x: 480, y: 548 },
  ],
  'knowledge-server': [
    { x: 738, y: 548 }, { x: 716, y: 548 }, { x: 690, y: 548 },
    { x: 690, y: 322 }, { x: 620, y: 322 }, { x: 570, y: 322 },
    { x: 570, y: 350 }, { x: 620, y: 350 }, { x: 690, y: 322 },
    { x: 690, y: 548 }, { x: 716, y: 548 }, { x: 738, y: 548 },
    { x: 792, y: 548 },
  ],
}

const corridorBridge = (from: Point, to: Point): Point[] => {
  const crossesCenter =
    (from.x < 420 && to.x > 540) || (from.x > 540 && to.x < 420)
  if (!crossesCenter) return [to]
  return [
    { x: from.x, y: 245 },
    { x: to.x, y: 245 },
    to,
  ]
}

export function routeBetweenRooms(fromRoom: string, toRoom: string): Point[] {
  if (fromRoom === toRoom) return []
  const exit = ROOM_TO_CORRIDOR[fromRoom]
  const entry = ROOM_TO_CORRIDOR[toRoom]
  if (!exit || !entry) return []

  const route = [...exit]
  const exitHub = exit[exit.length - 1]
  const entryHub = entry[entry.length - 1]
  if (exitHub.x !== entryHub.x || exitHub.y !== entryHub.y) {
    route.push(...corridorBridge(exitHub, entryHub))
  }
  route.push(...entry.slice(0, -1).reverse())
  return route
}

export function routeFromCorridor(position: Point, toRoom: string): Point[] {
  const entry = ROOM_TO_CORRIDOR[toRoom]
  if (!entry) return []
  const entryHub = entry[entry.length - 1]
  const route: Point[] = []
  const currentHub = { x: position.x, y: 322 }
  if (Math.abs(position.y - 322) > 5) route.push(currentHub)
  route.push(...corridorBridge(currentHub, entryHub))
  route.push(...entry.slice(0, -1).reverse())
  return route
}
