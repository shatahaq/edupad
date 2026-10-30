export type AgentVisualState = 'idle' | 'walking' | 'working' | 'completed' | 'failed'

const transitions: Record<AgentVisualState, ReadonlySet<AgentVisualState>> = {
  idle: new Set(['walking', 'working', 'completed', 'failed']),
  walking: new Set(['idle', 'working', 'completed', 'failed']),
  working: new Set(['idle', 'walking', 'completed', 'failed']),
  completed: new Set(['idle', 'walking', 'working']),
  failed: new Set(['idle', 'walking', 'working']),
}

export class AgentStateMachine {
  private value: AgentVisualState = 'idle'

  get state() {
    return this.value
  }

  transition(next: AgentVisualState) {
    if (next === this.value) return this.value
    if (!transitions[this.value].has(next)) {
      throw new Error(`Transisi agent tidak valid: ${this.value} -> ${next}`)
    }
    this.value = next
    return this.value
  }
}
