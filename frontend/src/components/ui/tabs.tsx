"use client";

// Pestañas accesibles (patrón WAI-ARIA): flechas izquierda y derecha, Inicio y Fin
// cambian de pestaña; solo la activa entra en el orden de tabulación.
import { useId, useRef } from "react";
import type { KeyboardEvent, ReactNode } from "react";

export type TabItem = { id: string; label: string };

type TabsProps = {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
  label: string;
  children: ReactNode;
};

export function Tabs({ tabs, active, onChange, label, children }: TabsProps) {
  const baseId = useId();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  function focusTab(index: number) {
    const tab = tabs[(index + tabs.length) % tabs.length];
    onChange(tab.id);
    refs.current[tab.id]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const keys: Record<string, number> = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 };
    if (event.key in keys) {
      event.preventDefault();
      focusTab(keys[event.key]);
    }
  }

  return (
    <div>
      <div role="tablist" aria-label={label} className="mb-4 flex gap-1 overflow-x-auto border-b border-line">
        {tabs.map((tab, index) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              ref={(node) => {
                refs.current[tab.id] = node;
              }}
              type="button"
              role="tab"
              id={`${baseId}-tab-${tab.id}`}
              aria-selected={selected}
              aria-controls={`${baseId}-panel`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(tab.id)}
              onKeyDown={(event) => onKeyDown(event, index)}
              className={`min-h-11 shrink-0 border-b-2 px-4 font-medium ${
                selected ? "border-accent text-ink" : "border-transparent text-ink-muted hover:text-ink"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" id={`${baseId}-panel`} aria-labelledby={`${baseId}-tab-${active}`}>
        {children}
      </div>
    </div>
  );
}
