import { useEffect, useRef, useState } from 'react'
import Phaser from 'phaser'

import type { OfficeAgent } from '../types'
import {
  AGENT_SELECTED,
  CAMERA_VIEW_UPDATED,
  ROOM_SELECTED,
  type CameraView,
  officeGameEvents,
} from './events'
import { OFFICE_WORLD_HEIGHT, OFFICE_WORLD_WIDTH, OfficeScene } from './OfficeScene'
import { FurnitureEditor } from './FurnitureEditor'

function CameraIcon({ kind }: { kind: 'minus' | 'plus' | 'fit' }) {
  if (kind === 'minus') return <svg viewBox="0 0 24 24" aria-hidden><path d="M5 12h14" /></svg>
  if (kind === 'plus') return <svg viewBox="0 0 24 24" aria-hidden><path d="M12 5v14M5 12h14" /></svg>
  return (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M8 4H4v4M16 4h4v4M20 16v4h-4M4 16v4h4" />
      <path d="M9 9h6v6H9z" />
    </svg>
  )
}

export function OfficeGame({
  agents,
  onAgentSelect,
  onRoomSelect,
  externalControls = false,
}: {
  agents: OfficeAgent[]
  onAgentSelect?: (agentId: string) => void
  onRoomSelect?: (roomId: string) => void
  externalControls?: boolean
}) {
  const host = useRef<HTMLDivElement>(null)
  const game = useRef<Phaser.Game | null>(null)

  useEffect(() => {
    if (!host.current || game.current) return
    game.current = new Phaser.Game({
      type: Phaser.AUTO,
      parent: host.current,
      width: OFFICE_WORLD_WIDTH,
      height: OFFICE_WORLD_HEIGHT,
      backgroundColor: 'rgba(0, 0, 0, 0)',
      transparent: true,
      pixelArt: true,
      antialias: false,
      roundPixels: true,
      scene: [OfficeScene],
      scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
      audio: { noAudio: true },
      render: { transparent: true, powerPreference: 'high-performance' },
    })
    const observer = new ResizeObserver(() => game.current?.scale.refresh())
    observer.observe(host.current)
    return () => {
      observer.disconnect()
      game.current?.destroy(true)
      game.current = null
    }
  }, [])

  useEffect(() => officeGameEvents.updateAgents(agents), [agents])

  useEffect(() => {
    const handleAgent = (event: Event) =>
      onAgentSelect?.((event as CustomEvent<string>).detail)
    const handleRoom = (event: Event) =>
      onRoomSelect?.((event as CustomEvent<string>).detail)
    officeGameEvents.addEventListener(AGENT_SELECTED, handleAgent)
    officeGameEvents.addEventListener(ROOM_SELECTED, handleRoom)
    return () => {
      officeGameEvents.removeEventListener(AGENT_SELECTED, handleAgent)
      officeGameEvents.removeEventListener(ROOM_SELECTED, handleRoom)
    }
  }, [onAgentSelect, onRoomSelect])

  return (
    <div className="office-game-shell office-owl-game-shell">
      <div ref={host} className="office-canvas" />
      {!externalControls && <OfficeControls />}
    </div>
  )
}

export function OfficeControls() {
  const [cameraView, setCameraView] = useState<CameraView>(() => officeGameEvents.currentCameraView())
  useEffect(() => {
    const handleCamera = (event: Event) => setCameraView((event as CustomEvent<CameraView>).detail)
    officeGameEvents.addEventListener(CAMERA_VIEW_UPDATED, handleCamera)
    setCameraView(officeGameEvents.currentCameraView())
    return () => officeGameEvents.removeEventListener(CAMERA_VIEW_UPDATED, handleCamera)
  }, [])
  return (
    <>
      <FurnitureEditor />
      <div className="office-camera-controls" aria-label="Kontrol kamera kantor" onPointerDown={(event) => event.stopPropagation()} onPointerUp={(event) => event.stopPropagation()} onClick={(event) => event.stopPropagation()}>
        <button
          type="button"
          aria-label="Perkecil kantor"
          disabled={!cameraView.canZoomOut}
          onClick={() => officeGameEvents.changeCameraZoom(-0.2)}
        >
          <CameraIcon kind="minus" />
        </button>
        <span>{Math.round(cameraView.zoom * 100)}%</span>
        <button
          type="button"
          aria-label="Perbesar kantor"
          disabled={!cameraView.canZoomIn}
          onClick={() => officeGameEvents.changeCameraZoom(0.2)}
        >
          <CameraIcon kind="plus" />
        </button>
        <button type="button" aria-label="Tampilkan seluruh kantor" onClick={() => officeGameEvents.resetCamera()}>
          <CameraIcon kind="fit" />
        </button>
      </div>
    </>
  )
}
