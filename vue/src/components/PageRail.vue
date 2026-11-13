<template>
  <nav class="page-rail" :class="{ 'has-strip': strip }" aria-label="On this page" :style="{ '--rail-top': top }">
    <p class="page-rail-title">On this page</p>
    <div class="page-rail-inner" :class="{ container: strip }">
      <div v-for="(block, index) in blocks" :key="index" class="page-rail-group">
        <p v-if="block.title" class="page-rail-group-title">{{ block.title }}</p>
        <div class="page-rail-links">
          <a
            v-for="link in block.links"
            :key="link.id"
            :href="'#' + link.id"
            :class="{ 'is-current': current === link.id }"
            :aria-current="current === link.id ? 'location' : null"
            @click.prevent="$emit('jump', link.id)">{{ link.label }}</a>
        </div>
      </div>
    </div>
  </nav>
</template>

<script>
// The "On this page" contents list, shared by the Statistics, About and Run pages so they look and behave
// alike and are changed together. Each page keeps its own scroll tracking: it passes the current section and
// jumps when the list says `jump`.
//
// Pass either `groups` (each { title, links: [{ id, label }] }, shown under their title) or a flat `items`
// ([{ id, label, start }], where `start` begins a new, untitled group after a gap).
//
// Wide windows (1440px and up) pin it in the gutter left of the content. Under that it is hidden, or with
// `strip` a row of links above the page's sections.
export default {
  name: 'PageRail',
  props: {
    groups: { type: Array, default: null },
    items: { type: Array, default: () => [] },
    // The id of the section the reader is in.
    current: { type: String, default: null },
    // Show a row of links under 1440px wide instead of hiding the list.
    strip: { type: Boolean, default: false },
    // How far below the top of the window the pinned list starts (a page with a taller header sets more).
    top: { type: String, default: '6.5rem' }
  },
  emits: ['jump'],
  computed: {
    blocks () {
      if (this.groups) return this.groups
      return this.items.reduce((blocks, item) => {
        if (item.start || blocks.length === 0) blocks.push({ title: '', links: [] })
        blocks[blocks.length - 1].links.push(item)
        return blocks
      }, [])
    }
  },
  watch: {
    // A window too short for the whole list: keep the current section's entry in view inside it.
    current () {
      this.$nextTick(() => {
        const link = this.$el.querySelector('a.is-current')
        if (!link || this.$el.scrollHeight <= this.$el.clientHeight) return
        const above = link.getBoundingClientRect().top - this.$el.getBoundingClientRect().top
        const below = link.getBoundingClientRect().bottom - this.$el.getBoundingClientRect().bottom
        if (above < 0) this.$el.scrollTop += above
        else if (below > 0) this.$el.scrollTop += below
      })
    }
  }
}
</script>

<style scoped>
/* Under 1440px: nothing, or a row of links above the sections. */
.page-rail { display: none; }
.page-rail.has-strip {
  display: block;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-rule);
}
.page-rail-title { display: none; }
.page-rail-group-title { display: none; }
.page-rail-inner { display: flex; gap: var(--space-6); overflow-x: auto; white-space: nowrap; scrollbar-width: none; }
.page-rail-inner::-webkit-scrollbar { display: none; }
.page-rail-group, .page-rail-links { display: contents; }
.page-rail-links a {
  position: relative;
  flex: none;
  padding: var(--space-3) 0;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-ink-muted);
  text-decoration: none;
  transition: color 0.15s;
}
/* The current section is marked in the accent, drawn in from the start. */
.page-rail-links a::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  background: var(--color-accent);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.2s var(--ease-spring);
}
/* A hairline in the gap before each new group. */
.page-rail-group + .page-rail-group .page-rail-links a:first-child::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--space-3));
  top: 30%;
  bottom: 30%;
  width: 1px;
  background: var(--color-rule);
}
.page-rail-links a:hover, .page-rail-links a.is-current { color: var(--color-ink); }
.page-rail-links a.is-current::after { transform: scaleX(1); }
.page-rail-links a:active { color: var(--color-accent-strong); }
.page-rail-links a:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; border-radius: 2px; }

/* 1440px and up: pinned in the empty gutter left of the content, which stays put. A quiet index hung off a
   hairline, the current entry picked out by an accent bar and a soft tint. Its weight never changes, so no
   entry re-wraps and moves the ones below. */
