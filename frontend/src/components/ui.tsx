import { cloneElement, isValidElement, useEffect, useId, useRef, type ReactElement, type ReactNode } from "react";
import { cls } from "../util";

export function Dialog({ open, title, onClose, children, footer, wide }: { open: boolean; title: string; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      d.showModal();
      d.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    }
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className={cls("dialog", wide && "dialog-wide")} aria-labelledby={titleId} onCancel={(e) => { e.preventDefault(); onClose(); }}>
      {open && (
        <div className="dialog-inner">
          <header className="dialog-head">
            <h2 id={titleId}>{title}</h2>
            <button type="button" className="btn-icon" onClick={onClose} aria-label="Dialog schließen">✕</button>
          </header>
          <div className="dialog-body">{children}</div>
          {footer && <footer className="dialog-foot">{footer}</footer>}
        </div>
      )}
    </dialog>
  );
}

export function Field({ label, error, hint, children }: { label: string; error?: string; hint?: string; children: ReactElement }) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errId = `${id}-err`;
  const describedBy = [hint && hintId, error && errId].filter(Boolean).join(" ") || undefined;
  const control = isValidElement(children)
    ? cloneElement(children as ReactElement<Record<string, unknown>>, { id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })
    : children;
  return (
    <div className={cls("field", error && "field-error")}>
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      {control}
      {hint && (
        <span className="field-hint" id={hintId}>
          {hint}
        </span>
      )}
      {error && (
        <span className="field-msg" id={errId} role="alert">
          ⚠ {error}
        </span>
      )}
    </div>
  );
}

export function Alert({ kind = "info", children }: { kind?: "info" | "warn" | "error" | "ok"; children: ReactNode }) {
  const icon = { info: "ℹ", warn: "⚠", error: "✖", ok: "✔" }[kind];
  return (
    <div className={`alert alert-${kind}`} role={kind === "error" ? "alert" : "status"}>
      <span className="alert-icon" aria-hidden="true">{icon}</span>
      <div>{children}</div>
    </div>
  );
}

export function Badge({ kind = "neutral", children, title }: { kind?: "neutral" | "ok" | "warn" | "info" | "demo"; children: ReactNode; title?: string }) {
  return (
    <span className={`badge badge-${kind}`} title={title}>
      {children}
    </span>
  );
}

export function Spinner({ label = "Lädt …" }: { label?: string }) {
  return (
    <div className="spinner" role="status">
      <span className="spinner-dot" aria-hidden="true" />
      {label}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      {children}
    </div>
  );
}

export function DemoBadge() {
  return (
    <Badge kind="demo" title="Demonstrationsmaterial – nicht fachlich geprüft">
      Demo · nicht fachlich geprüft
    </Badge>
  );
}
