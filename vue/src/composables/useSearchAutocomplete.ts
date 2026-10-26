// Drives the universal search bar's autocomplete: suggests key names while
// typing before ":", suggests real values while typing after it, and
// supports Tab-to-cycle ghost-text completion. Shared between Search.vue's
// main bar and App.vue's sticky bar so both behave identically.
//
// Ranking (see docs/superpowers/specs/2026-09-14-search-bar-autocomplete-design.md,
// "Ranking -- hybrid"): key names have no database-frequency concept, so
// they sort alphabetically; enum values (SearchFieldDef.values) and live
// values both sort by total count, descending, so index 0 is always the
// highest-count match and Tab cycles from most to least common.
import axios from 'axios'
import { ref } from 'vue'
import { SEARCH_FIELDS, SearchFieldDef } from '@/constants/searchFields'

const MAX_SUGGESTIONS = 8
const MIN_LIVE_QUERY_LENGTH = 2
const LIVE_DEBOUNCE_MS = 300

export interface Suggestion {
  kind: 'key' | 'value'
  label: string
  insertKey: string
  insertValue?: string
  count?: number | null
}

export interface ActiveSegment {
  start: number
  end: number
  key: string | null
  value: string
}

// Finds the comma-delimited "key: value" segment the caret currently sits
// in, e.g. for "country: Australia, platform: illu|" (caret at "|"):
// { start: 21, end: 35, key: 'platform', value: 'illu' }
//
// `caret` must be a definite number here, not `undefined` -- callers read it
// from `inputEl.selectionStart`, and if that element lookup ever fails,
// `String.prototype.slice(0, undefined)` silently means "to the end of the
// string" while `String.prototype.indexOf(',', undefined)` silently means
// "search from position 0", a mismatched pair of fallbacks that corrupts
// `end` for any query with more than one clause (verified: for
// "platform: ILLUMINA, taxonomy: X" with caret=undefined, `start` lands
// right after the comma but `end` lands on that same comma, so `end < start`
// and the accepted suggestion gets spliced in on top of, rather than
// replacing, the existing text -- producing doubled clauses like
// "taxonomy: taxonomy: ..."). Defaulting explicitly to text.length removes
// the ambiguity outright instead of relying on the two built-ins agreeing.
// Search queries are comma-separated, but a value can contain commas when
// wrapped in double quotes, e.g. location: "Pacific Ocean: Oahu, Kaneohe Bay".
// Same rule as the backend's split_query_parts (backend/api/api.py).

// Positions of the commas that separate parts (not those inside quotes).
function separatorCommas (text: string): number[] {
  const commas: number[] = []
  let quoted = false
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '"') quoted = !quoted
    else if (text[i] === ',' && !quoted) commas.push(i)
  }
  return commas
}

/** 'a: 1, b: "x, y"' -> ['a: 1', 'b: "x, y"'] */
export function splitQueryParts (text: string): string[] {
  const parts: string[] = []
  let start = 0
  for (const comma of [...separatorCommas(text), text.length]) {
    const part = text.slice(start, comma).trim()
    if (part) parts.push(part)
    start = comma + 1
  }
  return parts
}

/** A value as written into a query: quoted only when it contains a comma. */
export function quoteQueryValue (value: string): string {
  return value.includes(',') ? `"${value.replace(/"/g, '')}"` : value
}

/** '"Oahu, Kaneohe Bay"' -> 'Oahu, Kaneohe Bay'; unquoted values unchanged. */
export function unquoteQueryValue (value: string): string {
  const v = value.trim()
  return v.length >= 2 && v.startsWith('"') && v.endsWith('"') ? v.slice(1, -1).trim() : v
}

export function splitActiveSegment (text: string, caret: number): ActiveSegment {
  const pos = typeof caret === 'number' ? caret : text.length
  const commas = separatorCommas(text)
  const before = commas.filter(c => c < pos)
  const start = before.length ? before[before.length - 1] + 1 : 0
  const after = commas.find(c => c >= pos)
  const end = after === undefined ? text.length : after
  const segment = text.slice(start, pos)
  const m = segment.match(/^\s*([\w\s]*?)\s*:\s*(.*)$/)
  return {
    start,
    end,
    key: m ? m[1].trim() : null,
    value: m ? m[2] : segment.trim(),
  }
}

