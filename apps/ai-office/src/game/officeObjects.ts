export type OfficeObject = {
  id: string
  room: 'command-center' | 'research-lab' | 'tutor-room' | 'planning-hub' | 'analytics-room' | 'knowledge-server' | 'corridor'
  frame: number
  x: number
  y: number
  width: number
  height: number
  depth?: number
  placement?: 'floor' | 'wall'
  crop?: { x: number; y: number; width: number; height: number }
}

export const FURNITURE_CONTENT_SIZE: ReadonlyArray<{ width: number; height: number }> = [
  { width: 305, height: 193 },
  { width: 249, height: 178 },
  { width: 216, height: 187 },
  { width: 236, height: 182 },
  { width: 292, height: 204 },
  { width: 253, height: 203 },
  { width: 206, height: 176 },
  { width: 271, height: 289 },
  { width: 197, height: 275 },
  { width: 263, height: 160 },
  { width: 233, height: 226 },
  { width: 274, height: 146 },
  { width: 187, height: 241 },
  { width: 126, height: 165 },
  { width: 158, height: 186 },
  { width: 111, height: 209 },
]

export const FURNITURE_CATALOG = [
  'Command Console',
  'Research Workbench',
  'Tutor Desk',
  'Planning Desk',
  'Analytics Console',
  'Server Rack',
  'Index Terminal',
  'Knowledge Globe',
  'Bookshelf',
  'Wall Display',
  'Scanner Cabinet',
  'Lobby Sofa',
  'Tall Plant',
  'Desk Plant',
  'Office Chair',
  'Data Kiosk',
] as const

// Frame order follows the 4x4 atlas documented in ASSET_PROMPTS.md.
export const OFFICE_OBJECTS: OfficeObject[] = [
  { id: 'command-console', room: 'command-center', frame: 0, x: 166, y: 140, width: 176, height: 100 },
  { id: 'command-kiosk', room: 'command-center', frame: 15, x: 284, y: 126, width: 28, height: 48 },
  { id: 'research-workbench', room: 'research-lab', frame: 1, x: 474, y: 140, width: 160, height: 92 },
  { id: 'research-chair', room: 'research-lab', frame: 14, x: 366, y: 122, width: 32, height: 38 },
  { id: 'tutor-desk', room: 'tutor-room', frame: 2, x: 790, y: 140, width: 158, height: 92 },
  { id: 'tutor-chair', room: 'tutor-room', frame: 14, x: 684, y: 145, width: 32, height: 38 },
  { id: 'planning-desk', room: 'planning-hub', frame: 3, x: 164, y: 470, width: 162, height: 86 },
  { id: 'planning-books', room: 'planning-hub', frame: 8, x: 278, y: 480, width: 36, height: 72 },
  { id: 'analytics-console', room: 'analytics-room', frame: 4, x: 550, y: 485, width: 160, height: 84 },
  { id: 'analytics-board', room: 'analytics-room', frame: 9, x: 640, y: 445, width: 70, height: 35, depth: 424, placement: 'wall' },
  { id: 'analytics-plant', room: 'analytics-room', frame: 13, x: 650, y: 560, width: 28, height: 38 },
  { id: 'server-rack-01', room: 'knowledge-server', frame: 5, x: 747, y: 466, width: 34, height: 82, crop: { x: 65, y: 90, width: 84, height: 203 } },
  { id: 'server-rack-02', room: 'knowledge-server', frame: 5, x: 783, y: 466, width: 34, height: 82, crop: { x: 149, y: 90, width: 84, height: 203 } },
  { id: 'server-rack-03', room: 'knowledge-server', frame: 5, x: 819, y: 466, width: 34, height: 82, crop: { x: 233, y: 90, width: 85, height: 203 } },
  { id: 'server-rack-04', room: 'knowledge-server', frame: 5, x: 855, y: 466, width: 34, height: 82, crop: { x: 149, y: 90, width: 84, height: 203 } },
  { id: 'index-terminal', room: 'knowledge-server', frame: 6, x: 874, y: 545, width: 64, height: 62 },
  { id: 'knowledge-globe', room: 'corridor', frame: 7, x: 480, y: 330, width: 96, height: 96 },
  { id: 'research-books', room: 'research-lab', frame: 8, x: 572, y: 124, width: 48, height: 82, depth: 76 },
  { id: 'tutor-whiteboard', room: 'tutor-room', frame: 9, x: 790, y: 65, width: 126, height: 56, depth: 64, placement: 'wall' },
  { id: 'planning-scanner', room: 'planning-hub', frame: 10, x: 82, y: 454, width: 44, height: 66, depth: 76 },
  { id: 'lobby-sofa', room: 'corridor', frame: 11, x: 170, y: 324, width: 92, height: 52 },
  { id: 'command-plant', room: 'command-center', frame: 12, x: 62, y: 174, width: 40, height: 68 },
  { id: 'research-plant', room: 'research-lab', frame: 13, x: 390, y: 198, width: 30, height: 42 },
  { id: 'tutor-plant', room: 'tutor-room', frame: 12, x: 895, y: 174, width: 40, height: 68 },
  { id: 'planning-plant', room: 'planning-hub', frame: 13, x: 56, y: 520, width: 30, height: 42 },
  { id: 'server-kiosk', room: 'analytics-room', frame: 15, x: 640, y: 500, width: 36, height: 64 },
]
