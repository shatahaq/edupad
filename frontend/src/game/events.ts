import type { OfficeAgent } from '../types'

export const AGENTS_UPDATED = 'agents:updated'
export const AGENT_SELECTED = 'agent:selected'
export const FURNITURE_EDIT_MODE_UPDATED = 'furniture:edit-mode'
export const FURNITURE_LAYOUT_RESET = 'furniture:layout-reset'
export const FURNITURE_ADD_REQUESTED = 'furniture:add'
export const FURNITURE_DELETE_REQUESTED = 'furniture:delete'
export const FURNITURE_SELECTED = 'furniture:selected'
export const ROOM_SELECTED = 'room:selected'

class OfficeGameEvents extends EventTarget {
  private agents: OfficeAgent[] = []
  private furnitureEditMode = false

  updateAgents(agents: OfficeAgent[]) {
    this.agents = agents
    this.dispatchEvent(new CustomEvent<OfficeAgent[]>(AGENTS_UPDATED, { detail: agents }))
  }

  currentAgents() {
    return this.agents
  }

  selectAgent(agentId: string) {
    this.dispatchEvent(new CustomEvent<string>(AGENT_SELECTED, { detail: agentId }))
  }

  setFurnitureEditMode(enabled: boolean) {
    this.furnitureEditMode = enabled
    this.dispatchEvent(
      new CustomEvent<boolean>(FURNITURE_EDIT_MODE_UPDATED, { detail: enabled }),
    )
  }

  currentFurnitureEditMode() {
    return this.furnitureEditMode
  }

  resetFurnitureLayout() {
    this.dispatchEvent(new Event(FURNITURE_LAYOUT_RESET))
  }

  addFurniture(frame: number) {
    this.dispatchEvent(new CustomEvent<number>(FURNITURE_ADD_REQUESTED, { detail: frame }))
  }

  deleteFurniture(id: string) {
    this.dispatchEvent(new CustomEvent<string>(FURNITURE_DELETE_REQUESTED, { detail: id }))
  }

  selectFurniture(id: string | null) {
    this.dispatchEvent(new CustomEvent<string | null>(FURNITURE_SELECTED, { detail: id }))
  }

  selectRoom(roomId: string) {
    this.dispatchEvent(new CustomEvent<string>(ROOM_SELECTED, { detail: roomId }))
  }
}

export const officeGameEvents = new OfficeGameEvents()

