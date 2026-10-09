import { Navigate, Route, Routes } from 'react-router-dom'

import { ToastProvider } from './components/Toast'
import Admin from './pages/Admin'
import BasketDevice from './pages/BasketDevice'
import Checkout from './pages/Checkout'
import Demo from './pages/Demo'
import Home from './pages/Home'
import Insights from './pages/Insights'
import PrintCodes from './pages/PrintCodes'

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/basket/:basketId" element={<BasketDevice />} />
        {/* A bare /basket is a common mistake on the demo laptop. */}
        <Route path="/basket" element={<Navigate to="/basket/BSK-001" replace />} />
        <Route path="/checkout" element={<Checkout />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/print" element={<PrintCodes />} />
        <Route path="/demo" element={<Demo />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ToastProvider>
  )
}
