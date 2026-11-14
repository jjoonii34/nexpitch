/** 실제 데이터가 아닐 때 그 사실과 이유를 숨기지 않고 보여주는 안내 띠. */
export default function SourceNotice({ source, error }: { source: "live" | "sample"; error?: string }) {
  if (source === "live") return null;
  return (
    <p role="status" className="mx-3 mb-2 rounded-xl border border-accent/40 bg-accent/10 px-3 py-2 text-xs text-text">
      <strong>샘플 데이터입니다 (실제 결과 아님).</strong>{" "}
      {error ? `데이터를 불러오지 못했습니다: ${error}` : "FOOTBALL_DATA_API_KEY가 설정되지 않았습니다."}
    </p>
  );
}
