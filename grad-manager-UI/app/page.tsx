import { GradDataProvider } from "@/components/gradmanager/grad-data-provider"
import { GradManagerApp } from "@/components/gradmanager/grad-manager-app"

export default function Page() {
  return (
    <GradDataProvider>
      <GradManagerApp />
    </GradDataProvider>
  )
}
