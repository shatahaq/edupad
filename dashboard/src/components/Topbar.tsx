import { Icon } from "./Icon";

/** Bar atas hanya di HP: tombol menu + nama halaman. */
export function Topbar({ page, onMenu }: { page: string; onMenu: () => void }) {
  return (
    <header className="topbar">
      <button className="icon-btn hamburger" onClick={onMenu} aria-label="Buka menu">
        <Icon name="menu" />
      </button>
      <span className="topbar-title">{page}</span>
    </header>
  );
}
