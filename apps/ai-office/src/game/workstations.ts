export type Point = { x: number; y: number }

export type Workstation = {
  id: string
  room: string
  position: Point
  approach: Point[]
  facing: 'up' | 'down' | 'left' | 'right'
}

export const COMMAND_CONSOLE_WORKSTATION: Workstation = {
  id: 'command-console-01',
  room: 'command-center',
  position: { x: 168, y: 214 },
  approach: [{ x: 168, y: 214 }],
  facing: 'up',
}

export const RESEARCH_DESK_WORKSTATION: Workstation = {
  id: 'research-desk-01',
  room: 'research-lab',
  position: { x: 480, y: 212 },
  approach: [{ x: 480, y: 212 }],
  facing: 'up',
}

export const TUTOR_DESK_WORKSTATION: Workstation = {
  id: 'tutor-desk-01',
  room: 'tutor-room',
  position: { x: 792, y: 212 },
  approach: [{ x: 792, y: 212 }],
  facing: 'up',
}

export const PLANNING_DESK_WORKSTATION: Workstation = {
  id: 'planning-desk-01',
  room: 'planning-hub',
  position: { x: 168, y: 542 },
  approach: [{ x: 168, y: 542 }],
  facing: 'up',
}

export const ANALYTICS_CONSOLE_WORKSTATION: Workstation = {
  id: 'analytics-console-01',
  room: 'analytics-room',
  position: { x: 550, y: 555 },
  approach: [{ x: 550, y: 555 }],
  facing: 'up',
}

export const KNOWLEDGE_INDEX_WORKSTATION: Workstation = {
  id: 'knowledge-index-01',
  room: 'knowledge-server',
  position: { x: 874, y: 565 },
  approach: [
    { x: 780, y: 548 },
    { x: 840, y: 548 },
    { x: 874, y: 565 },
  ],
  facing: 'up',
}

export const KNOWLEDGE_MAINTENANCE_WORKSTATION: Workstation = {
  id: 'knowledge-maintenance-01',
  room: 'knowledge-server',
  position: { x: 770, y: 540 },
  approach: [
    { x: 738, y: 548 },
    { x: 770, y: 548 },
    { x: 770, y: 540 },
  ],
  facing: 'right',
}

export const WORKSTATIONS: Record<string, Workstation> = {
  [COMMAND_CONSOLE_WORKSTATION.id]: COMMAND_CONSOLE_WORKSTATION,
  [RESEARCH_DESK_WORKSTATION.id]: RESEARCH_DESK_WORKSTATION,
  [TUTOR_DESK_WORKSTATION.id]: TUTOR_DESK_WORKSTATION,
  [PLANNING_DESK_WORKSTATION.id]: PLANNING_DESK_WORKSTATION,
  [ANALYTICS_CONSOLE_WORKSTATION.id]: ANALYTICS_CONSOLE_WORKSTATION,
  [KNOWLEDGE_INDEX_WORKSTATION.id]: KNOWLEDGE_INDEX_WORKSTATION,
  [KNOWLEDGE_MAINTENANCE_WORKSTATION.id]: KNOWLEDGE_MAINTENANCE_WORKSTATION,
}

export const AGENT_WORKSTATION_IDS: Record<string, string> = {
  coordinator: COMMAND_CONSOLE_WORKSTATION.id,
  researcher: KNOWLEDGE_INDEX_WORKSTATION.id,
  tutor: TUTOR_DESK_WORKSTATION.id,
  planner: PLANNING_DESK_WORKSTATION.id,
  analyst: ANALYTICS_CONSOLE_WORKSTATION.id,
  keeper: KNOWLEDGE_MAINTENANCE_WORKSTATION.id,
}
