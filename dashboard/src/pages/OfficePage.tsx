import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";

import { OfficeControls, OfficeGame } from "../../../frontend/src/game/OfficeGame";
import { useOfficeData } from "../../../frontend/src/hooks/useOfficeData";
import type { AgentState, OfficeAgent, OfficeTask } from "../../../frontend/src/types";
import { FURNITURE_EDIT_MODE_UPDATED, FURNITURE_LAYOUT_UPDATED, FURNITURE_SELECTED, officeGameEvents } from "../../../frontend/src/game/events";
import { FURNITURE, HOME_ROOM, furnitureUrl, roomAt, type FurnitureItem } from "../../../frontend/src/game/owlLayout";

type DetailTab = "summary" | "tasks";

const ROOM_INFO: Record<string, { name: string; eyebrow: string; description: string; function: string }> = {
  "command-center": {
    name: "Command Center",
    eyebrow: "PUSAT KOORDINASI",
    description: "Di Command Center, layar-layar pemantauan menyala seperti meja kendali sebuah perpustakaan yang tidak pernah tidur. Inilah tempat NOVA melihat kabar dari seluruh kantor, mengenali pekerjaan baru, lalu menunjukkan ke mana pekerjaan itu perlu diarahkan. Ketika belum ada permintaan, ruangan ini tetap menjadi titik untuk melihat kondisi EduPad secara keseluruhan.",
    function: "Koordinasi layanan dan pemantauan sistem EduPad",
  },
  "research-lab": {
    name: "Research Lab",
    eyebrow: "PENGOLAHAN MATERI",
    description: "Research Lab adalah meja baca yang mengubah tumpukan materi kuliah menjadi pengetahuan yang lebih mudah ditemukan. PIXEL menelaah dokumen di sini sebelum sebuah proses indexing membawanya ke Knowledge Server. Buku, catatan, dan layar riset menjadi pengingat bahwa jawaban belajar yang baik berawal dari materi yang tertata.",
    function: "Riset, ekstraksi dokumen, dan persiapan materi",
  },
  "tutor-room": {
    name: "Tutor Room",
    eyebrow: "ASISTEN BELAJAR",
    description: "Tutor Room terasa seperti ruang konsultasi kecil yang selalu siap menerima pertanyaan. SORA menyiapkan penjelasan dengan merujuk pada materi yang tersedia, lalu membantu mahasiswa memahami bagian yang masih membingungkan. Ketika belum ada pertanyaan, ruangan ini menjadi tempat membaca dan menyusun cara bercerita yang lebih jelas.",
    function: "Tanya jawab pembelajaran berbasis pengetahuan",
  },
  "planning-hub": {
    name: "Planning Hub",
    eyebrow: "PERENCANAAN BELAJAR",
    description: "Di Planning Hub, kalender dan catatan ditempatkan berdampingan supaya hari-hari kuliah tidak terasa berantakan. TEMPO memperhatikan jadwal, tugas, dan tenggat yang diketahui EduPad, lalu membantu menyusunnya menjadi langkah belajar yang masuk akal. Ruangan ini mengingatkan bahwa rencana yang rapi memberi ruang untuk beristirahat juga.",
    function: "Jadwal, tugas, presensi, dan pengingat",
  },
  "analytics-room": {
    name: "Analytics Room",
    eyebrow: "PROGRES BELAJAR",
    description: "Analytics Room adalah tempat angka-angka belajar dibaca sebagai sebuah perjalanan, bukan sekadar grafik. METRIC melihat aktivitas yang benar-benar tercatat di EduPad dan membantu merangkum perubahan dari waktu ke waktu. Jika datanya belum tersedia, ruang ini tidak akan berpura-pura mengetahui kemajuan mahasiswa.",
    function: "Analisis progres dan ringkasan pembelajaran",
  },
  "finance-office": {
    name: "Finance Office",
    eyebrow: "KEUANGAN MAHASISWA",
    description: "Finance Office menjadi sudut yang tenang untuk memikirkan uang saku, pengeluaran, dan rencana keuangan mahasiswa. KOIN membantu menata catatan yang diberikan pengguna agar anggaran dan laporan lebih mudah dibaca. Tidak ada transaksi yang dianggap terjadi hanya karena owl ini bergerak di kantor virtual.",
    function: "Anggaran, transaksi, dan laporan keuangan",
  },
  "knowledge-server": {
    name: "Knowledge Server",
    eyebrow: "PUSAT PENGETAHUAN",
    description: "Di Knowledge Server, rak-rak data berdiri rapat sebagai lambang tempat EduPad menyimpan jejak materi yang telah diproses. NEXUS memantau kesiapan ruang ini, sementara PIXEL datang saat tugas indexing sungguhan berjalan di backend. Lampu server adalah bagian dari cerita visual; hasil proses tetap mengikuti status sistem yang sebenarnya.",
    function: "Indexing, penyimpanan, dan kesehatan pengetahuan",
  },
};

