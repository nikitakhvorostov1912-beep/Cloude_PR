/**
 * Отображение сырого текста (fallback).
 */

export function RawTextView({ text }: { text: string }) {
  return (
    <pre className="mt-2 p-3 rounded-lg bg-text/5 text-xs font-mono text-text-secondary overflow-x-auto max-h-96 whitespace-pre-wrap">
      {text}
    </pre>
  );
}