type FetchLiveValues = (
  field: string, query: string, signal?: AbortSignal
) => Promise<{ value: string; count: number | null }[]>

/**
 * Run a live-value fetch that a newer keystroke can abort. Resolves to null
 * when the request was aborted (the caller drops it, as it drops stale ones).
 */
async function fetchSupersedable (
  fetchLiveValues: FetchLiveValues, field: string, query: string, signal: AbortSignal
) {
  try {
    return await fetchLiveValues(field, query, signal)
  } catch (error) {
    if (axios.isCancel(error)) return null
    throw error
  }
}

// Shared by both the "key: value" bar engine (useSearchAutocomplete) and the
// single-field engine (useFieldValueAutocomplete, for the Advanced options
// panel's individual inputs) -- same field-value ranking rules apply either
// way (spec: "Ranking -- hybrid").
function staticValueSuggestions (field: SearchFieldDef, rawValue: string): Suggestion[] {
  const q = rawValue.toLowerCase()
  return (field.values || [])
    .filter(v => v.value.toLowerCase().includes(q))
    .sort((a, b) => b.count - a.count)
    .slice(0, MAX_SUGGESTIONS)
    .map(v => ({
      kind: 'value',
      // Value only: counts were easy to misread, and are still used for ordering.
      label: v.value,
      insertKey: field.key,
      insertValue: v.value,
      count: v.count,
    }))
}

function liveRowsToSuggestions (field: SearchFieldDef, rows: { value: string; count: number | null }[]): Suggestion[] {
  // Rows already arrive count-desc sorted (the backend's
  // order_by(func.count().desc()), or taxonomy_search_hints' own
  // "order by ... name" for the one live field with no count).
  return rows.slice(0, MAX_SUGGESTIONS).map(r => ({
    kind: 'value',
    label: r.value,
    insertKey: field.key,
    insertValue: r.value,
    count: r.count,
  }))
}

// `getFields` lets one bar switch key sets (metagenome / amplicon) without
// a second engine; it is read on every keystroke, so it can follow a mode
// that changes while the bar is mounted.
export function useSearchAutocomplete (
  fetchLiveValues: FetchLiveValues,
  getFields: () => SearchFieldDef[] = () => SEARCH_FIELDS
) {
  const suggestions = ref<Suggestion[]>([])
  const activeIndex = ref(0)
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let requestId = 0
  let inFlight: AbortController | null = null

  function setSuggestions (list: Suggestion[]) {
    suggestions.value = list
    activeIndex.value = 0
  }

  function onInput (text: string, caret: number) {
    if (debounceTimer) clearTimeout(debounceTimer)
    requestId++
    inFlight?.abort()
    const seg = splitActiveSegment(text, caret)
    const fields = getFields()

    if (seg.key === null) {
      const q = seg.value.toLowerCase()
      setSuggestions(q.length < 1 ? [] : fields
        .filter(f => f.key.includes(q) || f.aliases.some(a => a.includes(q)))
        .sort((a, b) => a.key.localeCompare(b.key))
        .slice(0, MAX_SUGGESTIONS)
        .map(f => ({ kind: 'key', label: f.key, insertKey: f.key })))
      return
    }

    const typedKey = seg.key.toLowerCase()
    const field = fields.find(f => f.key === typedKey || f.aliases.includes(typedKey))
    if (!field) { setSuggestions([]); return }

    if (field.values) {
      setSuggestions(staticValueSuggestions(field, seg.value))
      return
    }

    if (field.liveField && seg.value.length >= MIN_LIVE_QUERY_LENGTH) {
      const thisRequestId = requestId
      debounceTimer = setTimeout(async () => {
        inFlight?.abort()
        inFlight = new AbortController()
        const rows = await fetchSupersedable(fetchLiveValues, field.liveField as string, seg.value, inFlight.signal)
        if (rows === null || thisRequestId !== requestId) return // aborted, or a newer keystroke superseded this fetch
        setSuggestions(liveRowsToSuggestions(field, rows))
      }, LIVE_DEBOUNCE_MS)
      return
    }

    setSuggestions([])
  }

  // Tab does not move focus or insert a tab character while suggestions are
  // open (caller must @keydown.tab.prevent only when suggestions.value.length
  // > 0, letting Tab behave normally otherwise) -- it advances the ghost-text
  // candidate instead, wrapping back to the first.
  function cycleNext () {
    if (suggestions.value.length === 0) return
    activeIndex.value = (activeIndex.value + 1) % suggestions.value.length
  }

  function applySuggestion (text: string, caret: number, s: Suggestion) {
    const seg = splitActiveSegment(text, caret)
    // seg.start sits right after a preceding comma (or at 0 with none) --
    // the ORIGINAL segment there carried whatever whitespace preceded it
    // ("platform: ILLUMINA,[ ]taxonomy: ..."), which gets discarded along
    // with the rest of the segment's old content. Re-add exactly one space
    // whenever this isn't the first clause, rather than dropping it (bare
    // "ILLUMINA,taxonomy:...") or trusting the original's exact whitespace
    // count (0, 1, or more spaces all collapse to one, consistently).
    const spacer = seg.start > 0 ? ' ' : ''
    const replacement = s.kind === 'key' ? `${s.insertKey}: ` : `${s.insertKey}: ${quoteQueryValue(s.insertValue ?? '')}`
    const newText = text.slice(0, seg.start) + spacer + replacement + text.slice(seg.end)
    setSuggestions([])
    return { text: newText, caret: seg.start + spacer.length + replacement.length }
  }

  function clear () {
    if (debounceTimer) clearTimeout(debounceTimer)
    setSuggestions([])
  }

  return { suggestions, activeIndex, onInput, cycleNext, applySuggestion, clear }
}

