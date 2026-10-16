import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type ReactNode,
} from 'react'

import { useOfficeData } from './hooks/useOfficeData'
import type {
import { assetUrl } from './game/assetUrl'
  AgentState,
  IoTChatTurn,
  NewTask,
  OfficeAgent,
  OfficeEvent,
  OfficeTask,
} from './types'

const OfficeGame = lazy(() =>
  import('./game/OfficeGame').then((module) => ({ default: module.OfficeGame })),
)

const stateLabels: Record<AgentState, string> = {
  offline: 'Offline',
  idle: 'Siaga',
  queued: 'Menunggu giliran',
  running: 'Sedang mengerjakan',
  waiting: 'Menunggu data',
  succeeded: 'Selesai',
  failed: 'Perlu diperiksa',
  cancelled: 'Dibatalkan',
}

const stateStyles: Record<AgentState, string> = {
  offline: 'border-slate-200 bg-slate-100 text-slate-500',
  idle: 'border-sky-100 bg-sky-50 text-sky-600',
  queued: 'border-violet-100 bg-violet-50 text-violet-600',
  running: 'border-cyan-100 bg-cyan-50 text-cyan-700',
  waiting: 'border-amber-100 bg-amber-50 text-amber-700',
  succeeded: 'border-emerald-100 bg-emerald-50 text-emerald-700',
  failed: 'border-rose-100 bg-rose-50 text-rose-700',
  cancelled: 'border-slate-200 bg-slate-100 text-slate-500',
}

const taskStatusLabels: Record<OfficeTask['status'], string> = {
  queued: 'Menunggu',
  in_progress: 'Diproses',
  completed: 'Selesai',
  failed: 'Gagal',
  cancelled: 'Dibatalkan',
}

const taskStatusStyles: Record<OfficeTask['status'], string> = {
  queued: 'is-queued',
  in_progress: 'is-running',
  completed: 'is-completed',
  failed: 'is-failed',
  cancelled: 'is-cancelled',
}

const friendlyAgentRoles: Record<string, string> = {
  coordinator: 'Koordinator asisten AI',
  researcher: 'Pengolah materi kuliah',
  tutor: 'Tutor belajar',
  planner: 'Pengatur jadwal belajar',
  analyst: 'Pemantau progres belajar',
  keeper: 'Penjaga data pengetahuan',
}

const priorityLabels: Record<OfficeTask['priority'], string> = {
  low: 'Biasa',
  medium: 'Penting',
  high: 'Mendesak',
}

const jobTypeLabels: Record<'manual' | 'index', string> = {
  manual: 'Tugas bantuan',
  index: 'Memproses materi',
}

const agentDescriptions: Record<string, string> = {
  coordinator: 'NOVA memantau kondisi EduPad dan membantu mengatur urutan pekerjaan para asisten AI.',
  researcher: 'PIXEL membaca dan mengolah materi kuliah agar isinya dapat digunakan oleh fitur belajar EduPad.',
  tutor: 'SORA membantu mahasiswa memahami materi dan menjawab pertanyaan berdasarkan sumber belajar yang tersedia.',
  planner: 'TEMPO membantu menyusun jadwal, mengingatkan tenggat, dan membagi target belajar menjadi langkah yang lebih ringan.',
  analyst: 'METRIC membantu melihat perkembangan belajar dari aktivitas dan hasil evaluasi mahasiswa.',
  keeper: 'NEXUS menjaga agar data materi dan sumber pengetahuan EduPad tetap tersedia dan teratur.',
}

const roomLabels: Record<string, string> = {
  'command-center': 'Command Center',
  'research-lab': 'Research Lab',
  'tutor-room': 'Tutor Room',
  'planning-hub': 'Planning Hub',
  'analytics-room': 'Analytics Room',
  'knowledge-server': 'Knowledge Server',
  corridor: 'Main Corridor',
}

type RoomProfile = {
  id: string
  number: string
  name: string
  tagline: string
  description: string
  color: string
  frame: number
  agentIds: string[]
  capabilities: string[]
}

