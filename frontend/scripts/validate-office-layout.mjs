import fs from 'node:fs'
import path from 'node:path'

const projectRoot = process.cwd()

function readLiteral(relativePath, marker, openingCharacter) {
  const source = fs.readFileSync(path.join(projectRoot, relativePath), 'utf8')
  const markerIndex = source.indexOf(marker)
  const assignmentIndex = source.indexOf('=', markerIndex)
  const start = source.indexOf(openingCharacter, assignmentIndex)
  const closingCharacter = openingCharacter === '[' ? ']' : '}'
  let depth = 0
  let quote = null
  for (let index = start; index < source.length; index += 1) {
    const character = source[index]
    const previous = source[index - 1]
    if (quote) {
      if (character === quote && previous !== '\\') quote = null
      continue
    }
    if (character === "'" || character === '"' || character === '`') {
      quote = character
      continue
    }
    if (character === openingCharacter) depth += 1
    if (character === closingCharacter) depth -= 1
    if (depth === 0) return new Function(`return (${source.slice(start, index + 1)})`)()
  }
  throw new Error(`Literal ${marker} tidak lengkap.`)
}

const FURNITURE_CONTENT_SIZE = readLiteral(
  'src/game/officeObjects.ts',
  'export const FURNITURE_CONTENT_SIZE',
  '[',
)
const OFFICE_OBJECTS = readLiteral(
  'src/game/officeObjects.ts',
  'export const OFFICE_OBJECTS',
  '[',
)
const IDLE_PATROLS = readLiteral(
  'src/game/navigation.ts',
  'export const IDLE_PATROLS',
  '{',
)
const clearance = 18

const ROOM_BOUNDS = {
  'command-center': { left: 40, right: 300, top: 35, bottom: 235 },
  'research-lab': { left: 350, right: 610, top: 35, bottom: 235 },
  'tutor-room': { left: 660, right: 920, top: 32, bottom: 235 },
  'planning-hub': { left: 40, right: 300, top: 405, bottom: 580 },
  'analytics-room': { left: 445, right: 710, top: 438, bottom: 580 },
  'knowledge-server': { left: 730, right: 908, top: 420, bottom: 575 },
}

const WALL_MOUNT_TOP = {
  'tutor-room': 32,
  'analytics-room': 420,
}

const DOOR_LANES = [
  { id: 'command-door', left: 242, right: 278, top: 190, bottom: 330 },
  { id: 'research-door', left: 562, right: 598, top: 190, bottom: 330 },
  { id: 'tutor-door', left: 662, right: 700, top: 190, bottom: 330 },
  { id: 'planning-door', left: 242, right: 278, top: 345, bottom: 425 },
  { id: 'analytics-door', left: 375, right: 480, top: 435, bottom: 470 },
  { id: 'knowledge-door', left: 680, right: 740, top: 520, bottom: 570 },
]

function boundsFor(object, padding = 0) {
  const content = object.crop ?? FURNITURE_CONTENT_SIZE[object.frame]
  const scale = Math.min(object.width / content.width, object.height / content.height)
  const width = content.width * scale
  const height = content.height * scale
  return {
    id: object.id,
    room: object.room,
    placement: object.placement ?? 'floor',
    left: object.x - width / 2 - padding,
    right: object.x + width / 2 + padding,
    top: object.y - height / 2 - padding,
    bottom: object.y + height / 2 + padding,
  }
}

const furnitureBounds = OFFICE_OBJECTS.map((object) => boundsFor(object))
const blockers = OFFICE_OBJECTS.map((object) => boundsFor(object, clearance))

function rectanglesOverlap(first, second) {
  return (
    first.left < second.right &&
    first.right > second.left &&
    first.top < second.bottom &&
    first.bottom > second.top
  )
}

function segmentIntersectsRectangle(start, end, rectangle) {
  let minimumTime = 0
  let maximumTime = 1
  const deltaX = end.x - start.x
  const deltaY = end.y - start.y
  const axes = [
    [start.x, deltaX, rectangle.left, rectangle.right],
    [start.y, deltaY, rectangle.top, rectangle.bottom],
  ]

  for (const [origin, delta, lower, upper] of axes) {
    if (Math.abs(delta) < Number.EPSILON) {
      if (origin < lower || origin > upper) return false
      continue
    }
    const firstTime = (lower - origin) / delta
    const secondTime = (upper - origin) / delta
    const entryTime = Math.min(firstTime, secondTime)
    const exitTime = Math.max(firstTime, secondTime)
    minimumTime = Math.max(minimumTime, entryTime)
    maximumTime = Math.min(maximumTime, exitTime)
    if (minimumTime > maximumTime) return false
  }
  return true
}

const collisions = []

for (let firstIndex = 0; firstIndex < furnitureBounds.length; firstIndex += 1) {
  for (let secondIndex = firstIndex + 1; secondIndex < furnitureBounds.length; secondIndex += 1) {
    const first = furnitureBounds[firstIndex]
    const second = furnitureBounds[secondIndex]
    if (rectanglesOverlap(first, second)) {
      collisions.push(`furniture overlap: ${first.id} hits ${second.id}`)
    }
  }
}

for (const furniture of furnitureBounds) {
  const room = ROOM_BOUNDS[furniture.room]
  const minimumTop = furniture.placement === 'wall'
    ? (WALL_MOUNT_TOP[furniture.room] ?? room?.top)
    : room?.top
  if (
    room &&
    (furniture.left < room.left ||
      furniture.right > room.right ||
      furniture.top < minimumTop ||
      furniture.bottom > room.bottom)
  ) {
    collisions.push(`room bounds: ${furniture.id} leaves ${furniture.room}`)
  }
  for (const lane of DOOR_LANES) {
    if (rectanglesOverlap(furniture, lane)) {
      collisions.push(`door clearance: ${furniture.id} blocks ${lane.id}`)
    }
  }
}

for (const [room, patrol] of Object.entries(IDLE_PATROLS)) {
  for (let index = 1; index < patrol.length; index += 1) {
    for (const blocker of blockers) {
      if (segmentIntersectsRectangle(patrol[index - 1], patrol[index], blocker)) {
        collisions.push(`${room} segment ${index - 1}-${index} hits ${blocker.id}`)
      }
    }
  }
}

if (collisions.length) {
  console.error(collisions.join('\n'))
  process.exitCode = 1
} else {
  console.log(
    `Validated ${OFFICE_OBJECTS.length} furniture assets, ${DOOR_LANES.length} door lanes, and ${Object.keys(IDLE_PATROLS).length} patrols with ${clearance}px clearance.`,
  )
}
