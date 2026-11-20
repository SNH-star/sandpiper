#!/usr/bin/env node
// Installs a screenshot as the link-preview image and writes a page that shows it as a Twitter/X card would.
// No browser automation and no dependencies, so it runs on any Node 14+ (including the cluster's).
//
//   1. Open the site's home page in your browser, press F12, switch on the device toolbar and set the size to
//      1200 x 630, then use "Capture screenshot" (Chrome: the three dots in the toolbar). Save the PNG anywhere.
//   2. npm run og-preview -- path/to/screenshot.png
//   3. Open vue/.og-preview/card.html in a browser to see the card. Not right? Take another screenshot, run again.
//
// Each run overwrites public/og-preview.png (and dist/og-preview.png when dist exists). With no screenshot given,
// it only rebuilds the card from the image already in public/ (use that after drawing the image another way, such as
// scripts/og_preview_compose.py, which needs no browser). The card's title, description and domain come
// from the Open Graph tags in index.html.
import { readFileSync, writeFileSync, copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const IMAGE = join(ROOT, 'public', 'og-preview.png')
const DIST_IMAGE = join(ROOT, 'dist', 'og-preview.png')
const CARD_DIR = join(ROOT, '.og-preview')
const WIDTH = 1200
const HEIGHT = 630
const PNG_SIGNATURE = '89504e470d0a1a0a'
const IHDR_OFFSET = 16

function pngSize (bytes) {
  if (bytes.subarray(0, 8).toString('hex') !== PNG_SIGNATURE) throw new Error('That file is not a PNG image.')
  return { width: bytes.readUInt32BE(IHDR_OFFSET), height: bytes.readUInt32BE(IHDR_OFFSET + 4) }
}

function tag (html, property) {
  const match = html.match(new RegExp(`<meta[^>]+(?:property|name)="${property}"[^>]+content="([^"]*)"`))
  return match ? match[1] : ''
}

const escapeHtml = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;')

function cardPage ({ title, description, domain, image }) {
  const card = (theme, background, border, ink, muted) => `
    <h2>${theme}</h2>
    <div class="card" style="background:${background};border-color:${border}">
      <img src="${image}" alt="">
      <div class="text"><span style="color:${muted}">${escapeHtml(domain)}</span>
        <strong style="color:${ink}">${escapeHtml(title)}</strong>
        <span style="color:${muted}">${escapeHtml(description)}</span></div>
    </div>`
  return `<!doctype html><html lang="en"><meta charset="utf-8"><title>Link preview</title>
<style>
  body { margin: 0; padding: 2rem; font-family: system-ui, sans-serif; background: #e8eaed; }
  h1, h2 { font-weight: 600; margin: 0 0 .75rem; font-size: 1rem; color: #444; }
  h2 { margin-top: 1.5rem; }
  .card { width: 504px; max-width: 100%; border: 1px solid; border-radius: 16px; overflow: hidden; }
  .card img { display: block; width: 100%; aspect-ratio: ${WIDTH} / ${HEIGHT}; object-fit: cover; }
  .text { display: flex; flex-direction: column; gap: 2px; padding: 12px 14px; font-size: 14px; line-height: 1.3; }
  .text strong { font-size: 15px; font-weight: 600; }
  .note { margin-top: 1.5rem; font-size: .85rem; color: #555; max-width: 504px; }
</style>
<h1>How the link looks on Twitter/X (large summary card)</h1>
${card('Light', '#ffffff', '#cfd9de', '#0f1419', '#536471')}
${card('Dark', '#000000', '#2f3336', '#e7e9ea', '#71767b')}
<p class="note">Image: ${WIDTH} x ${HEIGHT} px. Twitter/X crops to this shape, so keep text away from the edges. Other sites (Slack, Facebook, email) draw similar cards.</p>
</html>
`
}

function main () {
  const source = process.argv[2]
  if (source) {
    const bytes = readFileSync(resolve(source))
    const { width, height } = pngSize(bytes)
    if (width !== WIDTH || height !== HEIGHT) {
      console.warn(`Warning: the screenshot is ${width} x ${height}; link previews are ${WIDTH} x ${HEIGHT}, so it will be cropped or stretched.`)
    }
    copyFileSync(resolve(source), IMAGE)
    console.log(`Installed ${source} as ${IMAGE}`)
  } else if (!existsSync(IMAGE)) {
    throw new Error('No screenshot given and public/og-preview.png does not exist. Usage: npm run og-preview -- screenshot.png')
  }
  if (existsSync(dirname(DIST_IMAGE))) copyFileSync(IMAGE, DIST_IMAGE)
  const html = readFileSync(join(ROOT, 'index.html'), 'utf8')
  const url = tag(html, 'og:url')
  const image = `data:image/png;base64,${readFileSync(IMAGE).toString('base64')}`
  mkdirSync(CARD_DIR, { recursive: true })
  const page = join(CARD_DIR, 'card.html')
  writeFileSync(page, cardPage({
    title: tag(html, 'og:title') || 'Sandpiper',
    description: tag(html, 'og:description'),
    domain: url.replace(/^https?:\/\//, '').replace(/\/$/, ''),
    image
  }))
  console.log(`Open ${page} in a browser to see the card.`)
}

try { main() } catch (error) { console.error(error.message); process.exit(1) }
