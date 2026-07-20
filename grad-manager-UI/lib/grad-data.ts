// UI styling constants (not loaded from JSON)
import type { AiCourseColor } from "@/data/types"

export type { GradManagerData, UserInfo, DigitalTwin } from "@/lib/grad-data-types"

export const aiColorMap: Record<
  AiCourseColor,
  { badge: string; border: string; banner: string; bannerText: string }
> = {
  violet: {
    badge: "bg-violet-500",
    border: "border-violet-500",
    banner: "bg-violet-50",
    bannerText: "text-violet-700",
  },
  pink: {
    badge: "bg-pink-500",
    border: "border-pink-500",
    banner: "bg-pink-50",
    bannerText: "text-pink-700",
  },
  teal: {
    badge: "bg-teal-500",
    border: "border-teal-500",
    banner: "bg-teal-50",
    bannerText: "text-teal-700",
  },
}
