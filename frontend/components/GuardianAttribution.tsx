/**
 * 가디언 Open Platform 약관이 요구하는 출처 표기 (ADR 0006):
 * 기사가 실린 같은 페이지에 "Powered by The Guardian" 로고를 싣고, 저작권 표기를 남긴다. 로고는 가디언이 배포한 파일 그대로다.
 */
export default function GuardianAttribution() {
  return (
    <div className="mx-3 mb-3 flex items-center justify-between gap-3 px-1 text-xs text-muted">
      <span>기사 제목·요약 © Guardian News &amp; Media Ltd. 원문 그대로 싣고 최근 24시간 안에 확인된 기사만 보여줍니다.</span>
      <a href="https://www.theguardian.com" target="_blank" rel="noopener noreferrer" aria-label="Powered by The Guardian" className="shrink-0">
        <picture>
          <source srcSet="/guardian/powered-by-black.png" media="(prefers-color-scheme: light)" />
          <img src="/guardian/powered-by-white.png" alt="Powered by The Guardian" width={140} height={45} className="h-8 w-auto" />
        </picture>
      </a>
    </div>
  );
}
