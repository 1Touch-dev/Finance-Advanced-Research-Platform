export const POSITION_DIFF_DEFAULTS = {
  status: 'changed',
  sortBy: 'reported_value_diff_usd',
  sortDir: 'desc',
  limit: 100,
  offset: 0,
}

export const POSITION_DIFF_STATUS_OPTIONS = [
  { value: 'changed', label: 'Changed' },
  { value: 'new', label: 'New' },
  { value: 'increased', label: 'Increased' },
  { value: 'reduced', label: 'Reduced' },
  { value: 'unchanged', label: 'Unchanged' },
  { value: 'exited', label: 'Exited' },
  { value: 'all', label: 'All' },
]

export const POSITION_DIFF_SORT_OPTIONS = [
  { value: 'reported_value_diff_usd', label: 'Reported Value Diff (USD)' },
  { value: 'share_diff', label: 'Share Diff' },
  { value: 'current_reported_value_usd', label: 'Current Reported Value (USD)' },
  { value: 'previous_reported_value_usd', label: 'Previous Reported Value (USD)' },
  { value: 'issuer_name', label: 'Issuer Name' },
  { value: 'status', label: 'Status' },
]

export const POSITION_DIFF_SORT_DIRECTION_OPTIONS = [
  { value: 'asc', label: 'Ascending' },
  { value: 'desc', label: 'Descending' },
]

export const POSITION_DIFF_SECTION_LABELS = {
  institution: 'Institution',
  periods: 'Periods',
  filings: 'Filing Information',
  summary: 'Summary',
  highlights: 'Highlights',
  warnings: 'Warnings',
  dataQuality: 'Data Quality',
  positions: 'Position Differences',
  pagination: 'Pagination',
}

export const POSITION_DIFF_HIGHLIGHT_LABELS = {
  largest_buyers: 'Largest Buyers',
  largest_sellers: 'Largest Sellers',
  new_positions: 'New Positions',
  complete_exits: 'Complete Exits',
}

export const POSITION_DIFF_DATA_QUALITY_LABELS = {
  comparison_complete: 'Comparison Complete',
  current_filing_complete: 'Current Filing Complete',
  previous_filing_complete: 'Previous Filing Complete',
  ticker_enrichment_complete: 'Ticker Enrichment Complete',
  confidential_omissions_possible: 'Confidential Omissions Possible',
}

export const POSITION_DIFF_STATUS_LABELS = POSITION_DIFF_STATUS_OPTIONS.reduce(
  (acc, option) => {
    acc[option.value] = option.label
    return acc
  },
  {}
)
