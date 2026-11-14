"use client"; // 현재 주소(usePathname)를 읽어 활성 탭을 표시해야 해서 브라우저에서 실행한다.

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "경기", icon: "M4 6h16v12H4zM12 6v12M4 12h3m10 0h3" },
  { href: "/news", label: "뉴스", icon: "M5 5h14v14H5zM8 9h8M8 12h8M8 15h5" },
  { href: "/league", label: "리그", icon: "M8 4h8v5a4 4 0 0 1-8 0zM12 13v4M8 20h8M8 6H5v1a3 3 0 0 0 3 3M16 6h3v1a3 3 0 0 1-3 3" },
  { href: "/following", label: "팔로잉", icon: "M12 4l2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9 5.5-.8z" },
];

/** 현재 주소를 읽어 활성 탭을 표시한다. 주소는 요청이 와야 알 수 있어 layout에서 Suspense로 감싼다. */
export default function BottomTabs() {
  return <Tabs pathname={usePathname()} />;
}

/** 화면 아래에 고정되는 4개 탭 (경기/뉴스/리그/팔로잉). pathname이 null이면 활성 표시 없이 그린다 (주소를 알기 전 임시 모습). */
export function Tabs({ pathname }: { pathname: string | null }) {
  return (
    <nav
      aria-label="주요 메뉴"
      className="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-surface/95 backdrop-blur pb-[env(safe-area-inset-bottom)]"
    >
      <ul className="mx-auto flex max-w-xl">
        {TABS.map((tab) => {
          // 경기 상세(/matches/…)도 '경기' 탭에 속한다.
          const active =
            pathname !== null &&
            (tab.href === "/" ? pathname === "/" || pathname.startsWith("/matches") : pathname.startsWith(tab.href));
          return (
            <li key={tab.href} className="flex-1">
              <Link
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`flex h-16 flex-col items-center justify-center gap-1 text-xs font-medium ${
                  active ? "text-accent" : "text-muted"
                }`}
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-6 w-6"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d={tab.icon} />
                </svg>
                {tab.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
