import { useState } from "react";
import type { ConversationSession, ConversationTurn } from "../api/types";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { dayHeading, hourLabel, secs } from "../lib/format";
import { owlSrc } from "../lib/owls";

/** Satu giliran: pertanyaan lewat suara, jawaban yang disuarakan, layar LCD, sumber materi. */
function TurnView({ t }: { t: ConversationTurn }) {
  return (
    <article className="turn">
      <div className="turn-q">
        <span className="bubble">
          <Icon name="mic" size={12} />
          {t.question}
        </span>
      </div>
      <div className="turn-a">
        <img className="a-mark a-owl" src={owlSrc("sora")} alt="" aria-hidden width={32} height={32} />
        <div className="a-body">
          <div className="turn-meta mono">
            {hourLabel(t.at)}
            {t.latency_s != null && ` · ${secs(t.latency_s)}`}
            {t.tools.length > 0 && ` · ${t.tools.join(", ")}`}
          </div>
          <p>{t.speech}</p>
          {t.screen.length > 0 && (
            <div className="lcd" aria-label="Tampilan layar perangkat">
              <span className="lcd-label">LCD</span>
              {t.screen.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </div>
          )}
          {t.sources.length > 0 && (
            <div className="pills">
              {t.sources.map((s, i) => (
                <span key={i} className="pill chip" title={s.matkul}>
                  {s.matkul} <b>p{s.pertemuan.join(",")}</b>
                  {s.judul && <> · {s.judul}</>}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

const matches = (s: ConversationSession, q: string) =>
  !q || s.turns.some((t) => `${t.question} ${t.speech}`.toLowerCase().includes(q)) || (s.summary ?? "").toLowerCase().includes(q);

/** Daftar sesi + transkrip sesi terpilih (halaman Riwayat percakapan). */
export function ConversationBrowser() {
  const [selected, setSelected] = useState<number | null>(null);
  const [query, setQuery] = useState("");

  return (
    <Panel panel="conversations" title="Sesi percakapan" subtitle="Sesi baru setelah 30 menit tanpa pertanyaan">
      {(d) => {
        const q = query.trim().toLowerCase();
        const sessions = d.sessions.filter((s) => matches(s, q));
        const current = sessions.find((s) => s.id === selected) ?? sessions[0];
        return (
          <div className="convo">
            <div className="convo-list">
              <label className="field">
                <Icon name="search" size={14} />
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Cari pertanyaan atau jawaban…" aria-label="Cari percakapan" />
              </label>
              {sessions.length ? (
                <ul>
                  {sessions.map((s) => (
                    <li key={s.id}>
                      <button className={`session ${current?.id === s.id ? "active" : ""}`} onClick={() => setSelected(s.id)} aria-current={current?.id === s.id}>
                        <span className="session-head">
                          <span>
                            {dayHeading(s.started_at)} · <span className="mono">{hourLabel(s.started_at)}</span>
                          </span>
                          <span className="mono muted">{s.turns.length}×</span>
                        </span>
                        <span className="clamp-2 cell-sub">{s.summary ?? s.turns[0]?.question ?? "—"}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="empty">Tidak ada percakapan yang cocok.</p>
              )}
            </div>

            <div className="convo-view">
              {current ? (
                <>
                  <header className="convo-head">
                    <div>
                      <div className="cell-strong">{dayHeading(current.started_at)}</div>
                      <div className="cell-sub mono">
                        {hourLabel(current.started_at)}–{hourLabel(current.last_active)} · {current.turns.length} pertanyaan
                      </div>
                    </div>
                  </header>
                  {current.summary && (
                    <p className="note">
                      <b>Ringkasan memory:</b> {current.summary}
                    </p>
                  )}
                  <div className="turns">
                    {current.turns.map((t) => (
                      <TurnView key={t.id} t={t} />
                    ))}
                  </div>
                </>
              ) : (
                <p className="empty">Pilih sesi di kiri.</p>
              )}
            </div>
          </div>
        );
      }}
    </Panel>
  );
}
