/** Analitika paneli. Built in phase 9. */

import { Construction } from 'lucide-react'

import { EmptyState, Page } from '../components/ui'

export default function Admin() {
  return (
    <Page title="Analitika paneli" subtitle="Dövriyyə, istilik xəritəsi və AI tövsiyələri.">
      <EmptyState
        icon={<Construction className="size-9" aria-hidden />}
        title="Bu ekran Faza 9-da hazırlanır"
        hint="Dövriyyə, istilik xəritəsi və AI tövsiyələri."
      />
    </Page>
  )
}