const AGENT_DESCRIPTIONS: Record<string, string> = {
  coordinator: "NOVA adalah owl penjaga meja kendali. Dari Command Center ia memperhatikan kabar yang datang dari kantor EduPad dan membantu menunjukkan pekerja mana yang paling tepat untuk menanganinya. Saat suasana sepi, ia merapikan headset dan berkeliling sebentar, tetapi status pekerjaannya tetap mengikuti kabar nyata dari backend.",
  researcher: "PIXEL paling betah di antara buku dan dokumen Research Lab. Ia menelaah materi kuliah, lalu berpindah ke Knowledge Server ketika tugas indexing benar-benar diterima oleh sistem. Selesai bekerja, PIXEL kembali membaca dan menunggu materi berikutnya tanpa berpura-pura masih memproses tugas.",
  tutor: "SORA menyukai pertanyaan yang membuat orang berhenti dan berpikir. Dari Tutor Room ia membantu menyampaikan penjelasan belajar dengan bahasa yang lebih dekat bagi mahasiswa dan merujuk pada materi yang tersedia. Pada waktu tenang, ia membuka buku cerita sambil menyiapkan cara menjelaskan yang lebih sederhana.",
  planner: "TEMPO melihat kalender sebagai peta perjalanan belajar, bukan kumpulan kotak tanggal. Di Planning Hub ia membantu menghubungkan jadwal, tugas, dan tenggat yang diketahui EduPad agar mahasiswa dapat menentukan prioritas. Setelah itu ia meregangkan sayap dan berjalan sebentar sebelum kembali ke meja.",
  analyst: "METRIC senang mencari makna di balik grafik. Dari Analytics Room ia membaca aktivitas belajar yang memang tercatat, lalu membantu merangkumnya menjadi gambaran perkembangan yang mudah dipahami. Bila catatan belum cukup, METRIC menunggu data baru alih-alih mengarang sebuah kemajuan.",
  finance: "KOIN menemani mahasiswa menata cerita di balik uang saku mereka. Di Finance Office ia membantu membaca catatan pemasukan, pengeluaran, dan anggaran yang diberikan pengguna sehingga keputusan sehari-hari terasa lebih jelas. Saat tidak ada catatan baru, ia menikmati jeda kecil di dekat meja kerjanya.",
  keeper: "NEXUS adalah penjaga rak pengetahuan EduPad. Ia mengawasi representasi server dan kesiapan sumber data yang ditampilkan kantor, sementara proses indexing sesungguhnya tetap dikerjakan oleh fungsi backend yang telah ada. Di sela pekerjaan, ia berjalan memeriksa rak dan mendengarkan musik sebentar.",
};

