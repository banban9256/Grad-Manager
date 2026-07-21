// UI styling constants (not loaded from JSON)
import type { AiCourseColor } from "@/data/types"

export type { GradManagerData, UserInfo, DigitalTwin } from "@/lib/grad-data-types"

export const aiColorMap: Record<
  AiCourseColor,
  { badge: string; border: string; banner: string; bannerText: string }
> = {
  violet: {
    badge: "bg-[#8f5cf0]",
    border: "border-[#8f5cf0]/30",
    banner: "bg-[#f7f4fd] dark:bg-[#2c1d3c]",
    bannerText: "text-[#703bc9] dark:text-[#a880f7] font-semibold",
  },
  pink: {
    badge: "bg-[#f25875]",
    border: "border-[#f25875]/30",
    banner: "bg-[#fff3f5] dark:bg-[#381e25]",
    bannerText: "text-[#d6284a] dark:text-[#ff6b8b] font-semibold",
  },
  teal: {
    badge: "bg-[#00b5a3]",
    border: "border-[#00b5a3]/30",
    banner: "bg-[#daf2ee] dark:bg-[#183531]",
    bannerText: "text-[#008f80] dark:text-[#00caab] font-semibold",
  },
}
