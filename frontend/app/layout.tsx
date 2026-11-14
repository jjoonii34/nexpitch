import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import { Suspense } from "react";
import BottomTabs, { Tabs } from "@/components/BottomTabs";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "nexpitch",
  description: "프리미어리그 경기 결과와 순위를 한눈에",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0d1017" },
    { media: "(prefers-color-scheme: light)", color: "#f3f4f7" },
  ],
};

/** 모든 화면의 공통 틀: 가운데 정렬된 모바일 폭 본문 + 하단 탭. */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className={`${geistSans.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">
        <div className="mx-auto flex min-h-dvh w-full max-w-xl flex-col pb-20">{children}</div>
        <Suspense fallback={<Tabs pathname={null} />}>
          <BottomTabs />
        </Suspense>
      </body>
    </html>
  );
}
