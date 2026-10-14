import { useEffect, useRef, useState } from 'react'
import Phaser from 'phaser'

import type { OfficeAgent } from '../types'
import { FURNITURE_CATALOG } from './officeObjects'
import {
  AGENT_SELECTED,
  FURNITURE_SELECTED,
  ROOM_SELECTED,
  officeGameEvents,
} from './events'
import { OfficeScene } from './OfficeScene'

function FurnitureIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8">
      <path d="M5 11V8.5A2.5 2.5 0 0 1 7.5 6h9A2.5 2.5 0 0 1 19 8.5V11" />
      <path d="M4 11h2a2 2 0 0 1 2 2v2h8v-2a2 2 0 0 1 2-2h2v7H4v-7Z" />
      <path d="M7 18v2M17 18v2M12 3v2M9.5 4h5" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 fill-none stroke-current" strokeWidth="1.8">
      <path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5" />
    </svg>
  )
}

function ResetIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 fill-none stroke-current" strokeWidth="1.8">
      <path d="M4 12a8 8 0 1 0 2.34-5.66L4 8.7" /><path d="M4 4v4.7h4.7" />
    </svg>
  )
}

function ChevronIcon({ direction }: { direction: 'up' | 'down' }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={`h-4 w-4 fill-none stroke-current ${direction === 'down' ? 'rotate-180' : ''}`}
      strokeWidth="2"
    >
      <path d="m5 15 7-7 7 7" />
    </svg>
  )
}

function FurnitureThumbnail({ frame }: { frame: number }) {
  const column = frame % 4
  const row = Math.floor(frame / 4)
  return (
    <span
      className="furniture-thumbnail"
      style={{
        backgroundPosition: `${(column / 3) * 100}% ${(row / 3) * 100}%`,
      }}
    />
  )
}

export function OfficeGame({
  agents,
  onAgentSelect,
  onRoomSelect,
}: {
  agents: OfficeAgent[]
  onAgentSelect: (agentId: string) => void
  onRoomSelect: (roomId: string) => void
}) {
  const host = useRef<HTMLDivElement>(null)
  const game = useRef<Phaser.Game | null>(null)
  const [editingFurniture, setEditingFurniture] = useState(false)
  const [paletteCollapsed, setPaletteCollapsed] = useState(false)
  const [selectedFurniture, setSelectedFurniture] = useState<string | null>(null)

  useEffect(() => {
    if (!host.current || game.current) return
    game.current = new Phaser.Game({
      type: Phaser.AUTO,
      parent: host.current,
      width: 960,
      height: 640,
      backgroundColor: '#061224',
      pixelArt: true,
      antialias: false,
      roundPixels: true,
      scene: [OfficeScene],
      scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
      audio: { noAudio: true },
      render: { transparent: false, powerPreference: 'high-performance' },
    })
    return () => {
      game.current?.destroy(true)
      game.current = null
    }
  }, [])

  useEffect(() => {
    officeGameEvents.updateAgents(agents)
  }, [agents])

  useEffect(() => {
    officeGameEvents.setFurnitureEditMode(editingFurniture)
    if (!editingFurniture) {
      setSelectedFurniture(null)
      setPaletteCollapsed(false)
    }
    return () => officeGameEvents.setFurnitureEditMode(false)
  }, [editingFurniture])

  useEffect(() => {
    const handleAgentSelected = (event: Event) => {
      onAgentSelect((event as CustomEvent<string>).detail)
    }
    const handleRoomSelected = (event: Event) => {
      onRoomSelect((event as CustomEvent<string>).detail)
    }
    const handleFurnitureSelected = (event: Event) => {
      setSelectedFurniture((event as CustomEvent<string | null>).detail)
    }
    officeGameEvents.addEventListener(AGENT_SELECTED, handleAgentSelected)
    officeGameEvents.addEventListener(ROOM_SELECTED, handleRoomSelected)
    officeGameEvents.addEventListener(FURNITURE_SELECTED, handleFurnitureSelected)
    return () => {
      officeGameEvents.removeEventListener(AGENT_SELECTED, handleAgentSelected)
      officeGameEvents.removeEventListener(ROOM_SELECTED, handleRoomSelected)
      officeGameEvents.removeEventListener(FURNITURE_SELECTED, handleFurnitureSelected)
    }
  }, [onAgentSelect, onRoomSelect])

  return (
    <div className="relative h-full min-h-0 w-full overflow-hidden">
      <div ref={host} className="office-canvas h-full min-h-0 w-full" />

      <button
        type="button"
        aria-label={editingFurniture ? 'Selesai mengatur furnitur' : 'Atur furnitur'}
        title={editingFurniture ? 'Selesai mengatur furnitur' : 'Atur furnitur'}
        aria-pressed={editingFurniture}
        onClick={() => {
          setEditingFurniture((current) => {
            if (!current) setPaletteCollapsed(false)
            return !current
          })
        }}
        className={`furniture-mode-button ${editingFurniture ? 'is-active' : ''}`}
      >
        {editingFurniture ? <span className="text-xl font-black">✓</span> : <FurnitureIcon />}
      </button>

      {editingFurniture && !paletteCollapsed && (
        <div className="furniture-palette">
          <div className="flex items-center justify-between gap-3 border-b border-white/10 px-3 py-2">
            <div>
              <div className="font-mono text-[9px] font-black uppercase tracking-[.16em] text-cyan-300">Furniture Library</div>
              <div className="mt-0.5 text-[9px] text-slate-400">Klik aset untuk menambah, lalu seret di dalam kantor.</div>
            </div>
            <div className="flex gap-1.5">
              <button
                type="button"
                onClick={() => setPaletteCollapsed(true)}
                className="furniture-tool-button text-cyan-200"
                aria-label="Sembunyikan panel furnitur"
                title="Sembunyikan panel furnitur"
              >
                <ChevronIcon direction="down" />
              </button>
              <button
                type="button"
                disabled={!selectedFurniture}
                onClick={() => selectedFurniture && officeGameEvents.deleteFurniture(selectedFurniture)}
                className="furniture-tool-button text-rose-300 disabled:text-slate-600"
                aria-label="Hapus furnitur terpilih"
                title="Hapus furnitur terpilih"
              >
                <TrashIcon />
              </button>
              <button
                type="button"
                onClick={() => officeGameEvents.resetFurnitureLayout()}
                className="furniture-tool-button text-amber-200"
                aria-label="Reset seluruh furnitur"
                title="Reset seluruh furnitur"
              >
                <ResetIcon />
              </button>
            </div>
          </div>
          <div className="furniture-catalog-grid">
            {FURNITURE_CATALOG.map((name, frame) => (
              <button
                type="button"
                key={name}
                onClick={() => officeGameEvents.addFurniture(frame)}
                className="furniture-catalog-item"
                title={`Tambah ${name}`}
              >
                <FurnitureThumbnail frame={frame} />
                <span>{name}</span>
              </button>
            ))}
          </div>
          <div className="border-t border-white/10 px-3 py-1.5 font-mono text-[8px] text-slate-500">
            {selectedFurniture ? `Dipilih: ${selectedFurniture}` : 'Pilih furnitur di peta untuk memindahkan atau menghapusnya.'}
          </div>
        </div>
      )}

      {editingFurniture && paletteCollapsed && (
        <button
          type="button"
          onClick={() => setPaletteCollapsed(false)}
          className="furniture-palette-reopen"
          aria-label="Tampilkan panel furnitur"
          title="Tampilkan panel furnitur"
        >
          <ChevronIcon direction="up" />
          <span>Furnitur</span>
        </button>
      )}
    </div>
  )
}
