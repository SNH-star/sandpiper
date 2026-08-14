// Default filters used when drawing a random run, shared by the search page
// form and the sticky search bar's empty-query fallback.
export const RANDOM_DEFAULTS = {
  host: false,
  non_human_host: true,
  ecological: true,
  two_gbp: true,
  exclude_strict_low_complexity: true
} as const