const OWL_SHEETS: Record<string, string> = {
  coordinator: "/assets/agents/owls/nova-owl-sheet-v1.png",
  researcher: "/assets/agents/owls/pixel-owl-sheet-v1.png",
  tutor: "/assets/agents/owls/sora-owl-sheet-v1.png",
  planner: "/assets/agents/owls/tempo-owl-sheet-v1.png",
  analyst: "/assets/agents/owls/metric-owl-sheet-v1.png",
  finance: "/assets/agents/owls/koin-owl-sheet-v1.png",
  keeper: "/assets/agents/owls/nexus-owl-sheet-v1.png",
};

const AGENT_ORDER = ["coordinator", "researcher", "tutor", "planner", "analyst", "finance", "keeper"];

const STATE_LABELS: Record<AgentState, string> = {
  offline: "Tidak terhubung",
  idle: "Siap membantu",
  queued: "Menunggu giliran",
  running: "Sedang bekerja",
  waiting: "Menunggu data",
  succeeded: "Pekerjaan selesai",
  failed: "Perlu diperiksa",
  cancelled: "Dibatalkan",
};

function taskStatusLabel(status: OfficeTask["status"]) {
  return {
    queued: "Menunggu",
    in_progress: "Diproses",
    completed: "Selesai",
    failed: "Gagal",
    cancelled: "Dibatalkan",
  }[status];
}

