import { formatKstFullDate } from "@/lib/dates";
import { clubsLabel } from "@/lib/newsMap";
import type { NewsItem } from "@/lib/types";

const SOURCE_LABEL: Record<string, string> = { guardian: "The Guardian", sample: "샘플" };

/**
 * 뉴스 한 장: 제목·요약·바이라인·날짜·구단. 가디언 약관(ADR 0006)대로 제목(전문)·요약·바이라인을 고치지 않고 그대로 싣는다.
 * 본문은 싣지 않고, 누르면 원문이 새 창으로 열린다.
 */
export default function NewsCard({ item }: { item: NewsItem }) {
  const clubs = clubsLabel(item.clubs);
  return (
    <li>
      <a href={item.url} target="_blank" rel="noopener noreferrer" className="block px-4 py-3 hover:bg-surface-2">
        <p className="text-xs text-muted">
          {SOURCE_LABEL[item.source] ?? item.source}
          {clubs && ` · ${clubs}`}
        </p>
        <h3 className="mt-1 text-sm font-bold leading-snug">{item.title}</h3>
        {item.summary && <p className="mt-1 line-clamp-3 text-sm text-muted">{item.summary}</p>}
        <p className="mt-1.5 text-xs text-muted">
          {item.author && `${item.author} · `}
          {formatKstFullDate(item.publishedAt)} · 원문 보기 ↗
        </p>
      </a>
    </li>
  );
}
