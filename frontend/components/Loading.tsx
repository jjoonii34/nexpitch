import PageHeader from "./PageHeader";

/** 데이터가 오기 전 잠깐 보이는 뼈대 화면. */
export default function Loading({ title }: { title: string }) {
  return (
    <main aria-busy="true">
      <PageHeader title={title} />
      <div className="mx-3 space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-2xl bg-surface" />
        ))}
      </div>
    </main>
  );
}
