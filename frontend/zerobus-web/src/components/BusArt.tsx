interface BusArtProps {
  /** Pixel width of the illustration (height scales automatically). */
  width?: number;
  /** Parked buses idle: no wheel, body, or dash motion. */
  parked?: boolean;
  className?: string;
}

/**
 * Shared ZeroBus motif: a night-bus illustration in brand indigo/amber.
 * Pure SVG, no effects — safe for SSR/static renders. All motion lives in
 * `index.css` and collapses under `prefers-reduced-motion`. Decorative, so
 * hidden from assistive tech; never carries information alone.
 */
export function BusArt({ width = 120, parked = false, className = "" }: BusArtProps) {
  return (
    <svg
      className={`zb-busart${parked ? " parked" : ""} ${className}`.trim()}
      width={width}
      height={width * 0.55}
      viewBox="0 0 120 66"
      aria-hidden="true"
      focusable="false"
    >
      <g className="zb-body">
        <rect x="4" y="10" width="104" height="32" rx="9" className="zb-bus-body" />
        <rect x="12" y="17" width="60" height="10" rx="3" className="zb-bus-glass" />
        <rect x="76" y="17" width="24" height="10" rx="3" className="zb-bus-glass" />
        <rect x="12" y="17" width="4" height="10" className="zb-bus-pillar" />
        <rect x="40" y="17" width="4" height="10" className="zb-bus-pillar" />
        <rect x="86" y="17" width="4" height="10" className="zb-bus-pillar" />
        <circle cx="104" cy="34" r="2.6" className="zb-bus-lamp" />
        <rect x="14" y="33" width="72" height="3" rx="1.5" className="zb-bus-stripe" />
      </g>
      <g className="zb-wheel" data-wheel="rear">
        <circle cx="30" cy="46" r="9" className="zb-tyre" />
        <circle cx="30" cy="46" r="3.4" className="zb-hub" />
        <line x1="30" y1="39" x2="30" y2="53" className="zb-spoke" />
        <line x1="23" y1="46" x2="37" y2="46" className="zb-spoke" />
      </g>
      <g className="zb-wheel" data-wheel="front">
        <circle cx="90" cy="46" r="9" className="zb-tyre" />
        <circle cx="90" cy="46" r="3.4" className="zb-hub" />
        <line x1="90" y1="39" x2="90" y2="53" className="zb-spoke" />
        <line x1="83" y1="46" x2="97" y2="46" className="zb-spoke" />
      </g>
      <g className="zb-dashes" aria-hidden="true">
        <line x1="0" y1="60" x2="18" y2="60" className="zb-dash" />
        <line x1="30" y1="60" x2="48" y2="60" className="zb-dash" />
        <line x1="60" y1="60" x2="78" y2="60" className="zb-dash" />
        <line x1="90" y1="60" x2="108" y2="60" className="zb-dash" />
      </g>
    </svg>
  );
}
