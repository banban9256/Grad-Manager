import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Noto_Sans_KR, Poppins } from 'next/font/google'
import './globals.css'

const notoSansKr = Noto_Sans_KR({
  subsets: ['latin'],
  variable: '--font-noto-sans-kr',
  weight: ['400', '500', '700'],
})

const poppins = Poppins({
  subsets: ['latin'],
  variable: '--font-poppins',
  weight: ['500', '600', '700'],
})

export const metadata: Metadata = {
  title: 'GradManager · 한신대 AI.SW 학사관리',
  description:
    '디지털 트윈 기반 졸업요건 시각화와 AI 조건부 시간표 추천을 제공하는 한신대학교 AI.SW학과 학사관리 서비스',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light',
  themeColor: '#1e2a4a',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ko" className={`${notoSansKr.variable} ${poppins.variable} bg-navy`}>
      <body className="font-sans antialiased">
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}