const roomProfiles: RoomProfile[] = [
  { id: 'command-center', number: '01', name: 'Command Center', tagline: 'Pusat koordinasi EduPad', description: 'Ruang kendali untuk memantau kondisi EduPad dan mengatur urutan pekerjaan para asisten AI.', color: '#22d3ee', frame: 0, agentIds: ['coordinator'], capabilities: ['Mengatur pekerjaan', 'Memantau layanan', 'Menentukan urutan tugas'] },
  { id: 'research-lab', number: '02', name: 'Research Lab', tagline: 'Pengolahan materi kuliah', description: 'Area tempat dokumen kuliah dibaca, dirapikan, dan disiapkan agar dapat digunakan oleh fitur belajar EduPad.', color: '#60a5fa', frame: 1, agentIds: ['researcher'], capabilities: ['Membaca dokumen', 'Merapikan materi', 'Menyiapkan sumber belajar'] },
  { id: 'tutor-room', number: '03', name: 'Tutor Room', tagline: 'Bantuan belajar mahasiswa', description: 'Ruang tutor untuk menjawab pertanyaan dan menjelaskan materi berdasarkan sumber belajar yang tersimpan di EduPad.', color: '#f59e0b', frame: 2, agentIds: ['tutor'], capabilities: ['Menjawab pertanyaan', 'Menjelaskan materi', 'Mendampingi belajar'] },
  { id: 'planning-hub', number: '04', name: 'Planning Hub', tagline: 'Jadwal, tugas, dan tenggat', description: 'Pusat perencanaan untuk menyusun agenda belajar, memantau batas pengumpulan, dan membagi target menjadi langkah kecil.', color: '#a78bfa', frame: 3, agentIds: ['planner'], capabilities: ['Menyusun jadwal', 'Mengingatkan tenggat', 'Membuat rencana belajar'] },
  { id: 'analytics-room', number: '05', name: 'Analytics Room', tagline: 'Perkembangan belajar', description: 'Ruang untuk melihat progres belajar, hasil evaluasi, dan ringkasan aktivitas mahasiswa.', color: '#34d399', frame: 4, agentIds: ['analyst'], capabilities: ['Melihat progres', 'Merangkum hasil', 'Menyiapkan laporan belajar'] },
  { id: 'knowledge-server', number: '06', name: 'Knowledge Server', tagline: 'Pusat data dan materi', description: 'Ruang server yang menyimpan materi dan sumber pengetahuan yang digunakan oleh EduPad.', color: '#fb7185', frame: 5, agentIds: ['keeper', 'researcher'], capabilities: ['Menyimpan materi', 'Memperbarui sumber belajar', 'Memantau kondisi data'] },
]

function BrandMark() {
  return <div className="relative grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-xl bg-gradient-to-br from-blue-600 to-cyan-400 shadow-[0_8px_24px_rgba(37,99,235,.26)]"><span className="absolute h-6 w-2 -rotate-45 rounded-full bg-white/90" /><span className="absolute h-2 w-6 rotate-45 rounded-full bg-emerald-300" /></div>
}

function TaskIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 4h8M9 3v3m6-3v3M6 5.5h12a2 2 0 0 1 2 2V19a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7.5a2 2 0 0 1 2-2Z" /><path d="m8 13 2.2 2.2L16 9.5" /></svg>
}

