/** 실제 데이터가 아닐 때 그 사실과 이유를 숨기지 않고 보여주는 안내 띠. missing은 비어 있는 환경변수 이름. */
export default function SourceNotice({
  source,
  error,
  missing = "FOOTBALL_DATA_API_KEY",
}: {
  source: "live" | "sample";
  error?: string;
  missing?: string;
}) {
  if (source === "live") return null;
  return (
    <p role="status" className="mx-3 mb-2 rounded-xl border border-accent/40 bg-accent/10 px-3 py-2 text-xs text-text">
      <strong>샘플 데이터입니다 (실제 결과 아님).</strong>{" "}
      {error ? `데이터를 불러오지 못했습니다: ${error}` : `${missing}가 설정되지 않았습니다.`}
    </p>
  );
}
