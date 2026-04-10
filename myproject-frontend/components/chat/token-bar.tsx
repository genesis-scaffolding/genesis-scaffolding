'use client'

interface TokenBarProps {
  history: number
  clipboard: number
  total: number
  max: number
  percent: number
}

export function TokenBar({ history, clipboard, total, max, percent }: TokenBarProps) {
  const isMaxKnown = max > 0

  return (
    <div className="shrink-0 border-b border-muted/50">
      <div className="chat-viewport-container py-1.5 flex gap-6 text-xs text-muted-foreground font-mono">
        <span>History: {(history ?? 0).toLocaleString()}</span>
        <span>Clipboard: {(clipboard ?? 0).toLocaleString()}</span>
        <span>
          Total: {(total ?? 0).toLocaleString()}
          {isMaxKnown
            ? ` / ${(max ?? 0).toLocaleString()} (${percent ?? 0}%)`
            : ` (model max unknown)`}
        </span>
      </div>
    </div>
  )
}
