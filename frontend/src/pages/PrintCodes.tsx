/** Çap. Built in phase 6. */

import { Construction } from 'lucide-react'

import { EmptyState, Page } from '../components/ui'

export default function PrintCodes() {
  return (
    <Page title="Çap" subtitle="Səbət QR kodları və məhsul barkodları.">
      <EmptyState
        icon={<Construction className="size-9" aria-hidden />}
        title="Bu ekran Faza 6-da hazırlanır"
        hint="Səbət QR kodları və məhsul barkodları."
      />
    </Page>
  )
}
