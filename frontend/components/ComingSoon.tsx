import PageHeader from "./PageHeader";

/** 아직 만들지 않은 탭의 자리 표시. 무엇이 들어올지 미리 알려준다. */
export default function ComingSoon({ title, body }: { title: string; body: string }) {
  return (
    <main>
      <PageHeader title={title} />
      <div className="mx-3 rounded-2xl bg-surface px-5 py-12 text-center">
        <p className="text-sm font-bold">준비 중</p>
        <p className="mt-2 text-sm text-muted">{body}</p>
      </div>
    </main>
  );
}
