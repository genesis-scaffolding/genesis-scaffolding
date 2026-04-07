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
        <span>History: {history.toLocaleString()}</span>
        <span>Clipboard: {clipboard.toLocaleString()}</span>
        <span>
          Total: {total.toLocaleString()}
          {isMaxKnown
            ? ` / ${max.toLocaleString()} (${percent}%)`
            : ` (model max unknown)`}
        </span>
      </div>
    </div>
  )
}