function StatusPill({ state }: { state: AgentState }) {
  return <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-[.1em] ${stateStyles[state]}`}><span className={`h-2 w-2 rounded-full bg-current ${state === 'running' ? 'animate-pulse' : ''}`} />{stateLabels[state]}</span>
}

function MiniBot({ agent }: { agent: OfficeAgent }) {
  return <div className="mini-bot" style={{ '--bot-color': agent.color } as CSSProperties}><span className="mini-bot-antenna" /><span className="mini-bot-face"><i /><i /></span></div>
}

function workCapacity(agent: OfficeAgent) {
  if (agent.state === 'offline') return 0
  if (agent.state === 'failed') return 35
  if (agent.state === 'running') return Math.max(18, 100 - Math.round(agent.progress * 0.72))
  if (['queued', 'waiting'].includes(agent.state)) return 70
  return 100
}

function AgentTopCard({ agent, onClick }: { agent: OfficeAgent; onClick: () => void }) {
  const capacity = workCapacity(agent)
  return (
    <button
      type="button"
      onClick={onClick}
      className="agent-top-card"
      title={`Lihat profil ${agent.name}`}
    >
      <MiniBot agent={agent} />
      <span className="min-w-0 flex-1 text-left">
        <strong className="block truncate text-[10px] text-slate-800">{agent.name}</strong>
        <span className="block truncate text-[8px] text-slate-400">
          {friendlyAgentRoles[agent.id] ?? agent.role}
        </span>
        <span className="mt-1 flex items-center gap-1" aria-label={`Kesiapan ${capacity}%`}>
          <small className="font-mono text-[6px] font-black text-slate-400">SIAP</small>
          <i className="h-1 flex-1 overflow-hidden rounded-full bg-slate-200">
            <i className="block h-full rounded-full" style={{ width: `${capacity}%`, backgroundColor: agent.color }} />
          </i>
          <small className="font-mono text-[7px] text-slate-400">{capacity}%</small>
        </span>
      </span>
    </button>
  )
}

function AnimatedAgent({ agent }: { agent: OfficeAgent }) {
  return <div className="agent-portrait-stage" style={{ boxShadow: `inset 0 0 90px ${agent.color}24` }}><div className="agent-portrait-grid" /><div className="agent-portrait-glow" style={{ backgroundColor: agent.color }} /><div className={`agent-idle-frame agent-tint-${agent.id}`}><img src={assetUrl("assets/agents/pixel/pixel-actions-v1.png")} alt="" draggable={false} className="agent-idle-strip" /></div><div className="agent-portrait-platform" style={{ borderColor: `${agent.color}80` }} /><span className="agent-portrait-label" style={{ color: agent.color }}>ANIMASI SAAT SIAP</span></div>
}

function StatTile({ label, value, accent }: { label: string; value: string; accent: string }) {
  return <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-3"><div className="text-[9px] font-bold uppercase tracking-[.12em] text-slate-400">{label}</div><div className="mt-1 font-mono text-xl font-black" style={{ color: accent }}>{value}</div></div>
}

function ModalLayer({ closing, onClose, children }: { closing: boolean; onClose: () => void; children: ReactNode }) {
  return <div className={`agent-modal-layer ${closing ? 'is-closing' : ''}`} onPointerDown={(event) => { event.stopPropagation(); if (event.target === event.currentTarget) onClose() }} onMouseDown={(event) => event.stopPropagation()} onClick={(event) => event.stopPropagation()}>{children}</div>
}

function CloseButton({ onClose }: { onClose: () => void }) {
  return <button type="button" onClick={onClose} className="agent-modal-close" aria-label="Tutup">×</button>
}

function taskTime(task: OfficeTask) {
  const value = new Date(task.updated_at || task.created_at)
  return Number.isNaN(value.getTime()) ? 'Waktu tidak tersedia' : value.toLocaleString('id-ID', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' })
}

function TaskStatusPill({ status }: { status: OfficeTask['status'] }) {
  return <span className={`task-status-pill ${taskStatusStyles[status]}`}><i />{taskStatusLabels[status]}</span>
}

function friendlyTaskError(error?: string | null) {
  if (!error) return null
  const normalized = error.toLowerCase()
  if (normalized.includes('kode 1') || normalized.includes('exit code 1')) {
    return 'Materi belum berhasil diproses. Pastikan sumber materi sudah tersedia, lalu coba lagi.'
  }
  return 'Tugas belum berhasil diselesaikan. Silakan coba lagi atau hubungi pengelola EduPad.'
}

function friendlyTaskTitle(title: string) {
  return title.replace(/^indeks materi/i, 'Perbarui materi')
}

function friendlyEducationalText(text: string) {
  const normalized = text.toLowerCase()
  if (normalized.includes('embedding') && normalized.includes('knowledge base')) {
    return 'Siapkan materi agar dapat digunakan oleh fitur belajar EduPad.'
  }
  return text
    .replace(/knowledge base/gi, 'sumber pengetahuan')
    .replace(/indexing/gi, 'pengolahan materi')
    .replace(/embedding/gi, 'pemrosesan materi')
    .replace(/\bchunk\b/gi, 'bagian')
}

function TaskListItem({ task, agent, onCancel, compact = false }: { task: OfficeTask; agent?: OfficeAgent; onCancel?: (taskId: string) => Promise<void>; compact?: boolean }) {
  const [cancelling, setCancelling] = useState(false)
  const errorMessage = friendlyTaskError(task.error)
  const handleCancel = async () => {
    if (!onCancel || cancelling) return
    setCancelling(true)
    try { await onCancel(task.id) } finally { setCancelling(false) }
  }
  return (
    <article className={`office-task-card ${compact ? 'is-compact' : ''}`}>
      <div className="office-task-card-top">
        <div className="office-task-agent-mark" style={{ '--task-agent-color': agent?.color ?? '#60a5fa' } as CSSProperties}>
          {agent ? agent.name.slice(0, 2) : 'AI'}
        </div>
        <div className="min-w-0 flex-1">
          <h4>{friendlyTaskTitle(task.title)}</h4>
          <p>{agent?.name ?? task.assigned_agent} <span aria-hidden="true">·</span> {jobTypeLabels[task.job_type ?? 'manual']}</p>
        </div>
        <TaskStatusPill status={task.status} />
      </div>
      {task.description && <p className="office-task-description">{friendlyEducationalText(task.description)}</p>}
      {errorMessage && <div className="office-task-error">{errorMessage}</div>}
      <div className="office-task-meta">
        <span className={`priority-${task.priority}`}>{priorityLabels[task.priority]}</span>
        <time>{taskTime(task)}</time>
        {task.status === 'queued' && onCancel && (
          <button type="button" disabled={cancelling} onClick={() => void handleCancel()}>
            {cancelling ? 'Membatalkan…' : 'Batalkan'}
          </button>
        )}
      </div>
    </article>
  )
}

function AgentProfileModal({ agent, tasks, closing, onClose, onOpenTaskCenter }: { agent: OfficeAgent; tasks: OfficeTask[]; closing: boolean; onClose: () => void; onOpenTaskCenter: () => void }) {
  const [activeTab, setActiveTab] = useState<'profile' | 'tasks'>('profile')
  const assigned = tasks.filter((task) => task.assigned_agent === agent.id)
  const completed = assigned.filter((task) => task.status === 'completed').length
  const failed = assigned.filter((task) => task.status === 'failed').length
  const hasLiveTaskConnection = agent.id === 'researcher'
  const updated = new Date(agent.updated_at)
  const updatedLabel = Number.isNaN(updated.getTime()) ? 'Belum tersedia' : updated.toLocaleString('id-ID', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' })
  return (
    <ModalLayer closing={closing} onClose={onClose}>
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="agent-profile-title"
        className="agent-profile-modal"
        style={{ '--agent-accent': agent.color } as CSSProperties}
      >
        <CloseButton onClose={onClose} />
        <div className="agent-profile-visual">
          <AnimatedAgent agent={agent} />
          <div className="mt-4 flex items-center justify-center gap-2">
            <span className="h-2 w-2 animate-pulse rounded-full" style={{ backgroundColor: agent.color }} />
            <span className="text-[10px] font-bold text-slate-500">{roomLabels[agent.room] ?? agent.room}</span>
          </div>
        </div>
        <div className="agent-profile-copy">
          <div className="text-[10px] font-black uppercase tracking-[.16em]" style={{ color: agent.color }}>
            Asisten belajar EduPad
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h2 id="agent-profile-title" className="text-4xl font-black tracking-tight text-slate-900">{agent.name}</h2>
            <StatusPill state={agent.state} />
          </div>
          <div className="mt-1 text-sm font-extrabold" style={{ color: agent.color }}>
            {friendlyAgentRoles[agent.id] ?? agent.role}
          </div>
          <div className="agent-detail-tabs" role="tablist" aria-label={`Informasi ${agent.name}`}>
            <button type="button" role="tab" aria-selected={activeTab === 'profile'} className={activeTab === 'profile' ? 'is-active' : ''} onClick={() => setActiveTab('profile')}>Tentang</button>
            <button type="button" role="tab" aria-selected={activeTab === 'tasks'} className={activeTab === 'tasks' ? 'is-active' : ''} onClick={() => setActiveTab('tasks')}>Riwayat tugas <span>{assigned.length}</span></button>
          </div>
          {activeTab === 'profile' ? (
            <div className="agent-tab-panel">
              <p className="max-w-xl text-sm leading-7 text-slate-600">{agentDescriptions[agent.id] ?? 'Asisten AI EduPad yang membantu kegiatan belajar mahasiswa.'}</p>
              <div className="mt-5 grid grid-cols-3 gap-2">
                <StatTile label="Tugas tercatat" value={String(assigned.length)} accent={agent.color} />
                <StatTile label="Selesai" value={String(completed)} accent="#10b981" />
                <StatTile label="Perlu ditinjau" value={String(failed)} accent="#f43f5e" />
              </div>
              <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/60 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-[10px] font-black uppercase tracking-[.12em] text-blue-500">Kegiatan saat ini</div>
                  <div className="text-[10px] font-bold text-slate-400">{agent.progress}%</div>
                </div>
                <div className="mt-1 text-sm font-bold text-slate-800">{friendlyEducationalText(agent.task)}</div>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-blue-100">
                  <div className="h-full rounded-full transition-all duration-700" style={{ width: `${agent.progress}%`, backgroundColor: agent.color }} />
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-[11px] text-slate-500">
                <span><strong className="text-slate-700">Lokasi:</strong> {roomLabels[agent.room] ?? agent.room}</span>
                <span><strong className="text-slate-700">Terakhir diperbarui:</strong> {updatedLabel}</span>
              </div>
            </div>
          ) : (
            <div className="agent-tab-panel agent-task-tab">
              <div className="agent-task-tab-heading">
                <div>
                  <strong>Riwayat tugas {agent.name}</strong>
                  <span>Daftar ini mengikuti catatan dari sistem EduPad.</span>
                </div>
                <button type="button" onClick={onOpenTaskCenter}>Lihat semua tugas</button>
              </div>
              <div className="agent-task-scroll">
                {assigned.length ? assigned.map((task) => <TaskListItem key={task.id} task={task} agent={agent} compact />) : (
                  <div className="agent-task-empty">
                    <TaskIcon />
                    <strong>Belum ada tugas</strong>
                    <span>Tugas untuk {agent.name} akan muncul di sini.</span>
                  </div>
                )}
              </div>
              <div className={`agent-task-note ${hasLiveTaskConnection ? 'is-live' : ''}`}>
                {hasLiveTaskConnection
                  ? 'PIXEL sudah terhubung ke proses pengolahan materi EduPad.'
                  : `Untuk uji coba ini, tugas nyata ${agent.name} belum diaktifkan. Pekerjaan nyata yang tersedia saat ini adalah pengolahan materi oleh PIXEL.`}
              </div>
            </div>
          )}
        </div>
      </section>
    </ModalLayer>
  )
}

function TaskCenterModal({ tasks, agents, apiAvailable, closing, onClose, onCreateTask, onUpdateTask }: { tasks: OfficeTask[]; agents: OfficeAgent[]; apiAvailable: boolean; closing: boolean; onClose: () => void; onCreateTask: (input: NewTask) => Promise<OfficeTask>; onUpdateTask: (taskId: string, values: Partial<OfficeTask>) => Promise<OfficeTask> }) {
  const [filter, setFilter] = useState<'all' | OfficeTask['status']>('all')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<OfficeTask['priority']>('medium')
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const visibleTasks = filter === 'all' ? tasks : tasks.filter((task) => task.status === filter)
  const activeCount = tasks.filter((task) => ['queued', 'in_progress'].includes(task.status)).length
  const completedCount = tasks.filter((task) => task.status === 'completed').length
  const failedCount = tasks.filter((task) => task.status === 'failed').length
  const agentById = new Map(agents.map((agent) => [agent.id, agent]))
  const researcher = agents.find((agent) => agent.id === 'researcher') ?? agents[0]

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!title.trim() || submitting) return
    setSubmitting(true)
    setFeedback(null)
    try {
      await onCreateTask({ title: title.trim(), description: description.trim(), priority, assigned_agent: 'researcher', job_type: 'index' })
      setFeedback({ type: 'success', message: apiAvailable ? 'Tugas sudah diterima. PIXEL akan mulai saat gilirannya tiba.' : 'Ini masih mode tampilan. Tugas belum dikirim ke sistem.' })
      setTitle('')
      setDescription('')
    } catch {
      setFeedback({ type: 'error', message: 'Tugas belum dapat dikirim. Periksa koneksi EduPad, lalu coba lagi.' })
    } finally {
      setSubmitting(false)
    }
  }

  const cancelTask = async (taskId: string) => {
    try { await onUpdateTask(taskId, { status: 'cancelled' }) } catch { setFeedback({ type: 'error', message: 'Tugas belum dapat dibatalkan. Silakan coba lagi.' }) }
  }

  return (
    <ModalLayer closing={closing} onClose={onClose}>
      <section role="dialog" aria-modal="true" aria-labelledby="task-center-title" className="task-center-modal">
        <CloseButton onClose={onClose} />
        <header className="task-center-header">
          <div className="task-center-symbol"><TaskIcon /></div>
          <div className="task-center-heading">
            <span>Pekerjaan asisten AI</span>
            <h2 id="task-center-title">Pusat Tugas</h2>
            <p>Buat tugas baru dan lihat hasil pekerjaan asisten EduPad.</p>
          </div>
          <div className="task-center-ready"><i /><span><strong>PIXEL siap digunakan</strong><small>Pengolahan materi kuliah</small></span></div>
        </header>
        <div className="task-center-metrics" aria-label="Ringkasan tugas">
          <div><span>Sedang berjalan</span><strong>{activeCount}</strong></div>
          <div><span>Selesai</span><strong>{completedCount}</strong></div>
          <div><span>Perlu ditinjau</span><strong>{failedCount}</strong></div>
        </div>
        <div className="task-center-body">
          <div className="task-center-list-column">
            <div className="task-list-heading">
              <div><strong>Daftar tugas</strong><span>{tasks.length} tugas tercatat</span></div>
              <div className="task-filter-row" role="tablist" aria-label="Pilih status tugas">
                {(['all', 'queued', 'in_progress', 'completed', 'failed'] as const).map((value) => (
                  <button type="button" role="tab" aria-selected={filter === value} className={filter === value ? 'is-active' : ''} onClick={() => setFilter(value)} key={value}>
                    {value === 'all' ? 'Semua' : value === 'failed' ? 'Perlu ditinjau' : taskStatusLabels[value]}
                  </button>
                ))}
              </div>
            </div>
            <div className="task-center-list">
              {visibleTasks.length ? visibleTasks.map((task) => (
                <TaskListItem key={task.id} task={task} agent={agentById.get(task.assigned_agent)} onCancel={cancelTask} />
              )) : (
                <div className="task-center-empty">
                  <TaskIcon />
                  <strong>Belum ada tugas di bagian ini</strong>
                  <span>Pilih status lain atau buat tugas baru untuk PIXEL.</span>
                </div>
              )}
            </div>
          </div>
          <form className="task-composer" onSubmit={(event) => void submit(event)}>
            <div className="task-composer-intro">
              <span className="task-composer-eyebrow">Buat tugas baru</span>
              <h3>Minta PIXEL mengolah materi</h3>
              <p>PIXEL akan memproses materi yang sudah tersedia di EduPad agar dapat digunakan untuk belajar.</p>
            </div>
            {researcher && (
              <div className="task-composer-route">
                <MiniBot agent={researcher} />
                <div><strong>PIXEL</strong><span>Pengolah materi kuliah</span></div>
                <b>AKTIF</b>
              </div>
            )}
            <label>
              <span>Nama tugas</span>
              <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={160} placeholder="Contoh: Perbarui materi Kalkulus minggu 3" required />
            </label>
            <label>
              <span>Catatan <small>(opsional)</small></span>
              <textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} rows={3} placeholder="Tambahkan catatan singkat untuk tugas ini" />
            </label>
            <label>
              <span>Tingkat kepentingan</span>
              <select value={priority} onChange={(event) => setPriority(event.target.value as OfficeTask['priority'])}>
                <option value="low">Biasa</option>
                <option value="medium">Penting</option>
                <option value="high">Mendesak</option>
              </select>
            </label>
            {feedback && <div className={`task-form-feedback is-${feedback.type}`}>{feedback.message}</div>}
            <button type="submit" className="task-submit-button" disabled={submitting || !title.trim()}>
              <TaskIcon />{submitting ? 'Mengirim tugas…' : 'Mulai pengolahan materi'}
            </button>
            <small>{apiAvailable ? 'Sistem siap menerima tugas.' : 'Mode tampilan: tugas belum dikirim ke sistem.'}</small>
            <div className="task-scope-note"><strong>Mengapa baru PIXEL?</strong><span>Untuk uji coba pertama, baru pengolahan materi yang sudah terhubung ke sistem EduPad. Tugas untuk NOVA, SORA, TEMPO, METRIC, dan NEXUS akan diaktifkan setelah proses masing-masing siap.</span></div>
          </form>
        </div>
      </section>
    </ModalLayer>
  )
}

function RoomVisual({ room }: { room: RoomProfile }) {
  const column = room.frame % 4
  const row = Math.floor(room.frame / 4)
  return <div className="room-portrait-stage" style={{ '--room-accent': room.color } as CSSProperties}><div className="agent-portrait-grid" /><div className="room-number">{room.number}</div><div className="room-main-asset" style={{ backgroundPosition: `${(column / 3) * 100}% ${(row / 3) * 100}%` }} /><div className="room-scan-line" /><strong>{room.name}</strong><span>{room.tagline}</span></div>
}

function RoomProfileModal({ room, agents, tasks, events, knowledgeHealth, closing, onClose }: { room: RoomProfile; agents: OfficeAgent[]; tasks: OfficeTask[]; events: OfficeEvent[]; knowledgeHealth: number; closing: boolean; onClose: () => void }) {
  const roomAgents = agents.filter((agent) => room.agentIds.includes(agent.id))
  const roomTasks = tasks.filter((task) => room.agentIds.includes(task.assigned_agent))
  const completed = roomTasks.filter((task) => task.status === 'completed').length
  const failed = roomTasks.filter((task) => task.status === 'failed').length
  const active = roomAgents.filter((agent) => ['queued', 'running', 'waiting'].includes(agent.state)).length
  const roomEvents = events.filter((event) => event.room === room.id)
  return (
    <ModalLayer closing={closing} onClose={onClose}>
      <section role="dialog" aria-modal="true" aria-labelledby="room-profile-title" className="agent-profile-modal room-profile-modal" style={{ '--agent-accent': room.color } as CSSProperties}>
        <CloseButton onClose={onClose} />
        <div className="agent-profile-visual">
          <RoomVisual room={room} />
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {roomAgents.map((agent) => <span key={agent.id} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[9px] font-bold text-slate-600"><i className="h-2 w-2 rounded-full" style={{ backgroundColor: agent.color }} />{agent.name}</span>)}
          </div>
        </div>
        <div className="agent-profile-copy">
          <div className="text-[10px] font-black uppercase tracking-[.16em]" style={{ color: room.color }}>Ruang {room.number}</div>
          <h2 id="room-profile-title" className="mt-2 text-4xl font-black tracking-tight text-slate-900">{room.name}</h2>
          <div className="mt-1 text-sm font-extrabold" style={{ color: room.color }}>{room.tagline}</div>
          <p className="mt-4 text-sm leading-7 text-slate-600">{room.description}</p>
          <div className="mt-5 grid grid-cols-4 gap-2">
            <StatTile label="Asisten aktif" value={String(active)} accent={room.color} />
            <StatTile label="Tugas tercatat" value={String(roomTasks.length)} accent="#2563eb" />
            <StatTile label="Selesai" value={String(completed)} accent="#10b981" />
            <StatTile label={room.id === 'knowledge-server' ? 'Kondisi data' : 'Perlu ditinjau'} value={room.id === 'knowledge-server' ? `${knowledgeHealth}%` : String(failed)} accent={room.id === 'knowledge-server' ? '#8b5cf6' : '#f43f5e'} />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-100 bg-slate-50/80 p-4">
              <div className="text-[9px] font-black uppercase tracking-[.14em] text-slate-400">Yang dilakukan di ruangan ini</div>
              <ul className="mt-2 space-y-2">{room.capabilities.map((capability) => <li key={capability} className="flex items-center gap-2 text-[11px] font-semibold text-slate-600"><i className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: room.color }} />{capability}</li>)}</ul>
            </div>
            <div className="rounded-2xl border border-blue-100 bg-blue-50/60 p-4">
              <div className="text-[9px] font-black uppercase tracking-[.14em] text-blue-500">Aktivitas terbaru</div>
              {roomEvents.slice(0, 3).map((event) => <div key={event.id} className="mt-2 truncate text-[10px] text-slate-600"><strong>{agents.find((agent) => agent.id === event.agent_id)?.name ?? event.agent_id}</strong> · {friendlyEducationalText(event.message)}</div>)}
              {!roomEvents.length && <div className="mt-3 text-[10px] text-slate-400">Belum ada aktivitas di ruangan ini.</div>}
            </div>
          </div>
        </div>
      </section>
    </ModalLayer>
  )
}

function ChatHistoryPanel({ chats, available }: { chats: IoTChatTurn[]; available: boolean }) {
  return (
    <aside className="iot-chat-panel">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div><div className="text-[9px] font-black uppercase tracking-[.14em] text-blue-500">Percakapan dari perangkat</div><h2 className="text-sm font-black text-slate-800">Riwayat percakapan</h2></div>
        <span className={`rounded-full px-2 py-1 text-[8px] font-black ${available ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'}`}>{available ? 'TERSAMBUNG' : 'BELUM TERSAMBUNG'}</span>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        {chats.map((turn) => <article key={turn.id} className="iot-chat-card"><div className="flex items-center justify-between"><span className="text-[8px] font-black uppercase tracking-wide text-blue-600">Perangkat belajar</span><time className="text-[8px] text-slate-400">{turn.created_at ? new Date(turn.created_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) : 'baru'}</time></div><div className="mt-2 text-[10px] font-bold leading-relaxed text-slate-700">“{turn.question}”</div><div className="mt-2 border-l-2 border-emerald-300 pl-2 text-[10px] leading-relaxed text-slate-500">{turn.answer}</div></article>)}
        {!chats.length && <div className="grid min-h-40 place-items-center rounded-2xl border border-dashed border-slate-200 p-5 text-center text-[10px] leading-relaxed text-slate-400">{available ? 'Belum ada percakapan dari perangkat belajar.' : 'Riwayat akan muncul setelah EduPad terhubung ke penyimpanan data.'}</div>}
      </div>
      <div className="border-t border-slate-100 px-4 py-2 text-[8px] leading-relaxed text-slate-400">Dashboard hanya menampilkan pertanyaan dan jawaban yang aman untuk dibaca.</div>
    </aside>
  )
}

