/** Demo rejimi. Built in phase 10. */

import { Construction } from 'lucide-react'

import { EmptyState, Page } from '../components/ui'

export default function Demo() {
  return (
    <Page title="Demo rejimi" subtitle="Səbət və kassa bir ekranda — proyektor üçün.">
      <EmptyState
        icon={<Construction className="size-9" aria-hidden />}
        title="Bu ekran Faza 10-da hazırlanır"
        hint="Səbət və kassa bir ekranda — proyektor üçün."
      />
    </Page>
  )
}
