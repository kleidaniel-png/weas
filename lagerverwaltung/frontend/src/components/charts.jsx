// Diagramme (SVG, ohne Zusatzbibliothek). Farben: --chart-1/--chart-2 in index.css.
import { useEffect, useRef, useState } from "react";
import { t } from "../i18n.js";

function useWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(600);
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

function niceMax(value) {
  if (value <= 0) return 1;
  const pow = 10 ** Math.floor(Math.log10(value));
  return [1, 2, 2.5, 5, 10].map((m) => m * pow).find((m) => m >= value);
}

const M = { top: 10, right: 8, bottom: 26, left: 64 };
const AXIS = "fill-stone-500 text-[11px]";
const GRID = "stroke-stone-200 dark:stroke-stone-800";

function Tooltip({ x, width, children }) {
  const left = Math.min(Math.max(x, 80), width - 80);
  return (
    <div className="pointer-events-none absolute top-0 z-10 -translate-x-1/2 rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs shadow-lg dark:border-stone-700 dark:bg-stone-800"
         style={{ left }}>{children}</div>
  );
}

export function Legend({ series }) {
  return (
    <div className="mb-2 flex gap-4 text-xs text-stone-600 dark:text-stone-400">
      {series.map((s) => (
        <span key={s.key} className="inline-flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm" style={{ background: s.color }} /> {t(s.label)}
        </span>
      ))}
    </div>
  );
}

function YAxis({ max, y, width, format }) {
  return [0, 0.25, 0.5, 0.75, 1].map((f) => (
    <g key={f}>
      <line x1={M.left} x2={width - M.right} y1={y(max * f)} y2={y(max * f)} className={GRID} />
      <text x={M.left - 8} y={y(max * f)} dy="0.32em" textAnchor="end" className={AXIS}>{format(max * f)}</text>
    </g>
  ));
}

// Gruppierte Säulen: data = [{label, <key>: Zahl}], series = [{key, label, color}]
export function BarChart({ data, series, format, height = 240 }) {
  const [ref, width] = useWidth();
  const [hover, setHover] = useState(null);
  const max = niceMax(Math.max(0, ...data.flatMap((d) => series.map((s) => d[s.key]))));
  const plotH = height - M.top - M.bottom;
  const band = (width - M.left - M.right) / Math.max(data.length, 1);
  const barW = Math.max(2, Math.min(16, (band - 6) / series.length - 2));
  const y = (v) => M.top + plotH - (v / max) * plotH;
  const every = Math.ceil(data.length / Math.max(1, Math.floor((width - M.left) / 56)));

  return (
    <div ref={ref} className="relative">
      <Legend series={series} />
      <svg width={width} height={height} role="img" aria-label={series.map((s) => t(s.label)).join(" / ")}>
        <YAxis max={max} y={y} width={width} format={format} />
        {data.map((d, i) => {
          const cx = M.left + band * (i + 0.5);
          const start = cx - (series.length * (barW + 2) - 2) / 2;
          return (
            <g key={i}>
              {hover === i && <rect x={M.left + band * i} y={M.top} width={band} height={plotH} className="fill-stone-500/10" />}
              {series.map((s, k) => {
                const h = (d[s.key] / max) * plotH;
                const r = Math.min(4, barW / 2, h);
                const x = start + k * (barW + 2), top = y(d[s.key]), bottom = M.top + plotH;
                return h > 0 && (
                  <path key={s.key} fill={s.color}
                        d={`M${x},${bottom}V${top + r}Q${x},${top} ${x + r},${top}H${x + barW - r}Q${x + barW},${top} ${x + barW},${top + r}V${bottom}Z`} />
                );
              })}
              {i % every === 0 && <text x={cx} y={height - 8} textAnchor="middle" className={AXIS}>{d.label}</text>}
              <rect x={M.left + band * i} y={M.top} width={band} height={plotH} fill="transparent"
                    onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} />
            </g>
          );
        })}
      </svg>
      {hover !== null && (
        <Tooltip x={M.left + band * (hover + 0.5)} width={width}>
          <div className="mb-1 font-semibold">{data[hover].label}</div>
          {series.map((s) => (
            <div key={s.key} className="flex items-center gap-1.5 whitespace-nowrap">
              <span className="size-2 rounded-sm" style={{ background: s.color }} />
              {t(s.label)}: <strong className="tabular-nums">{format(data[hover][s.key])}</strong>
            </div>
          ))}
        </Tooltip>
      )}
    </div>
  );
}