// Single-field variant for the Advanced options panel's individual inputs
// (Country, Platform, Organism, ...) -- each of those already knows which
// field it is (its own v-model), so there's no "key: value" segment to
// parse, just "what values match what's typed so far for this field."
// Reuses the exact same ranking rules and Tab-cycle mechanics as the bar's
// engine above; PresenceField.vue is the primary consumer.
export function useFieldValueAutocomplete (fieldKey: string | undefined, fetchLiveValues: FetchLiveValues) {
  const field = fieldKey ? SEARCH_FIELDS.find(f => f.key === fieldKey) : undefined
  const suggestions = ref<Suggestion[]>([])
  const activeIndex = ref(0)
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let requestId = 0
  let fieldInFlight: AbortController | null = null

  function setSuggestions (list: Suggestion[]) {
    suggestions.value = list
    activeIndex.value = 0
  }

  function onInput (value: string) {
    if (debounceTimer) clearTimeout(debounceTimer)
    requestId++
    fieldInFlight?.abort()
    if (!field) { setSuggestions([]); return }

    if (field.values) {
      setSuggestions(value.length < 1 ? [] : staticValueSuggestions(field, value))
      return
    }

    if (field.liveField && value.length >= MIN_LIVE_QUERY_LENGTH) {
      const thisRequestId = requestId
      debounceTimer = setTimeout(async () => {
        fieldInFlight?.abort()
        fieldInFlight = new AbortController()
        const rows = await fetchSupersedable(fetchLiveValues, field.liveField as string, value, fieldInFlight.signal)
        if (rows === null || thisRequestId !== requestId) return
        setSuggestions(liveRowsToSuggestions(field, rows))
      }, LIVE_DEBOUNCE_MS)
      return
    }

    setSuggestions([])
  }

  function cycleNext () {
    if (suggestions.value.length === 0) return
    activeIndex.value = (activeIndex.value + 1) % suggestions.value.length
  }

  // No text splicing needed here (unlike applySuggestion above) -- the
  // field's entire value just becomes the suggestion's value outright.
  function acceptValue (s: Suggestion): string {
    setSuggestions([])
    return s.insertValue ?? ''
  }

  function clear () {
    if (debounceTimer) clearTimeout(debounceTimer)
    setSuggestions([])
  }

  return { suggestions, activeIndex, onInput, cycleNext, acceptValue, clear }
}
