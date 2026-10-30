import { usePanel } from "../api/usePanel";
import { PageIntro } from "../components/PageIntro";
import { ConversationBrowser } from "../panels/ConversationPanels";

export function ConversationsPage() {
  const data = usePanel("conversations").data;
  const turns = data?.sessions.reduce((total, s) => total + s.turns.length, 0) ?? 0;
  return (
    <>
      <PageIntro owl="pixel" title="Percakapan">
        {!data
          ? "Memuat riwayat percakapan…"
          : turns
            ? `${turns} tanya-jawab lewat perangkat EduPad, lengkap dengan isi layar dan sumber materinya.`
            : "Belum ada percakapan. Tahan tombol di EduPad lalu bertanya."}
      </PageIntro>
      <ConversationBrowser />
    </>
  );
}
