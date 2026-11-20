// The keyboard shortcut list: a small panel over the page, closed by Esc, ?, or its button.
import { useEffect, useRef } from "react";
import type { ShortcutListItem } from "./shortcuts";
import { CloseIcon } from "../icons";

export const SHORTCUT_LIST_TITLE = "Keyboard shortcuts";

interface ShortcutListProps {
  shortcuts: ShortcutListItem[];
  onClose: () => void;
}

export function ShortcutList({ shortcuts, onClose }: ShortcutListProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  // Focus moves into the panel, and back to what had it (usually the opening button) on close.
  useEffect(() => {
    const opener =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    closeRef.current?.focus();
    return () => {
      opener?.focus();
    };
  }, []);

  return (
    <div
      className="shortcut-list"
      role="dialog"
      aria-labelledby="shortcut-list-title"
    >
      <div className="shortcut-list-head">
        <h2 id="shortcut-list-title">{SHORTCUT_LIST_TITLE}</h2>
        <button
          ref={closeRef}
          type="button"
          className="icon-button"
          aria-label="Close keyboard shortcuts"
          onClick={onClose}
        >
          <CloseIcon />
        </button>
      </div>
      <table>
        <tbody>
          {shortcuts.map(({ keys, does }) => (
            <tr key={keys}>
              <th scope="row">
                <kbd>{keys}</kbd>
              </th>
              <td>{does}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
