import type { OfficeAgent, OfficeEvent, OfficeSnapshot, OfficeTask } from '../types'

const now = new Date().toISOString()

export const demoAgents: OfficeAgent[] = [
  {
    id: 'coordinator',
    name: 'NOVA',
    role: 'Koordinator asisten AI',
    room: 'command-center',
    color: '#22d3ee',
    state: 'idle',
    task: 'Siap memantau sistem EduPad',
    progress: 0,
    updated_at: now,
  },
  {
    id: 'researcher',
    name: 'PIXEL',
    role: 'Pengolah materi kuliah',
    room: 'research-lab',
    color: '#60a5fa',
    state: 'idle',
    task: 'Siap memproses materi kuliah',
    progress: 0,
    activity: 'idle',
    station_id: null,
    updated_at: now,
  },
  {
    id: 'tutor',
    name: 'SORA',
    role: 'Tutor belajar',
    room: 'tutor-room',
    color: '#facc15',
    state: 'idle',
    task: 'Siap menerima pertanyaan',
    progress: 0,
    updated_at: now,
  },
  {
    id: 'planner',
    name: 'TEMPO',
    role: 'Pengatur jadwal belajar',
    room: 'planning-hub',
    color: '#a78bfa',
    state: 'idle',
    task: 'Menunggu tugas perencanaan',
    progress: 0,
    updated_at: now,
  },
  {
    id: 'analyst',
    name: 'METRIC',
    role: 'Pemantau progres belajar',
    room: 'analytics-room',
    color: '#34d399',
    state: 'idle',
    task: 'Siap menganalisis progres',
    progress: 0,
    updated_at: now,
  },
  {
    id: 'keeper',
    name: 'NEXUS',
    role: 'Penjaga data pengetahuan',
    room: 'knowledge-server',
    color: '#fb7185',
    state: 'idle',
    task: 'Siap menjaga sumber pengetahuan',
    progress: 0,
    updated_at: now,
  },
]

export const demoTasks: OfficeTask[] = [
  {
    id: 'demo-1',
    title: 'Perbarui materi pertemuan terbaru',
    description: 'Siapkan materi terbaru agar dapat digunakan untuk belajar.',
    status: 'completed',
    priority: 'high',
    assigned_agent: 'researcher',
    job_type: 'index',
    created_at: now,
    updated_at: now,
  },
]

export const demoEvents: OfficeEvent[] = [
  {
    id: 1,
    agent_id: 'researcher',
    state: 'succeeded',
    room: 'knowledge-server',
    job_type: 'index',
    message: 'Materi terbaru sudah siap digunakan',
    progress: 100,
    metadata: {
      activity: 'completed',
      station_id: 'knowledge-index-01',
      task_id: 'demo-1',
      chunks_completed: 1,
      chunks_total: 1,
    },
    created_at: now,
  },
]

export const demoSnapshot: OfficeSnapshot = {
  status: 'preview',
  source: 'preview',
  agents: demoAgents,
  tasks: demoTasks,
  recent_events: demoEvents,
  last_event_id: 1,
  metrics: {
    active_agents: 0,
    queued_tasks: 0,
    completed_tasks: 1,
    knowledge_health: 96,
  },
}

