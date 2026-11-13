// Writes a resolution into a PNG. A browser's canvas saves PNGs with no resolution, so image software reports
// them as 72 or 96 dpi whatever their pixel count; the pHYs chunk added here states the real one.

const PNG_SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10]
// The IHDR chunk always comes first and is always 25 bytes (length, type, 13 of data, checksum); pHYs goes after it.
const IHDR_END = PNG_SIGNATURE.length + 25
const METRES_PER_INCH = 0.0254
const UNIT_METRE = 1
const PHYS_DATA_LENGTH = 9
const CHUNK_TYPE = [112, 72, 89, 115] // 'pHYs'

const CRC_TABLE = Array.from({ length: 256 }, (_, index) => {
  let value = index
  for (let bit = 0; bit < 8; bit++) value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1
  return value >>> 0
})

// The checksum PNG keeps after each chunk, over the chunk's type and data.
function crc32 (bytes) {
  const crc = bytes.reduce((value, byte) => CRC_TABLE[(value ^ byte) & 0xff] ^ (value >>> 8), 0xffffffff)
  return (crc ^ 0xffffffff) >>> 0
}

/**
 * A copy of a PNG that states its resolution. The PNG must have no pHYs chunk yet, as one saved from a canvas.
 * @param {Uint8Array} png the PNG file's bytes
 * @param {number} dpi pixels per inch
 * @returns {Uint8Array}
 */
export function withPngDpi (png, dpi) {
  if (!PNG_SIGNATURE.every((byte, index) => png[index] === byte)) throw new Error('Not a PNG file')
  const perMetre = Math.round(dpi / METRES_PER_INCH)
  const chunk = new Uint8Array(4 + CHUNK_TYPE.length + PHYS_DATA_LENGTH + 4)
  const view = new DataView(chunk.buffer)
  view.setUint32(0, PHYS_DATA_LENGTH)
  chunk.set(CHUNK_TYPE, 4)
  view.setUint32(8, perMetre)
  view.setUint32(12, perMetre)
  view.setUint8(16, UNIT_METRE)
  view.setUint32(17, crc32(chunk.subarray(4, 17)))
  const result = new Uint8Array(png.length + chunk.length)
  result.set(png.subarray(0, IHDR_END), 0)
  result.set(chunk, IHDR_END)
  result.set(png.subarray(IHDR_END), IHDR_END + chunk.length)
  return result
}