// Treppenlinie über die Zeit: points = [{t (Sekunden), value}]
export function StepLineChart({ points, format, formatTime, height = 220, color = "var(--chart-1)" }) {
  const [ref, width] = useWidth();
  const [hover, setHover] = useState(null);
  if (points.length === 0)
    return <div ref={ref}><p className="py-8 text-center text-sm text-stone-500">{t("Keine Buchungen im Zeitraum.")}</p></div>;
  const t0 = points[0].t, t1 = Math.max(points.at(-1).t, t0 + 1);
  const max = niceMax(Math.max(...points.map((p) => p.value)));
  const plotH = height - M.top - M.bottom, plotW = width - M.left - M.right;
  const x = (t) => M.left + ((t - t0) / (t1 - t0)) * plotW;
  const y = (v) => M.top + plotH - (v / max) * plotH;
  const path = points.map((p, i) => (i ? `H${x(p.t)}V${y(p.value)}` : `M${x(p.t)},${y(p.value)}`)).join("") + `H${x(t1)}`;

  function move(e) {
    const mx = e.clientX - e.currentTarget.getBoundingClientRect().left;
    let best = 0;
    points.forEach((p, i) => { if (x(p.t) <= mx) best = i; });
    setHover(best);
  }
  const h = hover !== null ? points[hover] : null;

  return (
    <div ref={ref} className="relative">
      <svg width={width} height={height} role="img" aria-label={t("Bestandsverlauf")} onMouseMove={move} onMouseLeave={() => setHover(null)}>
        <YAxis max={max} y={y} width={width} format={format} />
        <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        <text x={M.left} y={height - 8} className={AXIS}>{formatTime(t0)}</text>
        <text x={width - M.right} y={height - 8} textAnchor="end" className={AXIS}>{formatTime(t1)}</text>
        {h && <>
          <line x1={x(h.t)} x2={x(h.t)} y1={M.top} y2={M.top + plotH} className="stroke-stone-400" strokeDasharray="3 3" />
          <circle cx={x(h.t)} cy={y(h.value)} r="5" fill={color} className="stroke-white dark:stroke-stone-900" strokeWidth="2" />
        </>}
      </svg>
      {h && (
        <Tooltip x={x(h.t)} width={width}>
          <div className="font-semibold">{formatTime(h.t)}</div>
          <div className="whitespace-nowrap">{t("Bestand:")} <strong className="tabular-nums">{format(h.value)}</strong></div>
        </Tooltip>
      )}
    </div>
  );
}

// Rangliste mit Balken: items = [{label, value, sub?}]
export function BarList({ items, format, empty = "Keine Daten im Zeitraum." }) {
  const max = Math.max(0, ...items.map((i) => i.value));
  if (!items.length) return <p className="py-4 text-sm text-stone-500">{t(empty)}</p>;
  return (
    <ul className="space-y-2.5">
      {items.map((item, i) => (
        <li key={i} title={`${item.label}: ${format(item.value)}`}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="truncate">{item.label} {item.sub && <span className="text-stone-500">{item.sub}</span>}</span>
            <span className="shrink-0 font-medium tabular-nums">{format(item.value)}</span>
          </div>
          <div className="mt-1 h-1.5 rounded-full bg-stone-100 dark:bg-stone-800">
            <div className="h-1.5 rounded-full" style={{ width: `${max > 0 ? Math.max(1, (Math.max(item.value, 0) / max) * 100) : 0}%`, background: "var(--chart-1)" }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
