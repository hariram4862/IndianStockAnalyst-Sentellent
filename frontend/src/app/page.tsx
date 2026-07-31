"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

import { useAuthStore } from "@/store/auth-store"

export default function HomePage() {
  const router = useRouter()
  const { token } = useAuthStore()

  useEffect(() => {
    router.replace(token ? "/dashboard" : "/login")
  }, [router, token])

  return null
}
