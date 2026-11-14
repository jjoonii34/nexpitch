import ComingSoon from "@/components/ComingSoon";

export const metadata = { title: "뉴스 · nexpitch" };

/** 뉴스 탭 자리. 수집기·LLM 요약이 붙으면 이벤트 카드로 채운다. */
export default function NewsPage() {
  return <ComingSoon title="뉴스" body="기자 티어와 함께 보는 이적·부상 소식 한국어 요약이 여기에 들어옵니다." />;
}
