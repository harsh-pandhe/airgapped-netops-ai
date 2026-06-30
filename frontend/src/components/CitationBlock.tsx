// src/components/CitationBlock.tsx — extracted from inline App.tsx parser
interface Props {
  label: string;
}

export default function CitationBlock({ label }: Props) {
  return (
    <details className="mt-2 p-2 bg-slate-800 rounded border border-slate-700 text-sm block w-full">
      <summary className="cursor-pointer text-cyan-400 hover:text-cyan-300 font-mono font-semibold">
        ▶ Source: {label}
      </summary>
      <div className="mt-2 p-3 bg-black text-slate-300 font-mono text-xs overflow-x-auto rounded border border-slate-600">
        Retrieved configuration snippet
      </div>
    </details>
  );
}