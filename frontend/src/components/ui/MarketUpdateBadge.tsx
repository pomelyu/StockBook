interface Props {
  us: string | null
  tw: string | null
}

export default function MarketUpdateBadge({ us, tw }: Props) {
  if (!us && !tw) return null

  return (
    <span className="text-xs text-gray-400 whitespace-nowrap">
      最後更新：
      {us !== null && <span>US {us}</span>}
      {us !== null && tw !== null && <span className="mx-1">·</span>}
      {tw !== null && <span>TW {tw}</span>}
    </span>
  )
}
