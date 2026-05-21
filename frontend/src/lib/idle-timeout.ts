'use client'
import { useEffect, useRef, useState } from 'react'

const WARNING_SECONDS = 60
const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'] as const

export function useIdleTimeout(minutos = 30, onTimeout: () => void) {
  const timeoutMs = minutos * 60 * 1000
  const warningMs = Math.max(timeoutMs - WARNING_SECONDS * 1000, 1000)
  const warningTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const logoutTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [showWarning, setShowWarning] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(WARNING_SECONDS)

  const clearTimers = () => {
    if (warningTimer.current) clearTimeout(warningTimer.current)
    if (logoutTimer.current) clearTimeout(logoutTimer.current)
  }

  const reset = () => {
    clearTimers()
    setShowWarning(false)
    setSecondsLeft(WARNING_SECONDS)
    warningTimer.current = setTimeout(() => {
      setShowWarning(true)
      setSecondsLeft(WARNING_SECONDS)
      logoutTimer.current = setTimeout(onTimeout, WARNING_SECONDS * 1000)
    }, warningMs)
  }

  useEffect(() => {
    reset()
    const onActivity = () => reset()
    ACTIVITY_EVENTS.forEach(event => window.addEventListener(event, onActivity, { passive: true }))
    return () => {
      clearTimers()
      ACTIVITY_EVENTS.forEach(event => window.removeEventListener(event, onActivity))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minutos, onTimeout])

  useEffect(() => {
    if (!showWarning) return
    const interval = setInterval(() => {
      setSecondsLeft(s => Math.max(s - 1, 0))
    }, 1000)
    return () => clearInterval(interval)
  }, [showWarning])

  return { showWarning, secondsLeft, stayActive: reset }
}
