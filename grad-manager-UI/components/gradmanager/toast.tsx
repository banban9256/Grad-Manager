"use client"

import React, { createContext, useContext, useState, useEffect } from "react"

type ToastType = {
  message: string
  visible: boolean
}

type ToastContextType = {
  showToast: (message: string) => void
}

const ToastContext = createContext<ToastContextType | null>(null)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<ToastType>({ message: "", visible: false })

  const showToast = (message: string) => {
    setToast({ message, visible: true })
  }

  useEffect(() => {
    if (toast.visible) {
      const timer = setTimeout(() => {
        setToast((prev) => ({ ...prev, visible: false }))
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [toast.visible])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast UI - Positioned absolutely so it renders within the mobile frame mock */}
      <div
        className={`absolute bottom-20 left-1/2 z-50 w-[85%] -translate-x-1/2 transition-all duration-300 ease-out ${
          toast.visible
            ? "translate-y-0 opacity-100 scale-100"
            : "translate-y-4 opacity-0 scale-95 pointer-events-none"
        }`}
      >
        <div className="flex items-center justify-center rounded-2xl border border-white/10 bg-slate-900/90 px-4 py-3 text-center text-xs font-semibold text-white shadow-xl backdrop-blur-md">
          <span>{toast.message}</span>
        </div>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider")
  }
  return context
}
