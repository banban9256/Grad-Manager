import { motion } from "framer-motion"

type CircularProgressProps = {
  value: number
  size?: number
  stroke?: number
  label?: string
  light?: boolean
}

export function CircularProgress({
  value,
  size = 148,
  stroke = 14,
  label,
  light = false,
}: CircularProgressProps) {
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (value / 100) * circumference

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={light ? "rgba(255,255,255,0.18)" : "var(--muted)"}
          strokeWidth={stroke}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--primary)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={`text-3xl font-bold tracking-tight ${light ? "text-white" : "text-foreground"}`}
        >
          {value}%
        </span>
        {label ? (
          <span className={`mt-0.5 text-xs ${light ? "text-white/70" : "text-muted-foreground"}`}>
            {label}
          </span>
        ) : null}
      </div>
    </div>
  )
}

