// The sample groups the group charts name, with one colour each (tokens in app.scss), so a group looks the same
// on every chart. Each side lists its groups in the order they are stacked.
const group = (key, label) => ({ key, label, colour: `var(--color-group-${key})` })

export const HOST_GROUPS = [group('plant', 'Plant'), group('bovine', 'Bovine'), group('pig', 'Pig'), group('human', 'Human'), group('mouse', 'Mouse')]
export const ECOLOGICAL_GROUPS = [
  group('soil', 'Soil'), group('sediment', 'Sediment'), group('marine', 'Marine'), group('freshwater', 'Freshwater'), group('aquatic', 'Aquatic')
]

export const groupColour = key => `var(--color-group-${key})`
