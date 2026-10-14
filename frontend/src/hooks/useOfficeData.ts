import { useCallback, useEffect, useState } from 'react'

import { demoSnapshot } from '../data/demo'
import {
  connectOfficeEvents,
  createTask as createRemoteTask,
  fetchChatHistory,
  fetchSnapshot,
  updateTask as updateRemoteTask,
} from '../services/officeApi'
import type { IoTChatTurn, NewTask, OfficeEvent, OfficeSnapshot, OfficeTask } from '../types'

const forcePreview = new URLSearchParams(window.location.search).get('preview') === '1'

function mergeEvent(snapshot: OfficeSnapshot, event: OfficeEvent): OfficeSnapshot {
  const activity = event.metadata?.activity
  const stationId = event.metadata?.station_id
  const agents = snapshot.agents.map((agent) =>
    agent.id === event.agent_id
      ? {
          ...agent,
          state: event.state,
          room: event.room,
          task: event.message || event.job_type,
          progress: event.progress,
          activity: activity ?? agent.activity,
          station_id: event.state === 'running' ? stationId ?? agent.station_id : null,
          updated_at: event.created_at,
        }
      : agent,
  )
  const taskId = event.metadata?.task_id
  const eventTaskStatus: OfficeTask['status'] | null =
    event.state === 'running'
      ? 'in_progress'
      : event.state === 'succeeded'
        ? 'completed'
        : event.state === 'failed'
          ? 'failed'
          : null
  const tasks = snapshot.tasks.map((task) =>
    task.id === taskId && eventTaskStatus
      ? {
          ...task,
          status: eventTaskStatus,
          error: event.state === 'failed' ? event.metadata?.error : null,
          updated_at: event.created_at,
        }
      : task,
  )
  return {
    ...snapshot,
    agents,
    tasks,
    last_event_id: event.id,
    recent_events: [event, ...snapshot.recent_events.filter((item) => item.id !== event.id)].slice(
      0,
      20,
    ),
    metrics: {
      ...snapshot.metrics,
      active_agents: agents.filter((agent) => ['queued', 'running', 'waiting'].includes(agent.state))
        .length,
      queued_tasks: tasks.filter((task) => task.status === 'queued').length,
      completed_tasks: tasks.filter((task) => task.status === 'completed').length,
    },
  }
}

export function useOfficeData() {
  const [snapshot, setSnapshot] = useState<OfficeSnapshot>(demoSnapshot)
  const [apiAvailable, setApiAvailable] = useState(false)
  const [realtimeConnected, setRealtimeConnected] = useState(false)
  const [chatHistory, setChatHistory] = useState<IoTChatTurn[]>([])
  const [chatHistoryAvailable, setChatHistoryAvailable] = useState(false)

  useEffect(() => {
    if (forcePreview) {
      setSnapshot(demoSnapshot)
      setApiAvailable(false)
      setRealtimeConnected(false)
      setChatHistory([])
      setChatHistoryAvailable(false)
      return
    }

    let cancelled = false
    let disconnect: () => void = () => {}

    const load = async () => {
      try {
        const next = await fetchSnapshot()
        if (cancelled) return
        setSnapshot(next)
        setApiAvailable(true)
        try {
          const history = await fetchChatHistory()
          if (!cancelled) {
            setChatHistory(history.items)
            setChatHistoryAvailable(history.source === 'supabase')
          }
        } catch {
          if (!cancelled) setChatHistoryAvailable(false)
        }
        disconnect = connectOfficeEvents(
          next.last_event_id,
          (event) => setSnapshot((current) => mergeEvent(current, event)),
          setRealtimeConnected,
        )
      } catch {
        if (!cancelled) {
          setApiAvailable(false)
          setRealtimeConnected(false)
        }
      }
    }

    void load()
    const refresh = window.setInterval(async () => {
      try {
        const next = await fetchSnapshot()
        if (!cancelled) {
          setSnapshot(next)
          setApiAvailable(true)
        }
        try {
          const history = await fetchChatHistory()
          if (!cancelled) {
            setChatHistory(history.items)
            setChatHistoryAvailable(history.source === 'supabase')
          }
        } catch {
          if (!cancelled) setChatHistoryAvailable(false)
        }
      } catch {
        if (!cancelled) setApiAvailable(false)
      }
    }, 20_000)

    return () => {
      cancelled = true
      window.clearInterval(refresh)
      disconnect()
    }
  }, [])

  const createTask = useCallback(
    async (input: NewTask) => {
      let task: OfficeTask
      if (apiAvailable && !forcePreview) {
        task = await createRemoteTask(input)
      } else {
        const now = new Date().toISOString()
        task = {
          ...input,
          id: crypto.randomUUID(),
          status: 'queued',
          created_at: now,
          updated_at: now,
        }
      }
      setSnapshot((current) => ({
        ...current,
        tasks: [task, ...current.tasks],
        metrics: { ...current.metrics, queued_tasks: current.metrics.queued_tasks + 1 },
      }))
      return task
    },
    [apiAvailable],
  )

  const updateTask = useCallback(
    async (taskId: string, values: Partial<OfficeTask>) => {
      const task = apiAvailable && !forcePreview
        ? await updateRemoteTask(taskId, values)
        : ({
            ...snapshot.tasks.find((item) => item.id === taskId),
            ...values,
            updated_at: new Date().toISOString(),
          } as OfficeTask)
      setSnapshot((current) => ({
        ...current,
        tasks: current.tasks.map((item) => (item.id === taskId ? task : item)),
        metrics: {
          ...current.metrics,
          queued_tasks: current.tasks.filter((item) =>
            (item.id === taskId ? task : item).status === 'queued',
          ).length,
          completed_tasks: current.tasks.filter((item) =>
            (item.id === taskId ? task : item).status === 'completed',
          ).length,
        },
      }))
      return task
    },
    [apiAvailable, snapshot.tasks],
  )

  return {
    snapshot,
    apiAvailable,
    realtimeConnected,
    chatHistory,
    chatHistoryAvailable,
    createTask,
    updateTask,
  }
}