@media (min-width: 1440px) {
  .page-rail,
  .page-rail.has-strip {
    /* Fixed to the window's left edge: as the window narrows, the gap between the list and the content
       shrinks, and the list never moves. As wide as the gutter allows (6.5rem to 13rem) so entries wrap less. */
    position: fixed;
    top: var(--rail-top);
    z-index: 100;
    left: 1rem;
    display: block;
    width: clamp(6.5rem, calc((100vw - 1152px) / 2 - 2.5rem), 13rem);
    max-height: calc(100vh - 7rem);
    overflow-y: auto;
    /* A thin scrollbar and a fade, so a list taller than the window shows there is more below; the padding lets
       the last entries scroll clear of the fade. */
    scrollbar-width: thin;
    scrollbar-color: var(--color-rule) transparent;
    padding-bottom: 1rem;
    -webkit-mask-image: linear-gradient(to bottom, #000 calc(100% - 1rem), transparent);
    mask-image: linear-gradient(to bottom, #000 calc(100% - 1rem), transparent);
    background: none;
    border: 0;
  }
  .page-rail::-webkit-scrollbar { width: 4px; }
  .page-rail::-webkit-scrollbar-thumb { background: var(--color-rule); border-radius: 2px; }
  .page-rail-title {
    display: block;
    margin-bottom: var(--space-3);
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--color-ink-muted);
  }
  .page-rail-inner { display: block; overflow: visible; white-space: normal; max-width: none; margin: 0; }
  .page-rail-group { display: block; }
  .page-rail-group + .page-rail-group { margin-top: var(--space-4); }
  .page-rail-group-title {
    display: block;
    margin-bottom: var(--space-1);
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-ink);
  }
  .page-rail-links {
    display: block;
    border-left: 1px solid var(--color-rule);
  }
  .page-rail-links a {
    display: block;
    padding: 0.3rem var(--space-2) 0.3rem var(--space-3);
    border-radius: 0 var(--radius-bar) var(--radius-bar) 0;
    font-size: 0.8rem;
    font-weight: 400;
    line-height: 1.3;
    transition: color 0.15s, background-color 0.15s;
  }
  .page-rail-links a + a { margin-top: 1px; }
  .page-rail-group + .page-rail-group .page-rail-links a:first-child::before { display: none; }
  /* The accent bar sits on the hairline beside the current entry and grows down from its top. */
  .page-rail-links a::after {
    left: -1px;
    right: auto;
    top: 0;
    bottom: 0;
    width: 2px;
    height: auto;
    transform: scaleY(0);
    transform-origin: top;
    transition: transform 0.2s var(--ease-spring);
  }
  .page-rail-links a:hover { color: var(--color-ink); background-color: var(--color-track); }
  .page-rail-links a.is-current { color: var(--color-accent-strong); background-color: var(--color-surface-tint); }
  .page-rail-links a.is-current::after { transform: scaleY(1); }
  .page-rail-links a:focus-visible { outline-offset: 1px; }
}
/* Just over the breakpoint the gutter is narrow, so entries lose their side padding and get a smaller size. */
@media (min-width: 1440px) and (max-width: 1599px) {
  .page-rail-links a {
    padding-left: var(--space-2);
    padding-right: 0.15rem;
    font-size: 0.74rem;
    line-height: 1.25;
  }
}
/* A short window: tighter entries, so more of the list fits without scrolling. */
@media (min-width: 1440px) and (max-height: 900px) {
  .page-rail-links a {
    padding-top: 0.06rem;
    padding-bottom: 0.06rem;
    font-size: 0.72rem;
    line-height: 1.2;
  }
  .page-rail-group + .page-rail-group { margin-top: var(--space-3); }
}
@media (min-width: 1440px) and (max-height: 800px) {
  .page-rail-title { margin-bottom: var(--space-1); }
  .page-rail-group + .page-rail-group { margin-top: var(--space-2); }
  .page-rail-group-title { font-size: 0.8rem; margin-bottom: 0; }
  .page-rail-links a {
    padding-top: 0.03rem;
    padding-bottom: 0.03rem;
    font-size: 0.7rem;
    line-height: 1.15;
  }
}
@media (prefers-reduced-motion: reduce) {
  .page-rail-links a,
  .page-rail-links a::after {
    transition: none;
  }
}
</style>
