// html-report のレイアウト検査（ブラウザ側）。
// ページの中で実行して、崩れの候補を JSON で返す。layout-check.mjs（Playwright）からも、
// chrome-devtools MCP の evaluate_script（sourcePath にこのファイル、format は function）からも同じ結果になる。
// 検出するのは、この skill のレポートで実際に起きた崩れ:
//   1. ページ本体の横スクロール、要素が画面の外に出る
//   2. 箱からはみ出す文字・識別子（overflow-wrap が無い）
//   3. 入れ子のリストに行の grid が効いて、文字が細い列に押し込まれる
//   4. 多段の grid にコードブロックを入れて、コードが横スクロールになる
//   5. SVG の文字が箱の外や viewBox の外に出る
() => {
  const de = document.documentElement
  const vw = window.innerWidth
  const fails = []
  const warns = []
  const info = []
  const label = (el) => {
    const cls = typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).join('.') : ''
    const text = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)
    return `${el.tagName.toLowerCase()}${cls} 「${text}」`
  }
  const scrolls = (el) => {
    const o = getComputedStyle(el).overflowX
    return o === 'auto' || o === 'scroll'
  }

  // 1. ページ本体の横スクロールと、画面外に出る要素
  if (de.scrollWidth > de.clientWidth + 1) {
    fails.push({ kind: 'page-scrolls-sideways', detail: `scrollWidth ${de.scrollWidth} > clientWidth ${de.clientWidth}` })
  }
  for (const el of document.querySelectorAll('body *')) {
    if (el instanceof SVGElement) continue
    const r = el.getBoundingClientRect()
    if (r.width === 0) continue
    // 横スクロールする箱の中身は、その箱が受け持つ
    if (el.closest('pre, .tbl, .canvas, [style*="overflow"]') && !el.matches('pre, .tbl, .canvas')) continue
    if (r.right > vw + 1 || r.left < -1) {
      fails.push({ kind: 'outside-viewport', detail: `${label(el)} left ${Math.round(r.left)} right ${Math.round(r.right)} (viewport ${vw})` })
    }
  }

  // 2. 箱からはみ出す中身（横スクロールを持たない箱）
  for (const el of document.querySelectorAll('body *')) {
    if (el instanceof SVGElement) continue
    const cs = getComputedStyle(el)
    if (cs.display === 'inline' || el.clientWidth === 0) continue
    if (scrolls(el)) continue
    if (el.scrollWidth > el.clientWidth + 2) {
      fails.push({ kind: 'content-overflows-box', detail: `${label(el)} scrollWidth ${el.scrollWidth} > clientWidth ${el.clientWidth}` })
    }
  }

  // 3. 細い列に押し込まれた文章（入れ子の li に行の grid が効く、など）。
  //    要素ではなく文字そのものの描画幅を測る。grid の無名アイテムに入った文字は要素の幅では分からない
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  const lineLimit = Math.min(200, vw * 0.4)
  let node
  while ((node = walker.nextNode())) {
    const text = node.textContent.replace(/\s+/g, ' ').trim()
    if (text.length < 40) continue
    const parent = node.parentElement
    if (!parent || parent.closest('svg, pre, script, style')) continue
    const range = document.createRange()
    range.selectNodeContents(node)
    const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0)
    if (rects.length < 3) continue
    const widest = Math.max(...rects.map((r) => r.width))
    if (widest < lineLimit) {
      fails.push({ kind: 'text-in-narrow-column', detail: `${label(parent)} 行幅 ${Math.round(widest)}px で ${rects.length} 行に折り返し。入れ子の要素に親の grid が効いていないか見る` })
    }
  }

  // 4. コードブロック: 細い列に入って収まらないもの（FAIL）、広いが 1 行が長くて横スクロールするもの（warn）
  for (const pre of document.querySelectorAll('pre')) {
    const w = pre.getBoundingClientRect().width
    const head = (pre.textContent || '').trim().split('\n')[0].slice(0, 40)
    if (pre.scrollWidth <= pre.clientWidth + 1) continue
    if (w > 0 && w < Math.min(480, vw * 0.7)) {
      fails.push({ kind: 'code-in-narrow-column', detail: `pre 「${head}」 width ${Math.round(w)}px に収まらない（scrollWidth ${pre.scrollWidth}）。多段 grid の外に出すか .option.wide にする` })
    } else {
      warns.push({ kind: 'code-scrolls-sideways', detail: `pre 「${head}」 scrollWidth ${pre.scrollWidth} > clientWidth ${pre.clientWidth}。行を短くするか、1 行が長いだけなら pre.wrap` })
    }
  }

  // 5. SVG の文字が箱や viewBox の外に出る
  for (const svg of document.querySelectorAll('svg')) {
    const vb = svg.viewBox && svg.viewBox.baseVal
    if (!vb || vb.width === 0) continue
    const rects = Array.from(svg.querySelectorAll('rect')).map((r) => ({
      x: r.x.baseVal.value, y: r.y.baseVal.value, w: r.width.baseVal.value, h: r.height.baseVal.value,
    }))
    for (const t of svg.querySelectorAll('text')) {
      let b
      try { b = t.getBBox() } catch { continue }
      if (b.width === 0) continue
      if (b.x < vb.x - 1 || b.x + b.width > vb.x + vb.width + 1 || b.y < vb.y - 1 || b.y + b.height > vb.y + vb.height + 1) {
        fails.push({ kind: 'svg-text-outside-viewbox', detail: `text 「${(t.textContent || '').slice(0, 30)}」 x ${Math.round(b.x)}..${Math.round(b.x + b.width)} (viewBox ${vb.width}x${vb.height})` })
        continue
      }
      // 文字の中心が入っている箱があれば、その箱に収まっているか
      const cx = b.x + b.width / 2
      const cy = b.y + b.height / 2
      const box = rects.find((r) => cx >= r.x && cx <= r.x + r.w && cy >= r.y && cy <= r.y + r.h)
      if (box && (b.x < box.x - 1 || b.x + b.width > box.x + box.w + 1)) {
        fails.push({ kind: 'svg-text-wider-than-box', detail: `text 「${(t.textContent || '').slice(0, 30)}」 width ${Math.round(b.width)} > box ${Math.round(box.w)}。箱を広げるか文字を短くする` })
      }
    }
  }

  // フォント（崩れではないが、フォールバックのまま見ていると気付きにくい）
  const families = new Set()
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (rule.style && rule.selectorText === ':root') {
          for (const name of rule.style) {
            if (name.startsWith('--') && /display|body/.test(name)) {
              const first = rule.style.getPropertyValue(name).split(',')[0].trim().replace(/^"|"$/g, '')
              if (first) families.add(first)
            }
          }
        }
      }
    } catch { /* 外部シートは読めない */ }
  }
  for (const f of families) {
    if (!document.fonts.check(`16px "${f}"`)) info.push({ kind: 'font-not-loaded', detail: `${f}（フォールバックで表示中。オフラインなら無視してよい）` })
  }

  return { width: vw, height: de.scrollHeight, fails, warns, info }
}
