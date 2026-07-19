import { Bell, CalendarRange, Home, Sparkles, User, type LucideIcon } from "lucide-react"

export type TabKey = "home" | "chat" | "schedule" | "notice" | "profile"

const tabs: { key: TabKey; label: string; icon: LucideIcon }[] = [
  { key: "home", label: "홈", icon: Home },
  { key: "chat", label: "AI추천", icon: Sparkles },
  { key: "schedule", label: "시간표", icon: CalendarRange },
  { key: "notice", label: "알림", icon: Bell },
  { key: "profile", label: "프로필", icon: User },
]

export function BottomNav({
  active,
  onChange,
}: {
  active: TabKey
  onChange: (key: TabKey) => void
}) {
  return (
    <nav className="z-10 shrink-0 border-t border-border bg-card/95 backdrop-blur">
      <ul className="flex items-stretch">
        {tabs.map((t) => {
          const isActive = t.key === active
          const Icon = t.icon
          return (
            <li key={t.key} className="flex-1">
              <button
                onClick={() => onChange(t.key)}
                aria-current={isActive ? "page" : undefined}
                className={`flex w-full flex-col items-center gap-1 py-2.5 transition-colors ${
                  isActive ? "text-primary" : "text-muted-foreground"
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? "fill-primary/15" : ""}`} strokeWidth={2.2} />
                <span className="text-[11px] font-medium">{t.label}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
