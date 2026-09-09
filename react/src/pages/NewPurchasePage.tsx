import { PurchaseForm } from '../components/purchases/PurchaseForm'

export function NewPurchasePage() {
  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">New Purchase</h1>
      <div className="mt-4">
        <PurchaseForm />
      </div>
    </div>
  )
}
