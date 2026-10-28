#!/usr/bin/env node
// html-report のレイアウト検査（実行側）。
//   node layout-check.mjs /tmp/<topic>.html [--widths 1280,1000,640,400] [--json]
// Playwright で Google Chrome（channel: chrome）を headless 起動し、各幅で layout-check.browser.js を実行する。
// FAIL が 1 つでもあれば終了コード 1。Playwright が見つからなければ、chrome-devtools MCP で同じ検査をする手順を出して終了コード 2。
import { createRequire } from 'node:module'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { pathToFileURL, fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { homedir } from 'node:os'

const here = dirname(fileURLToPath(import.meta.url))
const browserScript = readFileSync(join(here, 'layout-check.browser.js'), 'utf8')

const args = process.argv.slice(2)
const file = args.find((a) => !a.startsWith('--'))
const widthsArg = args.includes('--widths') ? args[args.indexOf('--widths') + 1] : '1280,1000,640,400'
const asJson = args.includes('--json')
if (!file) {
  console.error('usage: node layout-check.mjs <report.html> [--widths 1280,1000,640,400] [--json]')
  process.exit(2)
}
const target = resolve(file)
if (!existsSync(target)) {
  console.error(`not found: ${target}`)
  process.exit(2)
}

// Playwright の置き場所は環境で違うので、順に探す（固定の依存を skill に持たせない）
function findPlaywright() {
  const candidates = []
  if (process.env.PLAYWRIGHT_MODULE_DIR) candidates.push(process.env.PLAYWRIGHT_MODULE_DIR)
  const npx = join(homedir(), '.npm', '_npx')
  if (existsSync(npx)) {
    for (const d of readdirSync(npx)) candidates.push(join(npx, d, 'node_modules', 'playwright'))
  }
  candidates.push(join(homedir(), 'src', 'github.com', 'mm-engineer', 'qb_product_main', 'frontend', 'node_modules', 'playwright'))
  for (const c of candidates) {
    if (existsSync(join(c, 'package.json'))) {
      try { return createRequire(join(c, 'package.json'))(c) } catch { /* 次へ */ }
    }
  }
  try { return createRequire(import.meta.url)('playwright') } catch { return null }
}

const pw = findPlaywright()
if (!pw) {
  console.error([
    'Playwright が見つかりません。chrome-devtools MCP で同じ検査ができます:',
    `  1. new_page で ${pathToFileURL(target).href} を開く`,
    `  2. evaluate_script に sourcePath=${join(here, 'layout-check.browser.js')}（format: function）を渡す`,
    '  3. resize_page で幅を変えて 2 と同じことを繰り返す（1000 と 640 は見る）',
    'Playwright の場所を指定するなら PLAYWRIGHT_MODULE_DIR=<node_modules/playwright へのパス>',
  ].join('\n'))
  process.exit(2)
}

const widths = widthsArg.split(',').map((w) => parseInt(w, 10)).filter((w) => w > 0)
let browser
try {
  browser = await pw.chromium.launch({ channel: 'chrome', headless: true })
} catch {
  browser = await pw.chromium.launch({ headless: true })
}
const results = []
try {
  for (const width of widths) {
    const page = await browser.newPage({ viewport: { width, height: 900 } })
    await page.goto(pathToFileURL(target).href, { waitUntil: 'load' })
    await page.evaluate(() => document.fonts.ready)
    await page.waitForTimeout(200)
    const report = await page.evaluate(`(${browserScript})()`)
    results.push(report)
    await page.close()
  }
} finally {
  await browser.close()
}

const totalFails = results.reduce((n, r) => n + r.fails.length, 0)
if (asJson) {
  console.log(JSON.stringify({ file: target, results, ok: totalFails === 0 }, null, 2))
} else {
  console.log(`layout-check: ${target}`)
  for (const r of results) {
    const mark = r.fails.length ? 'FAIL' : 'ok  '
    console.log(`\n[${mark}] width ${r.width}px (height ${r.height}px): fail ${r.fails.length}, warn ${r.warns.length}, info ${r.info.length}`)
    for (const f of r.fails) console.log(`  FAIL ${f.kind}: ${f.detail}`)
    for (const w of r.warns) console.log(`  warn ${w.kind}: ${w.detail}`)
    for (const i of r.info) console.log(`  info ${i.kind}: ${i.detail}`)
  }
  console.log(`\n${totalFails === 0 ? 'OK: 崩れの候補はありません' : `NG: FAIL ${totalFails} 件。直してからもう一度実行する`}`)
}
process.exit(totalFails === 0 ? 0 : 1)
