import { PageHeader } from "../components/PageHeader";
import { ConversationBrowser } from "../panels/ConversationPanels";

export function ConversationsPage() {
  return (
    <>
      <PageHeader title="Riwayat percakapan" subtitle="pertanyaan lewat perangkat EduPad" />
      <ConversationBrowser />
    </>
  );
}
