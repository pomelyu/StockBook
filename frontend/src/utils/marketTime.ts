interface MarketEntry {
  price_updated_at: string | null
  isTW: boolean
}

function formatHHMM(ts: string): string {
  return new Date(ts).toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function getMarketUpdateTimes(entries: MarketEntry[]): { us: string | null; tw: string | null } {
  let latestUS: string | null = null
  let latestTW: string | null = null

  for (const { price_updated_at, isTW } of entries) {
    if (!price_updated_at) continue
    if (isTW) {
      if (!latestTW || price_updated_at > latestTW) latestTW = price_updated_at
    } else {
      if (!latestUS || price_updated_at > latestUS) latestUS = price_updated_at
    }
  }

  return {
    us: latestUS ? formatHHMM(latestUS) : null,
    tw: latestTW ? formatHHMM(latestTW) : null,
  }
}
