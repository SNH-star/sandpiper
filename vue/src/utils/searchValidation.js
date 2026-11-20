// Sanity checks for the search syntax, shared by the Advanced search page and
// the run pages' filter bar so both refuse the same impossible values (a
// latitude of 200, an IndicPiper score of 250%, a range written backwards).
//
// Every function returns an error message, or null when the value is fine.
// Empty values are never errors: they mean "any value" (the Any buttons).
import { SEARCH_FIELDS, findSearchField } from '../constants/searchFields.ts'

const NUMBER = '-?\\d+(?:\\.\\d+)?'
const SINGLE_RE = new RegExp(`^${NUMBER}$`)
const RANGE_RE = new RegExp(`^(${NUMBER})-(${NUMBER})$`)
const COMPARISON_RE = new RegExp(`^(>=|<=|>|<)\\s*(${NUMBER})$`)
// Same split the backend uses (_parse_numeric_range): a "-" between digits is
// the range separator, so "-40-30" is -40 to 30 and "-40--30" is -40 to -30.
const RANGE_SPLIT_RE = /(?<=\d)-(?=-?\d)/

// Messages stay short enough for one line in a 260px field.
export const SYNTAX_MESSAGE = 'Use a number, 10-20 or >10'

// [min, max, what it measures]. Bounds are physical or historical limits, wide
// enough that no real sample is rejected. Fields with no natural upper limit
// only get a lower bound (Infinity).
const CURRENT_YEAR = new Date().getFullYear()
export const NUMERIC_LIMITS = {
  latitude: [-90, 90, 'Latitude'],
  longitude: [-180, 180, 'Longitude'],
  year: [1900, CURRENT_YEAR + 1, 'Year'],
  release_year: [1990, CURRENT_YEAR + 1, 'Year'],
  temperature: [-100, 150, 'Temperature'],
  depth: [-12000, 12000, 'Depth'],
  age: [0, Infinity, 'Age'],
  spf: [0, 100, 'SPF'],
  ksf: [0, 100, 'KSF'],
  gbp: [0, Infinity, 'Size'],
  reads: [0, Infinity, 'Reads'],
  read_length: [0, Infinity, 'Read length'],
}

function limitMessage ([min, max, label]) {
  if (max === Infinity) return `${label} cannot be below ${min}`
  return `${label} must be ${min} to ${max}`
}

// The numbers a numeric value contains, or null when it is not a number, range
// or comparison at all.
function numbersIn (text) {
  const comparison = text.match(COMPARISON_RE)
  if (comparison) return [Number(comparison[2])]
  if (SINGLE_RE.test(text)) return [Number(text)]
  if (RANGE_RE.test(text)) return text.split(RANGE_SPLIT_RE).map(Number)
  return null
}

export function validateNumeric (key, value) {
  const text = (value || '').trim()
  if (!text) return null
  const numbers = numbersIn(text)
  if (!numbers) return SYNTAX_MESSAGE
  const limits = NUMERIC_LIMITS[key]
  if (limits && numbers.some(n => n < limits[0] || n > limits[1])) return limitMessage(limits)
  if (numbers.length === 2 && numbers[0] > numbers[1]) return 'Range start is above its end'
  return null
}

// ---- IndicPiper ----------------------------------------------------------

const HABITATS = SEARCH_FIELDS.find(f => f.key === 'indicpiper').values.map(v => v.value)
const SCORE_RE = new RegExp(`^(.*?)\\s*(?:>=|<=|>|<)\\s*(${NUMBER})$`)

export const INDICPIPER_SCORE_MESSAGE = 'Score must be 0-1 or 1-100 (%)'

// A score typed as a fraction (0-1) or a percentage (1-100) as a fraction.
// 1 is read as 1%, not 100%; 100% is written 100. Returns null when out of range.
export function indicpiperScoreFraction (number) {
  if (!Number.isFinite(number) || number < 0 || number > 100) return null
  return number >= 1 ? number / 100 : number
}

export function validateIndicpiper (value) {
  const text = (value || '').trim()
  if (!text) return null
  const withScore = text.match(SCORE_RE)
  const name = (withScore ? withScore[1] : text).trim().toLowerCase()
  if (withScore && indicpiperScoreFraction(Number(withScore[2])) === null) return INDICPIPER_SCORE_MESSAGE
  if (!withScore && numbersIn(text)) return 'Add a comparison, e.g. soil>=10 or >0.5'
  if (name && !HABITATS.some(h => h.includes(name))) return `Unknown habitat "${name}"`
  return null
}

// ---- Whole queries --------------------------------------------------------

export function validateField (key, value) {
  if (key === 'indicpiper') return validateIndicpiper(value)
  if (key in NUMERIC_LIMITS) return validateNumeric(key, value)
  return null
}

const PART_RE = /^([\w\s]+?):\s*(.*)$/

// The problems in a typed query, one per bad "key: value" clause. `parts` is
// the query already split on its separating commas (splitQueryParts).
export function validateQueryParts (parts) {
  const problems = []
  for (const part of parts) {
    const m = part.match(PART_RE)
    const field = m && findSearchField(m[1])
    if (!field) continue
    const value = m[2].trim().replace(/^"(.*)"$/, '$1')
    const message = validateField(field.key, value)
    if (message) problems.push({ key: field.key, message })
  }
  return problems
}
