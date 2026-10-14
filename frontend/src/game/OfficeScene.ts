import Phaser from 'phaser'

import type { AgentState, OfficeAgent } from '../types'
import { AgentStateMachine, type AgentVisualState } from './AgentStateMachine'
import {
  AGENTS_UPDATED,
  FURNITURE_ADD_REQUESTED,
  FURNITURE_DELETE_REQUESTED,
  FURNITURE_EDIT_MODE_UPDATED,
  FURNITURE_LAYOUT_RESET,
  officeGameEvents,
} from './events'
import { IDLE_PATROLS, routeBetweenRooms, routeFromCorridor } from './navigation'
import {
  FURNITURE_CONTENT_SIZE,
  OFFICE_OBJECTS,
  type OfficeObject,
} from './officeObjects'
import { WALL_OCCLUDERS } from './officeWalls'
import {
  AGENT_WORKSTATION_IDS,
  WORKSTATIONS,
  type Point,
  type Workstation,
} from './workstations'

type Room = {
  id: string
  number: string
  label: string
  x: number
  y: number
  width: number
  height: number
  accent: number
  anchor: Point
}

type Bot = {
  agentId: string
  container: Phaser.GameObjects.Container
  body: Phaser.GameObjects.Rectangle
  antenna: Phaser.GameObjects.Rectangle
  leftArm: Phaser.GameObjects.Rectangle
  rightArm: Phaser.GameObjects.Rectangle
  leftLeg: Phaser.GameObjects.Rectangle
  rightLeg: Phaser.GameObjects.Rectangle
  pixelSprite: Phaser.GameObjects.Sprite | null
  statusRing: Phaser.GameObjects.Ellipse
  selectionPulse: Phaser.GameObjects.Ellipse
  speechBubble: Phaser.GameObjects.Graphics
  activityText: Phaser.GameObjects.Text
  defaultActivity: string
  room: string
  state: AgentState
  machine: AgentStateMachine
  pendingTerminal: AgentVisualState | null
  lastUpdate: string
  motionToken: number
  roamTimer: Phaser.Time.TimerEvent | null
  travelingToWorkstation: boolean
  idleActivityIndex: number
}

type WalkDirection = 'down' | 'left' | 'right' | 'up'

const MAP_KEY = 'edupad-office-shell'
const FURNITURE_KEY = 'edupad-office-furniture'
const WALL_KEY = 'edupad-office-walls'
const PIXEL_WALK_KEY = 'pixel-walk-sheet'
const PIXEL_ACTION_KEY = 'pixel-action-sheet'
const PIXEL_WORK_KEY = 'pixel-work-sheet'
const SHEET_FRAME_SIZE = 313
const FURNITURE_FRAME_SIZE = 384
const BOT_SPRITE_SIZE = 60
const FURNITURE_LAYOUT_STORAGE_KEY = 'edupad-office-furniture-layout-v1'
const FURNITURE_CUSTOM_STORAGE_KEY = 'edupad-office-furniture-custom-v1'
const FURNITURE_REMOVED_STORAGE_KEY = 'edupad-office-furniture-removed-v1'

const PRIMARY_ROOM_ASSETS = new Map<string, string>([
  ['command-console', 'command-center'],
  ['research-workbench', 'research-lab'],
  ['tutor-desk', 'tutor-room'],
  ['planning-desk', 'planning-hub'],
  ['analytics-console', 'analytics-room'],
  ['server-rack-02', 'knowledge-server'],
])

const ROOMS: Room[] = [
  { id: 'command-center', number: '01', label: 'COMMAND CENTER', x: 24, y: 34, width: 288, height: 230, accent: 0x22d3ee, anchor: { x: 168, y: 218 } },
  { id: 'research-lab', number: '02', label: 'RESEARCH LAB', x: 336, y: 34, width: 288, height: 230, accent: 0x60a5fa, anchor: { x: 480, y: 218 } },
  { id: 'tutor-room', number: '03', label: 'TUTOR ROOM', x: 648, y: 34, width: 288, height: 230, accent: 0x34d399, anchor: { x: 792, y: 218 } },
  { id: 'planning-hub', number: '04', label: 'PLANNING HUB', x: 24, y: 380, width: 288, height: 226, accent: 0xf59e0b, anchor: { x: 168, y: 548 } },
  { id: 'analytics-room', number: '05', label: 'ANALYTICS ROOM', x: 336, y: 380, width: 288, height: 226, accent: 0xa78bfa, anchor: { x: 480, y: 548 } },
  { id: 'knowledge-server', number: '06', label: 'KNOWLEDGE SERVER', x: 648, y: 380, width: 288, height: 226, accent: 0x38bdf8, anchor: { x: 792, y: 548 } },
]

const WORK_ANIMATION_BY_AGENT: Record<string, string> = {
  coordinator: 'pixel-work-desk',
  researcher: 'pixel-work-desk',
  tutor: 'pixel-work-tutor',
  planner: 'pixel-work-documents',
  analyst: 'pixel-work-desk',
  keeper: 'pixel-work-server',
}

const IDLE_ACTIVITY_ANIMATION_BY_AGENT: Record<string, string> = {
  coordinator: 'pixel-work-desk',
  researcher: 'pixel-work-documents',
  tutor: 'pixel-work-tutor',
  planner: 'pixel-work-documents',
  analyst: 'pixel-work-desk',
  keeper: 'pixel-work-server',
}

const IDLE_ACTIVITY_TEXT_BY_AGENT: Record<string, string> = {
  coordinator: 'Mengecek konsol',
  researcher: 'Membaca materi',
  tutor: 'Menyiapkan penjelasan',
  planner: 'Menata jadwal',
  analyst: 'Mengecek data',
  keeper: 'Memeriksa server',
}

const stateColor: Record<AgentState, number> = {
  offline: 0x64748b,
  idle: 0x38bdf8,
  queued: 0xa78bfa,
  running: 0x22d3ee,
  waiting: 0xfacc15,
  succeeded: 0x34d399,
  failed: 0xfb7185,
  cancelled: 0x94a3b8,
}