export default function App() {
  const { snapshot, apiAvailable, realtimeConnected, chatHistory, chatHistoryAvailable, createTask, updateTask } = useOfficeData()
  const [clock, setClock] = useState(new Date())
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null)
  const [taskCenterOpen, setTaskCenterOpen] = useState(false)
  const [modalClosing, setModalClosing] = useState(false)
  const closeTimer = useRef<number | null>(null)
  const selectedAgent = snapshot.agents.find((agent) => agent.id === selectedAgentId)
  const selectedRoom = roomProfiles.find((room) => room.id === selectedRoomId)
  const activeTaskCount = snapshot.tasks.filter((task) => ['queued', 'in_progress'].includes(task.status)).length

  useEffect(() => { const timer = window.setInterval(() => setClock(new Date()), 1000); return () => window.clearInterval(timer) }, [])
  useEffect(() => () => { if (closeTimer.current !== null) window.clearTimeout(closeTimer.current) }, [])

  const resetClose = useCallback(() => {
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current)
    closeTimer.current = null
    setModalClosing(false)
  }, [])
  const openAgent = useCallback((id: string) => { resetClose(); setSelectedRoomId(null); setTaskCenterOpen(false); setSelectedAgentId(id) }, [resetClose])
  const openRoom = useCallback((id: string) => { resetClose(); setSelectedAgentId(null); setTaskCenterOpen(false); setSelectedRoomId(id) }, [resetClose])
  const openTaskCenter = useCallback(() => { resetClose(); setSelectedAgentId(null); setSelectedRoomId(null); setTaskCenterOpen(true) }, [resetClose])
  const closeDetail = useCallback(() => {
    if ((!selectedAgentId && !selectedRoomId && !taskCenterOpen) || modalClosing) return
    setModalClosing(true)
    closeTimer.current = window.setTimeout(() => {
      setSelectedAgentId(null)
      setSelectedRoomId(null)
      setTaskCenterOpen(false)
      setModalClosing(false)
      closeTimer.current = null
    }, 220)
  }, [modalClosing, selectedAgentId, selectedRoomId, taskCenterOpen])

  useEffect(() => {
    if (!selectedAgentId && !selectedRoomId && !taskCenterOpen) return
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') closeDetail() }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [closeDetail, selectedAgentId, selectedRoomId, taskCenterOpen])

  return (
    <div className="office-only-app">
      <header className="office-agent-header">
        <div className="flex shrink-0 items-center gap-2">
          <BrandMark />
          <div className="hidden xl:block"><h1 className="text-sm font-black text-blue-800">EduPad AI Office</h1><p className="text-[8px] text-slate-400">Ruang kerja asisten AI</p></div>
        </div>
        <div className="agent-top-roster">
          {snapshot.agents.map((agent) => <AgentTopCard key={agent.id} agent={agent} onClick={() => openAgent(agent.id)} />)}
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <button type="button" className="task-center-launch" onClick={openTaskCenter} aria-label={`Buka Pusat Tugas, ${activeTaskCount} tugas sedang berjalan`}><TaskIcon /><span>Pusat Tugas</span><b>{activeTaskCount}</b></button>
          <div className="hidden items-center gap-2 rounded-full bg-slate-100 px-2.5 py-1.5 2xl:flex">
            <span className={`h-2 w-2 rounded-full ${realtimeConnected ? 'animate-pulse bg-emerald-400' : apiAvailable ? 'bg-blue-400' : 'bg-amber-400'}`} />
            <span className="text-[8px] font-bold text-slate-500">{realtimeConnected ? 'Terhubung langsung' : apiAvailable ? 'Sistem terhubung' : 'Mode tampilan'}</span>
          </div>
          <div className="text-right"><div className="font-mono text-base font-black leading-none text-blue-950">{clock.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}</div><div className="mt-1 text-[7px] font-bold uppercase text-slate-400">WIB · {clock.toLocaleDateString('id-ID', { day: '2-digit', month: 'short' })}</div></div>
        </div>
      </header>
      <main className="office-workspace">
        <section className="office-floor-pane">
          <Suspense fallback={<div className="grid h-full place-items-center text-xs font-bold uppercase tracking-[.14em] text-blue-500">Memuat kantor virtual…</div>}>
            <OfficeGame agents={snapshot.agents} onAgentSelect={openAgent} onRoomSelect={openRoom} />
          </Suspense>
        </section>
        <ChatHistoryPanel chats={chatHistory} available={chatHistoryAvailable} />
      </main>
      {selectedAgent && <AgentProfileModal agent={selectedAgent} tasks={snapshot.tasks} closing={modalClosing} onClose={closeDetail} onOpenTaskCenter={openTaskCenter} />}
      {selectedRoom && <RoomProfileModal room={selectedRoom} agents={snapshot.agents} tasks={snapshot.tasks} events={snapshot.recent_events} knowledgeHealth={snapshot.metrics.knowledge_health} closing={modalClosing} onClose={closeDetail} />}
      {taskCenterOpen && <TaskCenterModal tasks={snapshot.tasks} agents={snapshot.agents} apiAvailable={apiAvailable} closing={modalClosing} onClose={closeDetail} onCreateTask={createTask} onUpdateTask={updateTask} />}
    </div>
  )
}
