export type WallOccluder = {
  id: string
  x: number
  y: number
  width: number
  height: number
  depth: number
}

// Each entry reveals only one depth band from the full-size transparent wall layer.
// Splitting vertical structures keeps the usual top-down rule: lower Y renders in front.
export const WALL_OCCLUDERS: WallOccluder[] = [
  { id: 'north-frame', x: 0, y: 0, width: 960, height: 58, depth: 58 },
  { id: 'top-room-fronts', x: 0, y: 220, width: 960, height: 72, depth: 282 },
  { id: 'south-room-fronts', x: 0, y: 344, width: 960, height: 92, depth: 426 },
  { id: 'south-frame', x: 0, y: 580, width: 960, height: 60, depth: 640 },

  { id: 'west-wall-a', x: 0, y: 48, width: 56, height: 145, depth: 193 },
  { id: 'west-wall-b', x: 0, y: 193, width: 56, height: 150, depth: 343 },
  { id: 'west-wall-c', x: 0, y: 343, width: 56, height: 150, depth: 493 },
  { id: 'west-wall-d', x: 0, y: 493, width: 56, height: 100, depth: 593 },
  { id: 'east-wall-a', x: 904, y: 48, width: 56, height: 145, depth: 193 },
  { id: 'east-wall-b', x: 904, y: 193, width: 56, height: 150, depth: 343 },
  { id: 'east-wall-c', x: 904, y: 343, width: 56, height: 150, depth: 493 },
  { id: 'east-wall-d', x: 904, y: 493, width: 56, height: 100, depth: 593 },

  { id: 'top-divider-left-a', x: 300, y: 45, width: 64, height: 95, depth: 140 },
  { id: 'top-divider-left-b', x: 300, y: 140, width: 64, height: 95, depth: 235 },
  { id: 'top-divider-right-a', x: 604, y: 45, width: 64, height: 95, depth: 140 },
  { id: 'top-divider-right-b', x: 604, y: 140, width: 64, height: 95, depth: 235 },

  { id: 'bottom-divider-plan-a', x: 296, y: 400, width: 70, height: 92, depth: 492 },
  { id: 'bottom-divider-plan-b', x: 296, y: 492, width: 70, height: 98, depth: 590 },
  { id: 'bottom-divider-analytics-a', x: 420, y: 400, width: 58, height: 92, depth: 492 },
  { id: 'bottom-divider-analytics-b', x: 420, y: 492, width: 58, height: 98, depth: 590 },
  { id: 'bottom-divider-server-a', x: 716, y: 390, width: 56, height: 102, depth: 492 },
  { id: 'bottom-divider-server-b', x: 716, y: 492, width: 56, height: 98, depth: 590 },
]