const HOME_ROOMS: Record<string, string> = {
  coordinator: 'command-center',
  researcher: 'research-lab',
  tutor: 'tutor-room',
  planner: 'planning-hub',
  analyst: 'analytics-room',
  keeper: 'knowledge-server',
}

export class OfficeScene extends Phaser.Scene {
  private bots = new Map<string, Bot>()
  private furnitureSprites = new Map<string, Phaser.GameObjects.Sprite>()
  private furnitureEditorLabel: Phaser.GameObjects.Text | null = null
  private furnitureEditMode = false
  private selectedFurnitureId: string | null = null
  private customFurniture: OfficeObject[] = []
  private removedFurniture = new Set<string>()
  private roomLabels = new Map<string, Phaser.GameObjects.Container>()
  private hoveredRoomId: string | null = null
  private readonly reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  private readonly handleAgents = (event: Event) => {
    this.updateAgents((event as CustomEvent<OfficeAgent[]>).detail)
  }
  private readonly handleFurnitureEditMode = (event: Event) => {
    this.setFurnitureEditMode((event as CustomEvent<boolean>).detail)
  }
  private readonly handleFurnitureLayoutReset = () => {
    this.resetFurnitureLayout()
  }
  private readonly handleFurnitureAdd = (event: Event) => {
    this.addFurniture((event as CustomEvent<number>).detail)
  }
  private readonly handleFurnitureDelete = (event: Event) => {
    this.deleteFurniture((event as CustomEvent<string>).detail)
  }

  constructor() {
    super('office')
  }

  preload() {
    this.load.image(MAP_KEY, '/assets/office/edupad-office-shell-v2.png')
    this.load.spritesheet(FURNITURE_KEY, '/assets/office/office-furniture-atlas-v2.png', {
      frameWidth: FURNITURE_FRAME_SIZE,
      frameHeight: FURNITURE_FRAME_SIZE,
      endFrame: 15,
    })
    this.load.image(WALL_KEY, '/assets/office/edupad-office-walls-v1.png')
    this.load.spritesheet(PIXEL_WALK_KEY, '/assets/agents/pixel/pixel-walk-v1.png', {
      frameWidth: SHEET_FRAME_SIZE,
      frameHeight: SHEET_FRAME_SIZE,
      endFrame: 15,
    })
    this.load.spritesheet(PIXEL_ACTION_KEY, '/assets/agents/pixel/pixel-actions-seated-v2.png', {
      frameWidth: SHEET_FRAME_SIZE,
      frameHeight: SHEET_FRAME_SIZE,
      endFrame: 15,
    })
    this.load.spritesheet(PIXEL_WORK_KEY, '/assets/agents/pixel/pixel-work-actions-v1.png', {
      frameWidth: SHEET_FRAME_SIZE,
      frameHeight: SHEET_FRAME_SIZE,
      endFrame: 15,
    })
  }

