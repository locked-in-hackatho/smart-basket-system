/** Kassa. Built in phase 5. */

import { Construction } from 'lucide-react'

import { EmptyState, Page } from '../components/ui'

export default function Checkout() {
  return (
    <Page title="Kassa" subtitle="Kassir səbətin QR kodunu oxuyur, yekun dərhal görünür.">
      <EmptyState
        icon={<Construction className="size-9" aria-hidden />}
        title="Bu ekran Faza 5-da hazırlanır"
        hint="Kassir səbətin QR kodunu oxuyur, yekun dərhal görünür."
      />
    </Page>
  )
}
