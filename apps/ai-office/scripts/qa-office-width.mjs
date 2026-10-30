import assert from 'node:assert/strict'
import { access, mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

// Run against the dashboard dev server or a built dashboard served at OFFICE_QA_URL.
// Optional: OFFICE_QA_EXECUTABLE=/path/to/chromium node apps/ai-office/scripts/qa-office-width.mjs
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const output = resolve(root, '.test-tmp')
const url = new URL(process.env.OFFICE_QA_URL || 'http://localhost:5174/dashboard/')
url.searchParams.set('preview', '1')
url.hash = '#/'
const viewports = [
  { width: 1366, height: 768 },
  { width: 1366, height: 650 },
  { width: 1024, height: 600 },
  { width: 1920, height: 1080 },
  { width: 390, height: 844 },
]
const names = ['NOVA', 'PIXEL', 'SORA', 'TEMPO', 'METRIC', 'KOIN', 'NEXUS']
const visibleWorld = { x: 28, width: 1392, height: 1086 }

let playwright
try {
  playwright = await import('playwright')
} catch (error) {
  if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error
  playwright = await import(pathToFileURL(resolve(
    root, '.venv/lib/python3.12/site-packages/playwright/driver/package/index.mjs',
  )).href)
}

async function launchBrowser() {
  // Phaser's Canvas fallback avoids slow software WebGL in headless Linux.
  const options = { headless: true, args: ['--disable-webgl'] }
  if (process.env.OFFICE_QA_EXECUTABLE) {
    return playwright.chromium.launch({
      ...options, executablePath: process.env.OFFICE_QA_EXECUTABLE,
    })
  }
  try {
    return await playwright.chromium.launch(options)
  } catch (error) {
    // A Python Playwright installation may use a system browser instead of a download.
    for (const executablePath of [
      '/usr/bin/chromium', '/usr/bin/chromium-browser',
      '/usr/bin/google-chrome', '/usr/bin/brave-browser',
    ]) {
      try { await access(executablePath) } catch { continue }
      return playwright.chromium.launch({ ...options, executablePath })
    }
    throw error
  }
}

await mkdir(output, { recursive: true })
const browser = await launchBrowser()
try {
  const page = await browser.newPage({ viewport: viewports[0], deviceScaleFactor: 1 })
  page.setDefaultTimeout(15_000)
  const errors = []
  page.on('pageerror', error => {
    errors.push(error.message)
    console.error(`Browser runtime error: ${error.message}`)
  })
  // Keep this visual regression independent of login and backend availability.
  await page.route('**/api/me', route => route.fulfill({
    status: 200, contentType: 'application/json', body: 'null',
  }))
  await page.goto(url.href, { waitUntil: 'domcontentloaded' })
  const canvas = page.locator('.office-world-stage canvas')
  await canvas.waitFor({ state: 'visible' })
  await page.waitForFunction(() => performance.getEntriesByType('resource').some(
    resource => resource.name.includes('edupad-office-empty-v2.png') && resource.responseEnd > 0,
  ))
  const eventsUrl = await page.evaluate(() => performance.getEntriesByType('resource').find(
    resource => resource.name.includes('/ai-office/src/game/events.ts'),
  )?.name)
  if (eventsUrl) {
    await page.waitForFunction(async moduleUrl =>
      (await import(moduleUrl)).officeGameEvents.currentFurnitureLayout().length > 0,
    eventsUrl, { timeout: 30_000 })
  } else {
    // Production bundles do not expose module URLs; preview mode has no SSE stream.
    await page.waitForLoadState('networkidle', { timeout: 30_000 })
  }
  await page.waitForFunction(() => document.fonts.status === 'loaded', null, { timeout: 20_000 })
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))

  async function geometry() {
    return page.evaluate(() => {
      const box = selector => {
        const rect = document.querySelector(selector).getBoundingClientRect()
        return { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
      }
      const canvas = document.querySelector('.office-world-stage canvas')
      return {
        main: box('.main'),
        stage: box('.office-world-stage'),
        canvas: box('.office-world-stage canvas'),
        bitmap: { width: canvas.width, height: canvas.height },
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: document.documentElement.clientWidth,
        documentHeight: document.documentElement.scrollHeight,
        viewportHeight: document.documentElement.clientHeight,
        dock: box('.office-agent-dock'),
      }
    })
  }

  function assertGeometry(metrics, label) {
    const { main, stage, canvas, bitmap } = metrics
    assert.ok(Math.abs(canvas.x - stage.x) <= 1, `${label}: canvas starts at the stage's left edge`)
    assert.ok(Math.abs(canvas.width - stage.width) <= 1, `${label}: canvas fills the stage width`)
    assert.ok(Math.abs(canvas.height - stage.height) <= 1, `${label}: canvas fills the stage height`)
    assert.ok(Math.abs(stage.width - main.width) <= 2, `${label}: office fills the main area without side gutters`)
    assert.ok(stage.height > 200, `${label}: office has a usable height`)
    assert.ok(canvas.y >= -1 && metrics.dock.y + metrics.dock.height <= metrics.viewportHeight + 1,
      `${label}: entire office and dock are visible without vertical scrolling`)
    assert.ok(Math.abs(bitmap.width - canvas.width) <= 2 && Math.abs(bitmap.height - canvas.height) <= 2,
      `${label}: Phaser renders at the displayed canvas size`)
    assert.ok(metrics.documentWidth <= metrics.viewportWidth + 1, `${label}: page has no horizontal overflow`)
    assert.ok(metrics.documentHeight <= metrics.viewportHeight + 1, `${label}: page has no vertical overflow`)
  }

  async function scrollToOffice() {
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
  }

  async function clickWorld(x, y) {
    await scrollToOffice()
    const rect = await canvas.boundingBox()
    await page.mouse.click(
      rect.x + (x - visibleWorld.x) / visibleWorld.width * rect.width,
      rect.y + y * Math.min(rect.height / visibleWorld.height, rect.width / visibleWorld.width),
    )
  }

  for (const viewport of viewports) {
    const label = `${viewport.width}x${viewport.height}`
    await page.setViewportSize(viewport)
    await scrollToOffice()
    await page.waitForTimeout(350)
    const metrics = await geometry()
    assertGeometry(metrics, label)
    await page.screenshot({ path: resolve(output, `office-width-${label}.png`), fullPage: true })
    if (viewport.width >= 1000) {
      await page.mouse.move(
        metrics.canvas.x + metrics.canvas.width / 2,
        Math.min(metrics.canvas.y + metrics.canvas.height / 2, viewport.height - 100),
      )
      await page.mouse.wheel(0, 240)
      await page.waitForTimeout(150)
      assert.equal(await page.evaluate(() => window.scrollY), 0, `${label}: wheel does not scroll the office page`)
      assert.equal(await page.locator('.office-camera-controls span').innerText(), '100%',
        `${label}: wheel leaves the overview at 100%`)
    }

    const dock = page.locator('.office-agent-dock')
    if (viewport.width >= 1000) {
      assert.equal(await dock.evaluate(element => element.scrollWidth <= element.clientWidth + 1), true,
        `${label}: all seven owl cards fit without horizontal scrolling`)
    }
    await dock.scrollIntoViewIfNeeded()
    assert.deepEqual(await dock.locator('.office-agent-tab-copy strong').allTextContents(), names,
      `${label}: all seven owl names remain available`)
    const dockBox = await dock.boundingBox()
    const canvasBox = await canvas.boundingBox()
    assert.ok(dockBox.y >= canvasBox.y + canvasBox.height - 1, `${label}: dock follows the full office`)

    for (const name of names) {
      const tab = dock.getByRole('button', { name: new RegExp(`^Buka detail ${name}(?:,|$)`) })
      await tab.scrollIntoViewIfNeeded()
      const text = await tab.locator('.office-agent-tab-copy small').evaluate(element => {
        const style = getComputedStyle(element)
        const parentStyle = getComputedStyle(element.parentElement)
        return {
          role: element.textContent.trim(),
          display: style.display,
          parentDisplay: parentStyle.display,
          visibility: style.visibility,
          overflow: style.textOverflow,
          fontSize: parseFloat(style.fontSize),
          width: element.clientWidth,
          height: element.clientHeight,
          contentWidth: element.scrollWidth,
          contentHeight: element.scrollHeight,
        }
      })
      assert.ok(text.role.length > 0, `${label}: ${name} has a role description`)
      assert.ok(text.display !== 'none' && text.parentDisplay !== 'none' && text.visibility === 'visible',
        `${label}: ${name}'s role is visible`)
      assert.notEqual(text.overflow, 'ellipsis', `${label}: ${name}'s role is not ellipsized`)
      assert.ok(text.width > 0 && text.height > 0 && text.fontSize >= 12,
        `${label}: ${name}'s role has readable dimensions`)
      assert.ok(text.contentWidth <= text.width + 1 && text.contentHeight <= text.height + 1,
        `${label}: ${name}'s full role fits its text box`)
    }
    await page.screenshot({ path: resolve(output, `office-width-dock-${label}.png`) })

    await dock.getByRole('button', { name: /^Buka detail PIXEL(?:,|$)/ }).click()
    await page.getByRole('dialog', { name: 'Detail PIXEL', exact: true }).waitFor()
    assert.ok((await page.locator('.office-story-paragraph').innerText()).length > 180,
      `${label}: agent details remain readable`)
    await page.getByRole('button', { name: 'Tutup detail', exact: true }).click()

    await clickWorld(790, 920)
    await page.getByRole('dialog', { name: 'Detail Finance Office', exact: true }).waitFor()
    await page.getByRole('button', { name: 'Tutup detail', exact: true }).click()

    await scrollToOffice()
    await page.getByRole('button', { name: 'Perbesar kantor', exact: true }).click()
    await page.waitForFunction(() => document.querySelector('.office-camera-controls span')?.textContent === '120%')
    await page.getByRole('button', { name: 'Tampilkan seluruh kantor', exact: true }).click()
    await page.waitForFunction(() => document.querySelector('.office-camera-controls span')?.textContent === '100%')
    assert.equal(await page.getByRole('button', { name: 'Perkecil kantor', exact: true }).isDisabled(), true)
    await page.waitForTimeout(300)

    // Open a free floor area, using the cropped camera's logical-world mapping.
    await clickWorld(1010, 350)
    await page.getByRole('dialog', { name: 'Detail Tutor Room', exact: true }).waitFor()
    await page.getByRole('button', { name: 'Tutup detail', exact: true }).click()

    await clickWorld(726, 238)
    await page.getByRole('dialog', { name: 'Detail Meja riset', exact: true }).waitFor()
    await page.getByRole('button', { name: 'Tutup detail', exact: true }).click()

    await scrollToOffice()
    await page.getByRole('button', { name: 'Atur furnitur', exact: true }).click()
    await page.getByRole('button', { name: 'Selesai mengatur furnitur', exact: true }).waitFor()
    const catalog = page.locator('.owl-workshop-catalog')
    await catalog.waitFor({ state: 'visible' })
    const plant = page.getByRole('button', { name: 'Tambah Tanaman', exact: true })
    await plant.scrollIntoViewIfNeeded()
    assert.equal(await plant.isVisible(), true, `${label}: furniture catalog remains reachable`)
    await page.screenshot({ path: resolve(output, `office-width-editor-${label}.png`) })
    if (viewport.width >= 1000) {
      await plant.click()
      await clickWorld(500, 560)
      await page.getByRole('button', { name: 'Hapus tanaman', exact: true }).click()
      assert.match(await page.getByRole('status').innerText(), /dihapus/,
        `${label}: furniture can be placed and removed with the fitted camera`)
    }
    await page.getByRole('button', { name: 'Selesai', exact: true }).click()
    await page.waitForTimeout(300)
    assertGeometry(await geometry(), `${label} after closing editor`)

    console.log(`PASS ${label}: canvas ${Math.round(metrics.canvas.width)}×${Math.round(metrics.canvas.height)}, full roles, zoom/reset, agent/room details, furniture catalog`)
  }
  assert.deepEqual(errors, [], 'No browser runtime errors')
  console.log(`Screenshots: ${output}`)
} finally {
  await browser.close()
}
