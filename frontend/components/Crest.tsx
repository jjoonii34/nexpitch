import type { Team } from "@/lib/types";

/** 팀 엠블럼. 이미지 주소가 없으면 3글자 약어 동그라미로 대신한다. */
export default function Crest({ team, size = 24 }: { team: Team; size?: number }) {
  if (team.crest) {
    return (
      // 외부 도메인 이미지를 그대로 쓰기 위해 next/image 대신 img 사용 (Vercel 이미지 최적화 무료 한도를 쓰지 않으려는 목적도 있다)
      // eslint-disable-next-line @next/next/no-img-element
      <img src={team.crest} alt="" width={size} height={size} loading="lazy" className="shrink-0 object-contain" style={{ width: size, height: size }} />
    );
  }
  return (
    <span
      aria-hidden="true"
      className="flex shrink-0 items-center justify-center rounded-full bg-surface-2 font-bold text-muted"
      style={{ width: size, height: size, fontSize: size * 0.36 }}
    >
      {team.tla}
    </span>
  );
}