function readableTime(value?: string | null) {
  if (!value) return "Belum ada pembaruan";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Waktu tidak tersedia";
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function OfficePage() {
  const { snapshot, apiAvailable } = useOfficeData();
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>("summary");
  const [layout, setLayout] = useState<FurnitureItem[]>(() => officeGameEvents.currentFurnitureLayout());
  const [selectedFurnitureId, setSelectedFurnitureId] = useState<string | null>(null);
  const [editingFurniture, setEditingFurniture] = useState(() => officeGameEvents.currentFurnitureEditMode());
  const selectedFurniture = layout.find(item => item.id === selectedFurnitureId) ?? null;
  const isPreview = !apiAvailable;
  const tasks = isPreview ? [] : snapshot.tasks;
  const orderedAgents = useMemo(
    () => [...snapshot.agents].sort((a, b) => AGENT_ORDER.indexOf(a.id) - AGENT_ORDER.indexOf(b.id)),
    [snapshot.agents],
  );

  useEffect(() => {
    const update = (event: Event) => setLayout((event as CustomEvent<FurnitureItem[]>).detail);
    const select = (event: Event) => {
      if (officeGameEvents.currentFurnitureEditMode()) return;
      setSelectedFurnitureId((event as CustomEvent<string | null>).detail);
      setSelectedAgentId(null);
      setSelectedRoomId(null);
    };
    officeGameEvents.addEventListener(FURNITURE_LAYOUT_UPDATED, update);
    officeGameEvents.addEventListener(FURNITURE_SELECTED, select);
    return () => {
      officeGameEvents.removeEventListener(FURNITURE_LAYOUT_UPDATED, update);
      officeGameEvents.removeEventListener(FURNITURE_SELECTED, select);
    };
  }, []);

  useEffect(() => {
    const update = (event: Event) => setEditingFurniture((event as CustomEvent<boolean>).detail);
    officeGameEvents.addEventListener(FURNITURE_EDIT_MODE_UPDATED, update);
    return () => officeGameEvents.removeEventListener(FURNITURE_EDIT_MODE_UPDATED, update);
  }, []);

  const selectedAgent = useMemo(
    () => snapshot.agents.find((agent) => agent.id === selectedAgentId) ?? null,
    [selectedAgentId, snapshot.agents],
  );
  const selectedRoom = selectedRoomId ? ROOM_INFO[selectedRoomId] : null;
  const roomAgents = useMemo(
    () => snapshot.agents.filter((agent) => HOME_ROOM[agent.id] === selectedRoomId),
    [selectedRoomId, snapshot.agents],
  );
  const selectedAgentTasks = useMemo(
    () => tasks.filter((task) => task.assigned_agent === selectedAgentId),
    [selectedAgentId, tasks],
  );
  const roomTasks = useMemo(() => {
    const agentIds = new Set(roomAgents.map((agent) => agent.id));
    return tasks.filter((task) => agentIds.has(task.assigned_agent));
  }, [roomAgents, tasks]);

  const closeDetail = () => {
    setSelectedAgentId(null);
    setSelectedRoomId(null);
    setSelectedFurnitureId(null);
  };

  const openAgentDetail = (agentId: string) => {
    setDetailTab("summary");
    setSelectedAgentId(agentId);
    setSelectedRoomId(null);
    setSelectedFurnitureId(null);
  };

  useEffect(() => {
    if (!selectedAgent && !selectedRoom && !selectedFurniture) return;
    officeGameEvents.blockOfficeInput(true);
    const previousFocus = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>('.office-detail-modal');
    dialog?.querySelector<HTMLButtonElement>('button')?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeDetail();
      if (event.key === 'Tab' && dialog) {
        const focusable = Array.from(dialog.querySelectorAll<HTMLElement>('button, [href], [tabindex="0"]'));
        const first = focusable[0], last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => { window.removeEventListener("keydown", closeOnEscape); officeGameEvents.blockOfficeInput(false); previousFocus?.focus(); };
  }, [selectedAgentId, selectedRoomId, selectedFurnitureId]);

  return (
    <main className={`office-world-page ${editingFurniture ? "is-editing-furniture" : ""}`}>
      <section className="office-world-stage" aria-label="Kantor virtual EduPad AI">
        <OfficeGame
          externalControls
          agents={snapshot.agents}
          onAgentSelect={openAgentDetail}
          onRoomSelect={(roomId) => {
            setDetailTab("summary");
            setSelectedRoomId(roomId);
            setSelectedAgentId(null);
            setSelectedFurnitureId(null);
          }}
        />


      </section>
      <aside className="office-world-toolbar" aria-label="Alat kantor virtual"><OfficeControls /></aside>

      <nav className="office-agent-dock" aria-label="Pekerja AI di kantor">
        {orderedAgents.map((agent) => (
          <button
            type="button"
            key={agent.id}
            className={`office-agent-tab state-${agent.state}`}
            style={{ "--agent-color": agent.color } as CSSProperties}
            onClick={() => openAgentDetail(agent.id)}
            aria-label={`Buka detail ${agent.name}`}
          >
            <span
              className="office-agent-tab-avatar"
              style={{ backgroundImage: `url(${OWL_SHEETS[agent.id]})` }}
              aria-hidden
            />
            <span className="office-agent-tab-copy">
              <strong>{agent.name}</strong>
              <small>{agent.role}</small>
            </span>
            <span className="office-agent-tab-state">
              <i aria-hidden />
              {STATE_LABELS[agent.state]}
            </span>
          </button>
        ))}
      </nav>

      {(selectedAgent || selectedRoom || selectedFurniture) && createPortal(
        <div className="office-detail-backdrop" role="presentation" onMouseDown={closeDetail}>
          <section
            className="office-detail-modal"
            role="dialog"
            aria-modal="true"
            aria-label={selectedFurniture ? `Detail ${FURNITURE[selectedFurniture.frame].name}` : selectedAgent ? `Detail ${selectedAgent.name}` : `Detail ${selectedRoom?.name}`}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button type="button" className="office-detail-close" onClick={closeDetail} aria-label="Tutup detail">×</button>

            {selectedFurniture ? (
              <FurnitureDetail item={selectedFurniture} onEdit={() => { closeDetail(); officeGameEvents.setFurnitureEditMode(true); officeGameEvents.selectFurniture(selectedFurniture.id); }} />
            ) : selectedAgent ? (
              <AgentDetail agent={selectedAgent} tasks={selectedAgentTasks} tab={detailTab} onTabChange={setDetailTab} />
            ) : selectedRoom ? (
              <RoomDetail room={selectedRoom} agents={roomAgents} tasks={roomTasks} tab={detailTab} onTabChange={setDetailTab} furniture={layout.find(item => item.owner && HOME_ROOM[item.owner] === selectedRoomId)} />
            ) : null}
          </section>
        </div>
      , document.body)}
    </main>
  );
}

function DetailTabs({ tab, onChange }: { tab: DetailTab; onChange: (tab: DetailTab) => void }) {
  return (
    <div className="office-detail-tabs" role="tablist" aria-label="Bagian detail">
      <button type="button" className={tab === "summary" ? "active" : ""} onClick={() => onChange("summary")}>Ringkasan</button>
      <button type="button" className={tab === "tasks" ? "active" : ""} onClick={() => onChange("tasks")}>Riwayat tugas</button>
    </div>
  );
}

function AgentDetail({ agent, tasks, tab, onTabChange }: { agent: OfficeAgent; tasks: OfficeTask[]; tab: DetailTab; onTabChange: (tab: DetailTab) => void }) {
  const completed = tasks.filter((task) => task.status === "completed").length;
  const failed = tasks.filter((task) => task.status === "failed").length;
  const active = tasks.filter((task) => task.status === "queued" || task.status === "in_progress").length;

  return (
    <>
      <aside className="office-detail-visual" style={{ "--agent-accent": agent.color } as CSSProperties}>
        <div className="office-detail-sprite" style={{ backgroundImage: `url(${OWL_SHEETS[agent.id]})` }} />
        <span className={`office-state-dot state-${agent.state}`} />
        <h2>{agent.name}</h2>
        <p>{agent.role}</p>
        <small>{ROOM_INFO[agent.room]?.name ?? agent.room}</small>
      </aside>
      <div className="office-detail-content">
        <DetailTabs tab={tab} onChange={onTabChange} />
        {tab === "summary" ? (
          <>
            <span className="office-detail-eyebrow">PEKERJA AI</span>
            <h1>{agent.name}</h1>
            <p className="office-detail-description office-story-paragraph">{AGENT_DESCRIPTIONS[agent.id] ?? agent.role}</p>
            <div className="office-detail-metrics">
              <Metric label="Status saat ini" value={STATE_LABELS[agent.state]} />
              <Metric label="Tugas tercatat" value={String(tasks.length)} />
              <Metric label="Selesai" value={String(completed)} tone="good" />
              <Metric label="Perlu diperiksa" value={String(failed)} tone={failed ? "bad" : undefined} />
            </div>
            <div className="office-current-work">
              <span style={{ background: agent.color }} />
              <div><small>Aktivitas saat ini</small><strong>{agent.task || STATE_LABELS[agent.state]}</strong></div>
              <b>{agent.progress > 0 && agent.progress < 100 ? `${agent.progress}%` : active ? "AKTIF" : STATE_LABELS[agent.state]}</b>
            </div>
            <p className="office-detail-updated">Pembaruan terakhir {readableTime(agent.updated_at)}</p>
          </>
        ) : (
          <TaskHistory tasks={tasks} emptyText={`${agent.name} belum memiliki riwayat tugas.`} />
        )}
      </div>
    </>
  );
}

function RoomDetail({ room, agents, tasks, tab, onTabChange, furniture }: { room: (typeof ROOM_INFO)[string]; agents: OfficeAgent[]; tasks: OfficeTask[]; tab: DetailTab; onTabChange: (tab: DetailTab) => void; furniture?: FurnitureItem }) {
  const active = agents.filter((agent) => ["queued", "running", "waiting"].includes(agent.state)).length;
  const completed = tasks.filter((task) => task.status === "completed").length;
  const failed = tasks.filter((task) => task.status === "failed").length;

  return (
    <>
      <aside className="office-detail-visual office-room-visual">
        {furniture ? <img className="office-furniture-portrait" src={furnitureUrl(furniture.frame)} alt={FURNITURE[furniture.frame].name} /> : <div className="office-room-mark"><span>{room.name.split(" ").map((word) => word[0]).join("")}</span></div>}
        <span className="office-detail-eyebrow">{room.eyebrow}</span>
        <h2>{room.name}</h2>
        <p>{room.function}</p>
        <div className="office-room-agents">
          {agents.length ? agents.map((agent) => <span key={agent.id} style={{ borderColor: agent.color }}>{agent.name}</span>) : <span>Belum ada agent di ruangan</span>}
        </div>
      </aside>
      <div className="office-detail-content">
        <DetailTabs tab={tab} onChange={onTabChange} />
        {tab === "summary" ? (
          <>
            <span className="office-detail-eyebrow">{room.eyebrow}</span>
            <h1>{room.name}</h1>
            <p className="office-detail-description office-story-paragraph">{room.description}</p>
            <div className="office-detail-metrics">
              <Metric label="Pekerja di ruangan" value={String(agents.length)} />
              <Metric label="Sedang aktif" value={String(active)} />
              <Metric label="Tugas selesai" value={String(completed)} tone="good" />
              <Metric label="Perlu diperiksa" value={String(failed)} tone={failed ? "bad" : undefined} />
            </div>
            <div className="office-current-work office-room-purpose">
              <span />
              <div><small>Fungsi utama</small><strong>{room.function}</strong></div>
            </div>
          </>
        ) : (
          <TaskHistory tasks={tasks} emptyText={`Belum ada tugas tercatat untuk ${room.name}.`} />
        )}
      </div>
    </>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  return <div className={`office-detail-metric ${tone ? `is-${tone}` : ""}`}><span>{label}</span><strong>{value}</strong></div>;
}

function FurnitureDetail({ item, onEdit }: { item: FurnitureItem; onEdit: () => void }) {
  const spec = FURNITURE[item.frame];
  const room = roomAt(item);
  return <>
    <aside className="office-detail-visual office-room-visual">
      <img className="office-furniture-portrait" src={furnitureUrl(item.frame)} alt={spec.name} />
      <span className="office-detail-eyebrow">FURNITUR KANTOR</span>
      <h2>{spec.name}</h2><p>{spec.category}</p>
    </aside>
    <div className="office-detail-content office-furniture-description">
      <span className="office-detail-eyebrow">OBJEK TERPILIH</span>
      <h1>{spec.name}</h1>
      <p className="office-detail-description">{spec.description}</p>
      <div className="office-detail-metrics">
        <Metric label="Letak" value={room?.label ?? 'Koridor bersama'} />
        <Metric label="Kategori" value={spec.category} />
      </div>
      <div className="office-current-work office-room-purpose"><span /><div><small>Jalur berjalan</small><strong>Owl akan menghindari objek ini saat berjalan.</strong></div></div>
      <p className="office-detail-description">Gunakan studio furnitur untuk menggeser atau menghapus objek ini. Pintu dan akses meja kerja harus tetap terbuka.</p>
      <button type="button" className="office-furniture-edit-button" onClick={onEdit}>Atur posisi furnitur →</button>
    </div>
  </>;
}

function TaskHistory({ tasks, emptyText }: { tasks: OfficeTask[]; emptyText: string }) {
  if (!tasks.length) return <div className="office-task-empty"><strong>Belum ada riwayat tugas</strong><span>{emptyText}</span></div>;
  return (
    <div className="office-task-history">
      <div><span className="office-detail-eyebrow">RIWAYAT NYATA</span><h1>Tugas agent</h1><p>Data berikut berasal dari Office API.</p></div>
      <div className="office-task-list">
        {tasks.slice(0, 8).map((task) => (
          <article key={task.id}>
            <div><strong>{task.title}</strong><span>{task.description || "Tanpa keterangan tambahan"}</span></div>
            <aside><b className={`task-${task.status}`}>{taskStatusLabel(task.status)}</b><small>{readableTime(task.updated_at)}</small></aside>
          </article>
        ))}
      </div>
    </div>
  );
}
