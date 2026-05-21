import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json({
    app: 'ERP_Web',
    frontend: 'navigation-simplified',
    commit: process.env.VERCEL_GIT_COMMIT_SHA ?? 'local',
    builtAt: new Date().toISOString(),
  })
}
