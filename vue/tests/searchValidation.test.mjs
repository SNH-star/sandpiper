// Run with: node --test vue/tests
import test from 'node:test'
import assert from 'node:assert/strict'
import {
  validateField, validateIndicpiper, validateQueryParts, indicpiperScoreFraction, INDICPIPER_SCORE_MESSAGE, SYNTAX_MESSAGE,
} from '../src/utils/searchValidation.js'

test('indicpiper accepts fractions 0-1 and percentages 1-100', () => {
  for (const v of ['soil>=0.1', 'soil>0.5', '>0.5', 'soil>=10', 'soil>=100', '<=1', 'soil<0', 'marine>=1']) {
    assert.equal(validateIndicpiper(v), null, v)
  }
})

test('indicpiper rejects scores above 100 or negative', () => {
  assert.equal(validateIndicpiper('soil>=200'), INDICPIPER_SCORE_MESSAGE)
  assert.equal(validateIndicpiper('>100.5'), INDICPIPER_SCORE_MESSAGE)
  assert.equal(validateIndicpiper('soil>-1'), INDICPIPER_SCORE_MESSAGE)
})

test('indicpiper: 1 means 1 percent, other values below 1 are fractions', () => {
  assert.equal(indicpiperScoreFraction(1), 0.01)
  assert.equal(indicpiperScoreFraction(50), 0.5)
  assert.equal(indicpiperScoreFraction(0.5), 0.5)
  assert.equal(indicpiperScoreFraction(100), 1)
  assert.equal(indicpiperScoreFraction(0), 0)
  assert.equal(indicpiperScoreFraction(101), null)
})

test('indicpiper checks the habitat name and a bare number', () => {
  assert.equal(validateIndicpiper('soil'), null)
  assert.equal(validateIndicpiper('marine'), null)
  assert.equal(validateIndicpiper(''), null)
  assert.match(validateIndicpiper('moonbase'), /Unknown habitat/)
  assert.match(validateIndicpiper('50'), /Add a comparison/)
})

test('numeric fields reject impossible values', () => {
  assert.match(validateField('latitude', '200'), /-90 to 90/)
  assert.match(validateField('longitude', '10-400'), /-180 to 180/)
  assert.match(validateField('spf', '150'), /0 to 100/)
  assert.match(validateField('gbp', '-3'), /cannot be below 0/)
  assert.match(validateField('year', '20'), /1900 to/)
  assert.match(validateField('depth', '30-10'), /Range start/)
})

test('numeric fields accept real values, negatives and empty', () => {
  for (const [k, v] of [['latitude', '-33.8'], ['latitude', '-40-30'], ['latitude', '-40--30'], ['spf', '50-100'], ['spf', '>50'], ['year', '2010-2015'], ['temperature', ''], ['gbp', '>2']]) {
    assert.equal(validateField(k, v), null, `${k}=${v}`)
  }
  assert.equal(validateField('latitude', 'abc'), SYNTAX_MESSAGE)
})

test('validateQueryParts finds bad clauses through aliases and ignores free text', () => {
  const problems = validateQueryParts(['soil', 'habitat: soil>=200', 'lat: 95', 'country: Australia', 'year: 2015'])
  assert.deepEqual(problems.map(p => p.key), ['indicpiper', 'latitude'])
})