  create() {
    this.cameras.main.setBackgroundColor('#061224')
    this.drawEnvironment()
    this.drawRoomHitAreas()
    this.drawOfficeObjects()
    this.drawWallOccluders()
    this.createPixelAnimations()
    this.drawRoomLabels()
    this.drawAmbientTechnology()
    this.createFurnitureEditorLabel()
    this.input.on('pointermove', this.handleRoomPointer, this)
    this.input.on('gameout', this.hideRoomLabel, this)

    officeGameEvents.addEventListener(AGENTS_UPDATED, this.handleAgents)
    officeGameEvents.addEventListener(
      FURNITURE_EDIT_MODE_UPDATED,
      this.handleFurnitureEditMode,
    )
    officeGameEvents.addEventListener(FURNITURE_LAYOUT_RESET, this.handleFurnitureLayoutReset)
    officeGameEvents.addEventListener(FURNITURE_ADD_REQUESTED, this.handleFurnitureAdd)
    officeGameEvents.addEventListener(FURNITURE_DELETE_REQUESTED, this.handleFurnitureDelete)
    this.setFurnitureEditMode(officeGameEvents.currentFurnitureEditMode())
    this.updateAgents(officeGameEvents.currentAgents())
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      officeGameEvents.removeEventListener(AGENTS_UPDATED, this.handleAgents)
      officeGameEvents.removeEventListener(
        FURNITURE_EDIT_MODE_UPDATED,
        this.handleFurnitureEditMode,
      )
      officeGameEvents.removeEventListener(
        FURNITURE_LAYOUT_RESET,
        this.handleFurnitureLayoutReset,
      )
      officeGameEvents.removeEventListener(FURNITURE_ADD_REQUESTED, this.handleFurnitureAdd)
      officeGameEvents.removeEventListener(
        FURNITURE_DELETE_REQUESTED,
        this.handleFurnitureDelete,
      )
      this.input.off('pointermove', this.handleRoomPointer, this)
      this.input.off('gameout', this.hideRoomLabel, this)
    })
  }

  private drawEnvironment() {
    if (this.textures.exists(MAP_KEY)) {
      this.add.image(0, 0, MAP_KEY).setOrigin(0).setDisplaySize(960, 640).setDepth(-100)
      return
    }

    const fallback = this.add.graphics().setDepth(-100)
    fallback.fillStyle(0x07182a, 1).fillRect(0, 0, 960, 640)
    ROOMS.forEach((room) => {
      fallback.fillStyle(0x0d2943, 1).fillRect(room.x, room.y, room.width, room.height)
      fallback.lineStyle(3, room.accent, 0.7).strokeRect(room.x, room.y, room.width, room.height)
    })
    fallback.fillStyle(0x183b57, 1).fillRect(0, 280, 960, 82)
  }

  private drawRoomHitAreas() {
    ROOMS.forEach((room) => {
      this.add
        .zone(room.x + room.width / 2, room.y + room.height / 2, room.width, room.height)
        .setDepth(-50)
        .setInteractive({ useHandCursor: true })
        .on('pointerdown', () => {
          if (!this.furnitureEditMode) officeGameEvents.selectRoom(room.id)
        })
    })
  }

  private drawOfficeObjects() {
    if (!this.textures.exists(FURNITURE_KEY)) return
    const savedLayout = this.loadFurnitureLayout()
    this.customFurniture = this.loadCustomFurniture()
    this.removedFurniture = this.loadRemovedFurniture()
    ;[...OFFICE_OBJECTS, ...this.customFurniture].forEach((object) => {
      if (!this.removedFurniture.has(object.id)) this.createFurnitureSprite(object, savedLayout)
    })
  }

  private createFurnitureSprite(
    object: OfficeObject,
    savedLayout: Record<string, { x: number; y: number }> = {},
  ) {
    const furnitureTexture = this.textures.get(FURNITURE_KEY)
    let frame: string | number = object.frame
    let frameWidth = FURNITURE_FRAME_SIZE
    let frameHeight = FURNITURE_FRAME_SIZE
    const contentSize = object.crop ?? FURNITURE_CONTENT_SIZE[object.frame]
    if (object.crop) {
      const frameName = `crop-${object.id}`
      if (!furnitureTexture.has(frameName)) {
        const sourceFrame = furnitureTexture.get(object.frame)
        furnitureTexture.add(
          frameName,
          sourceFrame.sourceIndex,
          sourceFrame.cutX + object.crop.x,
          sourceFrame.cutY + object.crop.y,
          object.crop.width,
          object.crop.height,
        )
      }
      frame = frameName
      frameWidth = object.crop.width
      frameHeight = object.crop.height
    }
    const uniformScale = contentSize
      ? Math.min(object.width / contentSize.width, object.height / contentSize.height)
      : object.width / FURNITURE_FRAME_SIZE
    const displayWidth = frameWidth * uniformScale
    const displayHeight = frameHeight * uniformScale
    const visibleHeight = contentSize ? contentSize.height * uniformScale : object.height
    const savedPosition = savedLayout[object.id]
    const x = savedPosition?.x ?? object.x
    const y = savedPosition?.y ?? object.y
    const depth = object.depth ?? Math.max(10, Math.round(y - visibleHeight / 2))
    const sprite = this.add
      .sprite(x, y, FURNITURE_KEY, frame)
      .setDisplaySize(displayWidth, displayHeight)
      .setDepth(depth)
      .setName(object.id)
      .setData('visibleHeight', visibleHeight)
      .setData('fixedDepth', object.depth ?? null)
      .setData('room', object.room)
      .setInteractive({ useHandCursor: true })
    if (sprite.input) this.input.setDraggable(sprite, this.furnitureEditMode)
    sprite.on('pointerdown', () => {
      if (this.furnitureEditMode) {
        this.selectFurniture(sprite.name)
        return
      }
      const roomId = PRIMARY_ROOM_ASSETS.get(sprite.name)
      if (roomId) {
        const originalScaleX = sprite.scaleX
        const originalScaleY = sprite.scaleY
        this.tweens.add({
          targets: sprite,
          scaleX: originalScaleX * 1.045,
          scaleY: originalScaleY * 1.045,
          duration: 90,
          yoyo: true,
          ease: 'Quad.easeOut',
        })
        this.time.delayedCall(85, () => officeGameEvents.selectRoom(roomId))
      }
    })
    sprite.on('pointerover', () => {
      if (!this.furnitureEditMode) return
      sprite.setTint(0x9ff7ff)
      this.updateFurnitureEditorLabel(sprite)
    })
    sprite.on('pointerout', () => {
      if (!sprite.getData('dragging') && sprite.name !== this.selectedFurnitureId) {
        sprite.clearTint()
      }
    })
    sprite.on('dragstart', () => {
      if (!this.furnitureEditMode) return
      this.selectFurniture(sprite.name)
      sprite.setData('dragging', true).setTint(0xffef8a).setDepth(950)
      this.updateFurnitureEditorLabel(sprite)
    })
    sprite.on('drag', (_pointer: Phaser.Input.Pointer, dragX: number, dragY: number) => {
      if (!this.furnitureEditMode) return
      const halfWidth = sprite.displayWidth / 2
      const halfHeight = sprite.displayHeight / 2
      const xPosition = Phaser.Math.Snap.To(
        Phaser.Math.Clamp(dragX, halfWidth, 960 - halfWidth),
        4,
      )
      const yPosition = Phaser.Math.Snap.To(
        Phaser.Math.Clamp(dragY, halfHeight, 640 - halfHeight),
        4,
      )
      sprite.setPosition(xPosition, yPosition)
      this.updateFurnitureEditorLabel(sprite)
    })
    sprite.on('dragend', () => {
      if (!this.furnitureEditMode) return
      sprite.setData('dragging', false).setTint(0x9ff7ff)
      this.updateFurnitureDepth(sprite)
      this.saveFurnitureLayout()
      this.updateFurnitureEditorLabel(sprite)
    })
    this.furnitureSprites.set(object.id, sprite)
  }

  private createFurnitureEditorLabel() {
    this.furnitureEditorLabel = this.add
      .text(12, 612, 'Pilih dan seret furnitur', {
        fontFamily: 'Plus Jakarta Sans, Segoe UI, sans-serif',
        fontSize: '9px',
        fontStyle: 'bold',
        color: '#fef3c7',
        backgroundColor: '#061224e8',
        padding: { x: 8, y: 5 },
      })
      .setDepth(1100)
      .setVisible(false)
  }

  private setFurnitureEditMode(enabled: boolean) {
    this.furnitureEditMode = enabled
    this.furnitureEditorLabel?.setVisible(enabled)
    if (enabled) this.furnitureEditorLabel?.setText('Pilih dan seret furnitur')
    if (!enabled) this.selectFurniture(null)
    this.furnitureSprites.forEach((sprite) => {
      if (sprite.input) this.input.setDraggable(sprite, enabled)
      if (!enabled) {
        sprite.setData('dragging', false).clearTint()
        this.updateFurnitureDepth(sprite)
      }
    })
  }

  private selectFurniture(id: string | null) {
    if (this.selectedFurnitureId) {
      this.furnitureSprites.get(this.selectedFurnitureId)?.clearTint()
    }
    this.selectedFurnitureId = id
    if (id) {
      const sprite = this.furnitureSprites.get(id)
      sprite?.setTint(0x9ff7ff)
      if (sprite) this.updateFurnitureEditorLabel(sprite)
    }
    officeGameEvents.selectFurniture(id)
  }

  private addFurniture(frame: number) {
    if (!this.furnitureEditMode || frame < 0 || frame >= FURNITURE_CONTENT_SIZE.length) return
    const content = FURNITURE_CONTENT_SIZE[frame]
    const scale = Math.min(112 / content.width, 82 / content.height)
    const index = this.customFurniture.length
    const object: OfficeObject = {
      id: `custom-${frame}-${Date.now()}`,
      room: 'corridor',
      frame,
      x: 440 + (index % 4) * 36,
      y: 315 + (Math.floor(index / 4) % 2) * 32,
      width: Math.round(content.width * scale),
      height: Math.round(content.height * scale),
    }
    this.customFurniture.push(object)
    this.createFurnitureSprite(object)
    this.saveCustomFurniture()
    this.saveFurnitureLayout()
    this.selectFurniture(object.id)
    this.furnitureEditorLabel?.setText('Furnitur baru ditambahkan · seret ke posisi tujuan')
  }

  private deleteFurniture(id: string) {
    if (!this.furnitureEditMode) return
    const sprite = this.furnitureSprites.get(id)
    if (!sprite) return
    sprite.destroy()
    this.furnitureSprites.delete(id)
    const customIndex = this.customFurniture.findIndex((object) => object.id === id)
    if (customIndex >= 0) {
      this.customFurniture.splice(customIndex, 1)
      this.saveCustomFurniture()
    } else {
      this.removedFurniture.add(id)
      this.saveRemovedFurniture()
    }
    this.selectFurniture(null)
    this.saveFurnitureLayout()
    this.furnitureEditorLabel?.setText('Furnitur dihapus')
  }

  private updateFurnitureDepth(sprite: Phaser.GameObjects.Sprite) {
    const fixedDepth = sprite.getData('fixedDepth') as number | null
    const visibleHeight = Number(sprite.getData('visibleHeight') ?? sprite.displayHeight)
    sprite.setDepth(fixedDepth ?? Math.max(10, Math.round(sprite.y - visibleHeight / 2)))
  }

  private updateFurnitureEditorLabel(sprite: Phaser.GameObjects.Sprite) {
    if (!this.furnitureEditMode) return
    this.furnitureEditorLabel
      ?.setText(`${sprite.name} · X ${Math.round(sprite.x)} · Y ${Math.round(sprite.y)}`)
      .setVisible(true)
  }

  private loadFurnitureLayout(): Record<string, { x: number; y: number }> {
    try {
      const stored = window.localStorage.getItem(FURNITURE_LAYOUT_STORAGE_KEY)
      if (!stored) return {}
      return JSON.parse(stored) as Record<string, { x: number; y: number }>
    } catch {
      return {}
    }
  }

  private loadCustomFurniture(): OfficeObject[] {
    try {
      const stored = window.localStorage.getItem(FURNITURE_CUSTOM_STORAGE_KEY)
      if (!stored) return []
      const objects = JSON.parse(stored) as OfficeObject[]
      return objects.filter(
        (object) =>
          typeof object.id === 'string' &&
          Number.isInteger(object.frame) &&
          object.frame >= 0 &&
          object.frame < FURNITURE_CONTENT_SIZE.length,
      )
    } catch {
      return []
    }
  }

  private loadRemovedFurniture(): Set<string> {
    try {
      const stored = window.localStorage.getItem(FURNITURE_REMOVED_STORAGE_KEY)
      return new Set(stored ? (JSON.parse(stored) as string[]) : [])
    } catch {
      return new Set()
    }
  }

  private saveCustomFurniture() {
    window.localStorage.setItem(
      FURNITURE_CUSTOM_STORAGE_KEY,
      JSON.stringify(this.customFurniture),
    )
  }

  private saveRemovedFurniture() {
    window.localStorage.setItem(
      FURNITURE_REMOVED_STORAGE_KEY,
      JSON.stringify([...this.removedFurniture]),
    )
  }

  private saveFurnitureLayout() {
    const layout: Record<string, { x: number; y: number }> = {}
    this.furnitureSprites.forEach((sprite, id) => {
      layout[id] = { x: Math.round(sprite.x), y: Math.round(sprite.y) }
    })
    window.localStorage.setItem(FURNITURE_LAYOUT_STORAGE_KEY, JSON.stringify(layout))
  }

  private resetFurnitureLayout() {
    window.localStorage.removeItem(FURNITURE_LAYOUT_STORAGE_KEY)
    window.localStorage.removeItem(FURNITURE_CUSTOM_STORAGE_KEY)
    window.localStorage.removeItem(FURNITURE_REMOVED_STORAGE_KEY)
    this.selectFurniture(null)
    this.scene.restart()
  }

  private drawWallOccluders() {
    if (!this.textures.exists(WALL_KEY)) return
    WALL_OCCLUDERS.forEach((segment) => {
      const maskShape = this.add.graphics().setVisible(false)
      maskShape.fillStyle(0xffffff, 1).fillRect(segment.x, segment.y, segment.width, segment.height)
      const mask = maskShape.createGeometryMask()
      this.add
        .image(0, 0, WALL_KEY)
        .setOrigin(0)
        .setDisplaySize(960, 640)
        .setDepth(segment.depth)
        .setMask(mask)
        .setName(`wall-${segment.id}`)
    })
  }

  private drawRoomLabels() {
    ROOMS.forEach((room) => {
      const label = this.add
        .container(room.x + 12, room.y + 11)
        .setDepth(900)
        .setAlpha(0)
        .setVisible(false)
      const text = this.add.text(0, 0, `${room.number}  ${room.label}`, {
        fontFamily: 'Plus Jakarta Sans, Segoe UI, sans-serif',
        fontSize: '11px',
        fontStyle: 'bold',
        color: '#ffffff',
        backgroundColor: '#071526e8',
        padding: { x: 9, y: 6 },
      })
      const marker = this.add.rectangle(0, 0, 4, text.height, room.accent).setOrigin(0, 0)
      label.add([text, marker])
      this.roomLabels.set(room.id, label)
    })
  }

  private handleRoomPointer(pointer: Phaser.Input.Pointer) {
    const room = ROOMS.find(
      (item) =>
        pointer.worldX >= item.x &&
        pointer.worldX <= item.x + item.width &&
        pointer.worldY >= item.y &&
        pointer.worldY <= item.y + item.height,
    )
    const nextRoomId = room?.id ?? null
    if (nextRoomId === this.hoveredRoomId) return
    this.hideRoomLabel()
    if (!nextRoomId) return
    const label = this.roomLabels.get(nextRoomId)
    if (!label) return
    this.hoveredRoomId = nextRoomId
    label.setVisible(true).setAlpha(0)
    this.tweens.add({ targets: label, alpha: 1, duration: 100 })
  }

  private hideRoomLabel() {
    if (!this.hoveredRoomId) return
    const label = this.roomLabels.get(this.hoveredRoomId)
    if (label) {
      this.tweens.killTweensOf(label)
      label.setVisible(false).setAlpha(0)
    }
    this.hoveredRoomId = null
  }

  private drawAmbientTechnology() {
    const globeGlow = this.add.circle(480, 315, 39, 0x22d3ee, 0.07).setDepth(5)
    const terminalGlow = this.add.circle(874, 545, 18, 0x22d3ee, 0.05).setDepth(500)
    if (this.reducedMotion) return
    this.tweens.add({
      targets: globeGlow,
      alpha: { from: 0.04, to: 0.18 },
      scale: { from: 0.92, to: 1.12 },
      duration: 1300,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    })
    this.tweens.add({
      targets: terminalGlow,
      alpha: { from: 0.03, to: 0.16 },
      scale: { from: 0.88, to: 1.15 },
      duration: 900,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    })
  }

  private createPixelAnimations() {
    const createLoop = (key: string, texture: string, start: number, end: number, frameRate: number) => {
      if (this.anims.exists(key)) return
      this.anims.create({
        key,
        frames: this.anims.generateFrameNumbers(texture, { start, end }),
        frameRate: this.reducedMotion ? 1 : frameRate,
        repeat: this.reducedMotion ? 0 : -1,
      })
    }

    createLoop('pixel-walk-down', PIXEL_WALK_KEY, 0, 3, 8)
    createLoop('pixel-walk-left', PIXEL_WALK_KEY, 4, 7, 8)
    createLoop('pixel-walk-right', PIXEL_WALK_KEY, 8, 11, 8)
    createLoop('pixel-walk-up', PIXEL_WALK_KEY, 12, 15, 8)
    createLoop('pixel-idle', PIXEL_ACTION_KEY, 0, 3, 3)
    createLoop('pixel-working', PIXEL_ACTION_KEY, 4, 7, 7)
    createLoop('pixel-completed', PIXEL_ACTION_KEY, 8, 11, 6)
    createLoop('pixel-failed', PIXEL_ACTION_KEY, 12, 15, 5)
    createLoop('pixel-work-desk', PIXEL_WORK_KEY, 0, 3, 7)
    createLoop('pixel-work-documents', PIXEL_WORK_KEY, 4, 7, 5)
    createLoop('pixel-work-server', PIXEL_WORK_KEY, 8, 11, 6)
    createLoop('pixel-work-tutor', PIXEL_WORK_KEY, 12, 15, 5)
  }

  private updateAgents(agents: OfficeAgent[]) {
    agents.forEach((agent) => {
      const homeRoomId = HOME_ROOMS[agent.id] ?? agent.room
      const destinationRoomId = agent.state === 'running' ? agent.room : homeRoomId
      const room = ROOMS.find((item) => item.id === destinationRoomId) ?? ROOMS[0]
      const target = room.anchor
      let bot = this.bots.get(agent.id)
      if (!bot) {
        const home = ROOMS.find((item) => item.id === HOME_ROOMS[agent.id]) ?? room
        bot = this.createBot(agent, home.anchor.x, home.anchor.y)
        this.bots.set(agent.id, bot)
      }

      const updateKey = `${agent.updated_at}:${agent.state}:${agent.station_id ?? ''}`
      if (bot.lastUpdate === updateKey) return
      bot.lastUpdate = updateKey
      this.setBotPresentationState(bot, agent.state)
      bot.defaultActivity = this.agentActivityLabel(agent)
      this.updateBotBubble(bot, bot.defaultActivity, agent.state)
      this.cancelIdleRoam(bot)
      bot.state = agent.state

      const defaultStation = agent.state === 'running' ? AGENT_WORKSTATION_IDS[agent.id] : undefined
      const workstationId = agent.state === 'running'
        ? agent.station_id ?? defaultStation
        : undefined
      const workstation = workstationId ? WORKSTATIONS[workstationId] : undefined
      if (workstation) {
        this.updateAgentAtWorkstation(bot, agent, workstation)
        return
      }

      bot.travelingToWorkstation = false
      bot.pendingTerminal = null
      const returnRoute = this.routeToRoom(bot, room.id)
      this.moveBot(bot, [...returnRoute, target], this.visualState(agent.state), () => {
        bot.room = room.id
        if (bot.state === 'idle') {
          this.scheduleIdleRoam(bot)
        } else if (bot.state === 'succeeded') {
          bot.roamTimer = this.time.delayedCall(1200, () => {
            bot.roamTimer = null
            if (bot.state !== 'succeeded') return
            this.startIdleActivity(bot)
          })
        } else if (['queued', 'waiting', 'cancelled'].includes(bot.state)) {
          this.startIdleActivity(bot, false)
        }
      })
    })
  }

  private updateAgentAtWorkstation(bot: Bot, agent: OfficeAgent, workstation: Workstation) {
    const terminal =
      agent.state === 'succeeded' ? 'completed' : agent.state === 'failed' ? 'failed' : null
    if (bot.travelingToWorkstation) {
      if (terminal) bot.pendingTerminal = terminal
      return
    }

    const distance = Phaser.Math.Distance.Between(
      bot.container.x,
      bot.container.y,
      workstation.position.x,
      workstation.position.y,
    )
    if (distance > 8) {
      bot.pendingTerminal = terminal
      bot.travelingToWorkstation = true
      this.updateBotBubble(bot, 'Menuju workstation', agent.state)
      const doorwayRoute = this.routeToRoom(bot, workstation.room)
      bot.room = 'corridor'
      this.moveBot(bot, [...doorwayRoute, ...workstation.approach], 'working', () => {
        bot.travelingToWorkstation = false
        bot.room = workstation.room
        this.updateBotBubble(bot, bot.defaultActivity, bot.state)
        if (bot.pendingTerminal) {
          const next = bot.pendingTerminal
          bot.pendingTerminal = null
          this.animateBot(bot, next)
        }
      })
      return
    }

    bot.room = workstation.room
    bot.travelingToWorkstation = false
    this.animateBot(bot, terminal ?? 'working')
  }

  private cancelIdleRoam(bot: Bot) {
    bot.roamTimer?.remove(false)
    bot.roamTimer = null
  }

  private scheduleIdleRoam(bot: Bot) {
    this.cancelIdleRoam(bot)
    if (!this.canRoam(bot)) return
    const homeRoom = HOME_ROOMS[bot.agentId] ?? bot.room
    const patrol = IDLE_PATROLS[homeRoom]
    if (!patrol?.length) return

    bot.roamTimer = this.time.delayedCall(Phaser.Math.Between(700, 2200), () => {
      bot.roamTimer = null
      if (!this.canRoam(bot)) return
      bot.idleActivityIndex += 1
      if (bot.idleActivityIndex % 2 === 0) {
        this.startIdleActivity(bot)
        return
      }

      bot.room = 'corridor'
      this.updateBotBubble(bot, 'Keliling kantor', this.activityPresentationState(bot))
      this.moveBot(bot, patrol, 'idle', () => {
        bot.room = homeRoom
        this.updateBotBubble(
          bot,
          IDLE_ACTIVITY_TEXT_BY_AGENT[bot.agentId] ?? 'Siap untuk tugas berikutnya',
          this.activityPresentationState(bot),
        )
        this.scheduleIdleRoam(bot)
      })
    })
  }

  private startIdleActivity(bot: Bot, continueRoaming = true) {
    this.stopBotTweens(bot)
    bot.machine.transition('idle')
    const presentationState = this.activityPresentationState(bot)
    this.setBotPresentationState(bot, presentationState)
    this.updateBotBubble(
      bot,
      IDLE_ACTIVITY_TEXT_BY_AGENT[bot.agentId] ?? 'Menyiapkan pekerjaan',
      presentationState,
    )
    bot.pixelSprite?.play(
      IDLE_ACTIVITY_ANIMATION_BY_AGENT[bot.agentId] ?? 'pixel-idle',
      true,
    )
    if (!bot.pixelSprite && !this.reducedMotion) {
      this.tweens.add({
        targets: [bot.leftArm, bot.rightArm],
        angle: { from: -10, to: 10 },
        duration: 320,
        yoyo: true,
        repeat: -1,
        ease: 'Stepped',
      })
    }
    if (!continueRoaming) return
    bot.roamTimer = this.time.delayedCall(Phaser.Math.Between(2200, 3600), () => {
      bot.roamTimer = null
      if (!this.canRoam(bot)) return
      this.updateBotBubble(
        bot,
        IDLE_ACTIVITY_TEXT_BY_AGENT[bot.agentId] ?? bot.defaultActivity,
        this.activityPresentationState(bot),
      )
      this.animateBot(bot, 'idle')
      this.scheduleIdleRoam(bot)
    })
  }

  private canRoam(bot: Bot) {
    return bot.state === 'idle' || bot.state === 'succeeded'
  }

  private activityPresentationState(bot: Bot): AgentState {
    return bot.state === 'succeeded' ? 'idle' : bot.state
  }

  private setBotPresentationState(bot: Bot, state: AgentState) {
    bot.body.setFillStyle(stateColor[state])
    bot.antenna.setFillStyle(state === 'failed' ? 0xfb7185 : 0xfacc15)
    bot.statusRing.setStrokeStyle(state === 'running' ? 2 : 1, stateColor[state], 0.9)
  }

  private routeToRoom(bot: Bot, room: string) {
    if (bot.room === 'corridor') {
      return routeFromCorridor({ x: bot.container.x, y: bot.container.y }, room)
    }
    return routeBetweenRooms(bot.room, room)
  }

  private visualState(state: AgentState): AgentVisualState {
    if (state === 'running') return 'working'
    if (state === 'succeeded') return 'completed'
    if (state === 'failed') return 'failed'
    return 'idle'
  }

  private moveBot(
    bot: Bot,
    points: Point[],
    arrivalState: AgentVisualState,
    afterArrival?: () => void,
  ) {
    const path = points.filter(
      (point) => Phaser.Math.Distance.Between(bot.container.x, bot.container.y, point.x, point.y) > 5,
    )
    if (!path.length) {
      this.animateBot(bot, arrivalState)
      afterArrival?.()
      return
    }

    this.stopBotTweens(bot)
    bot.machine.transition('walking')
    const token = ++bot.motionToken
    if (!bot.pixelSprite && !this.reducedMotion) {
      this.tweens.add({ targets: [bot.leftLeg, bot.rightArm], angle: { from: -12, to: 12 }, duration: 130, yoyo: true, repeat: -1 })
      this.tweens.add({ targets: [bot.rightLeg, bot.leftArm], angle: { from: 12, to: -12 }, duration: 130, yoyo: true, repeat: -1 })
    }

    const step = (position: number) => {
      if (token !== bot.motionToken) return
      const point = path[position]
      const dx = point.x - bot.container.x
      const dy = point.y - bot.container.y
      if (bot.pixelSprite) this.playPixelWalk(bot.pixelSprite, this.walkDirection(dx, dy))
      const distance = Phaser.Math.Distance.Between(bot.container.x, bot.container.y, point.x, point.y)
      this.tweens.add({
        targets: bot.container,
        x: point.x,
        y: point.y,
        duration: this.reducedMotion ? 40 : Phaser.Math.Clamp(distance * 4.2, 240, 1250),
        ease: 'Linear',
        onUpdate: () => bot.container.setDepth(Math.round(bot.container.y)),
        onComplete: () => {
          if (position + 1 < path.length) {
            step(position + 1)
            return
          }
          this.animateBot(bot, arrivalState)
          afterArrival?.()
        },
      })
    }
    step(0)
  }

  private walkDirection(dx: number, dy: number): WalkDirection {
    if (Math.abs(dx) > Math.abs(dy)) return dx < 0 ? 'left' : 'right'
    return dy < 0 ? 'up' : 'down'
  }

  private playPixelWalk(sprite: Phaser.GameObjects.Sprite, direction: WalkDirection) {
    sprite.play(`pixel-walk-${direction}`, true)
  }

  private createBot(agent: OfficeAgent, x: number, y: number): Bot {
    const usesSprite =
      this.textures.exists(PIXEL_ACTION_KEY) && this.textures.exists(PIXEL_WALK_KEY)
    const shadow = this.add.ellipse(0, 17, usesSprite ? 29 : 27, usesSprite ? 8 : 8, 0x000000, 0.34)
    const selectionPulse = this.add
      .ellipse(0, 4, usesSprite ? 48 : 43, usesSprite ? 48 : 43)
      .setStrokeStyle(3, Phaser.Display.Color.HexStringToColor(agent.color).color, 1)
      .setAlpha(0)
    const statusRing = this.add.ellipse(0, 17, usesSprite ? 36 : 33, usesSprite ? 13 : 12).setStrokeStyle(1, stateColor[agent.state], 0.8)
    const body = this.add.rectangle(0, 2, 22, 24, stateColor[agent.state]).setStrokeStyle(2, 0xe6f7ff)
    const head = this.add.rectangle(0, -15, 28, 19, 0xd7f4ff).setStrokeStyle(2, 0x071526)
    const face = this.add.rectangle(0, -14, 19, 9, 0x071526)
    const eyeLeft = this.add.rectangle(-5, -14, 3, 3, 0x22d3ee)
    const eyeRight = this.add.rectangle(5, -14, 3, 3, 0x22d3ee)
    const antenna = this.add.rectangle(0, -28, 3, 8, 0xfacc15)
    const antennaTip = this.add.rectangle(0, -33, 7, 5, 0xfacc15)
    const leftArm = this.add.rectangle(-15, 2, 5, 16, 0x7dd3fc)
    const rightArm = this.add.rectangle(15, 2, 5, 16, 0x7dd3fc)
    const leftLeg = this.add.rectangle(-6, 17, 6, 9, 0x7dd3fc)
    const rightLeg = this.add.rectangle(6, 17, 6, 9, 0x7dd3fc)
    const proceduralParts = [leftLeg, rightLeg, leftArm, rightArm, body, head, face, eyeLeft, eyeRight, antenna, antennaTip]
    proceduralParts.forEach((part) => part.setVisible(!usesSprite))
    const pixelSprite = usesSprite
      ? this.add.sprite(0, -6, PIXEL_ACTION_KEY, 0).setDisplaySize(BOT_SPRITE_SIZE, BOT_SPRITE_SIZE)
      : null
    if (pixelSprite) {
      pixelSprite.setTint(Phaser.Display.Color.HexStringToColor(agent.color).color)
    }
    pixelSprite?.play('pixel-idle')
    const speechBubble = this.add.graphics()
    const activityText = this.add
      .text(0, -54, '', {
        fontFamily: 'Plus Jakarta Sans, Segoe UI, sans-serif',
        fontSize: '9px',
        fontStyle: '600',
        color: '#172033',
        align: 'center',
        lineSpacing: 2,
        wordWrap: { width: 146, useAdvancedWrap: true },
      })
      .setOrigin(0.5, 1)
    const name = this.add
      .text(0, -37, agent.name, {
        fontFamily: 'Plus Jakarta Sans, Segoe UI, sans-serif',
        fontSize: '9px',
        fontStyle: 'bold',
        color: '#ffffff',
        backgroundColor: '#071526dc',
        padding: { x: 5, y: 2 },
      })
      .setOrigin(0.5, 1)
    const children: Phaser.GameObjects.GameObject[] = [shadow, selectionPulse, statusRing, ...proceduralParts]
    if (pixelSprite) children.push(pixelSprite)
    children.push(speechBubble, activityText, name)
    const container = this.add
      .container(x, y, children)
      .setDepth(Math.round(y))
      .setSize(62, 78)
      .setInteractive({ useHandCursor: true })
    const bot: Bot = {
      agentId: agent.id,
      container,
      body,
      antenna,
      leftArm,
      rightArm,
      leftLeg,
      rightLeg,
      pixelSprite,
      statusRing,
      selectionPulse,
      speechBubble,
      activityText,
      defaultActivity: this.agentActivityLabel(agent),
      room: HOME_ROOMS[agent.id] ?? agent.room,
      state: agent.state,
      machine: new AgentStateMachine(),
      pendingTerminal: null,
      lastUpdate: '',
      motionToken: 0,
      roamTimer: null,
      travelingToWorkstation: false,
      idleActivityIndex: 0,
    }
    container.on('pointerdown', () => {
      if (this.furnitureEditMode) return
      this.tweens.killTweensOf(selectionPulse)
      selectionPulse.setAlpha(1).setScale(0.62)
      this.tweens.add({
        targets: selectionPulse,
        alpha: 0,
        scale: 1.75,
        duration: this.reducedMotion ? 40 : 240,
        ease: 'Cubic.easeOut',
      })
      this.time.delayedCall(this.reducedMotion ? 0 : 110, () => {
        officeGameEvents.selectAgent(agent.id)
      })
    })
    this.updateBotBubble(bot, bot.defaultActivity, agent.state)
    return bot
  }

  private agentActivityLabel(agent: OfficeAgent) {
    const fallback: Record<AgentState, string> = {
      offline: 'Tidak terhubung',
      idle: 'Siap membantu',
      queued: 'Menunggu giliran',
      running: 'Sedang mengerjakan tugas',
      waiting: 'Menunggu data',
      succeeded: 'Tugas selesai',
      failed: 'Tugas perlu diperiksa',
      cancelled: 'Tugas dibatalkan',
    }
    if (['succeeded', 'failed', 'cancelled'].includes(agent.state)) return fallback[agent.state]
    const task = agent.task?.trim() ?? ''
    const friendlyTask = task
      .replace(/Knowledge Server/gi, 'ruang server')
      .replace(/knowledge index/gi, 'materi')
      .replace(/knowledge base/gi, 'sumber pengetahuan')
      .replace(/indexing/gi, 'pengolahan materi')
      .replace(/embedding/gi, 'memproses materi')
      .replace(/\bchunk\b/gi, 'bagian')
    if (friendlyTask && !['idle', 'siap bekerja', 'siap membantu'].includes(friendlyTask.toLowerCase())) return friendlyTask
    return fallback[agent.state]
  }

  private updateBotBubble(bot: Bot, activity: string, state: AgentState) {
    const maxLength = 52
    const label = activity.length > maxLength ? `${activity.slice(0, maxLength - 1)}...` : activity
    bot.activityText.setText(label).setColor('#172033')
    const width = Phaser.Math.Clamp(Math.ceil(bot.activityText.width) + 26, 86, 168)
    const height = Math.ceil(bot.activityText.height) + 14
    const bottom = -51
    const top = bottom - height
    bot.activityText.setPosition(3, bottom - 7)
    bot.speechBubble
      .clear()
      .fillStyle(0x071526, 0.16)
      .fillRoundedRect(-width / 2 + 2, top + 3, width, height, 9)
      .fillStyle(0xffffff, 0.98)
      .lineStyle(1, 0xdbe5f1, 1)
      .fillRoundedRect(-width / 2, top, width, height, 9)
      .strokeRoundedRect(-width / 2, top, width, height, 9)
      .fillStyle(0xffffff, 0.98)
      .fillTriangle(-5, bottom - 1, 5, bottom - 1, 0, bottom + 6)
      .fillStyle(stateColor[state], 1)
      .fillCircle(-width / 2 + 10, top + 10, 3)
  }

  private stopBotTweens(bot: Bot) {
    const tweenTargets: object[] = [
      bot.container,
      bot.statusRing,
      bot.leftArm,
      bot.rightArm,
      bot.leftLeg,
      bot.rightLeg,
    ]
    if (bot.pixelSprite) tweenTargets.push(bot.pixelSprite)
    this.tweens.killTweensOf(tweenTargets)
    bot.container.setScale(1).setAngle(0)
    bot.pixelSprite?.setScale(BOT_SPRITE_SIZE / SHEET_FRAME_SIZE).setAngle(0)
    bot.statusRing.setScale(1).setAlpha(1)
    bot.leftArm.setAngle(0)
    bot.rightArm.setAngle(0)
    bot.leftLeg.setAngle(0)
    bot.rightLeg.setAngle(0)
  }

  private animateBot(bot: Bot, state: AgentVisualState) {
    this.stopBotTweens(bot)
    bot.machine.transition(state)
    const baseY = bot.container.y

    if (bot.pixelSprite) {
      const key: Record<Exclude<AgentVisualState, 'walking'>, string> = {
        idle: 'pixel-idle',
        working: WORK_ANIMATION_BY_AGENT[bot.agentId] ?? 'pixel-work-documents',
        completed: 'pixel-completed',
        failed: 'pixel-failed',
      }
      if (state !== 'walking') bot.pixelSprite.play(key[state], true)
      if (state === 'working' && !this.reducedMotion) {
        this.tweens.add({ targets: bot.statusRing, alpha: { from: 0.3, to: 1 }, scale: { from: 0.9, to: 1.14 }, duration: 520, yoyo: true, repeat: -1 })
      } else if (state === 'completed' && !this.reducedMotion) {
        this.tweens.add({ targets: bot.container, scale: { from: 1, to: 1.12 }, duration: 180, yoyo: true, repeat: 2 })
      } else if (state === 'failed' && !this.reducedMotion) {
        this.tweens.add({ targets: bot.container, x: { from: bot.container.x - 2, to: bot.container.x + 2 }, duration: 90, yoyo: true, repeat: 5 })
      }
      return
    }

    if (state === 'working' && !this.reducedMotion) {
      this.tweens.add({ targets: [bot.leftArm, bot.rightArm], angle: { from: -18, to: 18 }, duration: 180, yoyo: true, repeat: -1, ease: 'Stepped' })
      this.tweens.add({ targets: bot.container, y: baseY - 2, duration: 280, yoyo: true, repeat: -1, ease: 'Stepped' })
      return
    }
    if (state === 'completed' && !this.reducedMotion) {
      this.tweens.add({ targets: bot.container, scale: 1.16, duration: 180, yoyo: true, repeat: 2 })
      return
    }
    if (state === 'failed' && !this.reducedMotion) {
      this.tweens.add({ targets: bot.container, angle: { from: -4, to: 4 }, duration: 90, yoyo: true, repeat: 7 })
      return
    }
    if (!this.reducedMotion) {
      this.tweens.add({ targets: bot.container, y: baseY - 2, duration: 900, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' })
    }
  }
}
