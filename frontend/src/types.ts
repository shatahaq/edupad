export type AgentState =
  | 'offline'
  | 'idle'
  | 'queued'
  | 'running'
  | 'waiting'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export type AgentActivity = 'idle' | 'indexing' | 'completed' | 'failed'

export type OfficeAgent = {
  id: string
  name: string
  role: string
  room: string
  color: string
  state: AgentState
  task: string
  progress: number
  activity?: AgentActivity
  station_id?: string | null
  updated_at: string
}

export type OfficeTask = {
  id: string
  title: string
  description: string
  status: 'queued' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  priority: 'low' | 'medium' | 'high'
  assigned_agent: string
  job_type?: 'manual' | 'index'
  due_at?: string | null
  claimed_by?: string | null
  claimed_at?: string | null
  started_at?: string | null
  finished_at?: string | null
  error?: string | null
  result?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type OfficeEvent = {
  id: number | string
  run_id?: string | null
  agent_id: string
  state: AgentState
  room: string
  job_type: string
  message: string
  progress: number
  metadata?: {
    activity?: AgentActivity
    station_id?: string
    task_id?: string
    chunks_completed?: number
    chunks_total?: number
    error?: string
    [key: string]: unknown
  }
  created_at: string
}

export type OfficeSnapshot = {
  status: string
  source: 'supabase' | 'local' | 'preview'
  agents: OfficeAgent[]
  tasks: OfficeTask[]
  recent_events: OfficeEvent[]
  last_event_id: number | string | null
  metrics: {
    active_agents: number
    queued_tasks: number
    completed_tasks: number
    knowledge_health: number
  }
}

export type IoTChatTurn = {
  id: number | string
  session_id?: string | null
  question: string
  answer: string
  screen: string[]
  created_at?: string | null
}

export type IoTChatHistory = {
  source: 'supabase' | 'unavailable'
  items: IoTChatTurn[]
}

export type NewTask = Pick<
  OfficeTask,
  'title' | 'description' | 'priority' | 'assigned_agent'
> & { job_type: 'index' }

