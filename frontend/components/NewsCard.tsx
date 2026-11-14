import { formatKstFullDate } from "@/lib/dates";
import { clubsLabel, displayText } from "@/lib/newsMap";
import type { NewsItem } from "@/lib/types";

const SOURCE_LABEL: Record<string, string> = { guardian: "The Guardian", sample: "샘플" };

/** 뉴스 한 장: 한국어 제목·요약(번역 전이면 영어)·기자·날짜·구단. 본문은 싣지 않고, 누르면 원문이 새 창으로 열린다. */
export default function NewsCard({ item }: { item: NewsItem }) {
  const clubs = clubsLabel(item.clubs);
  const { title, summary, translated } = displayText(item);
  return (
    <li>
      <a href={item.url} target="_blank" rel="noopener noreferrer" className="block px-4 py-3 hover:bg-surface-2">
        <p className="text-xs text-muted">
          {SOURCE_LABEL[item.source] ?? item.source}
          {clubs && ` · ${clubs}`}
          {!translated && " · 번역 전"}
        </p>
        <h3 className="mt-1 text-sm font-bold leading-snug">{title}</h3>
        {summary && <p className="mt-1 line-clamp-3 text-sm text-muted">{summary}</p>}
        {/* 번역은 LLM이 만든 것이라 틀릴 수 있다 → 영어 원문 제목을 함께 보여 확인할 수 있게 한다 */}
        {translated && <p className="mt-1 truncate text-xs text-muted/80">{item.title}</p>}
        <p className="mt-1.5 text-xs text-muted">
          {item.author && `${item.author} · `}
          {formatKstFullDate(item.publishedAt)} · 원문 보기 ↗
        </p>
      </a>
    </li>
  );
}
