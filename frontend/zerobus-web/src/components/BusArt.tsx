interface BusArtProps {
  /** Pixel width of the illustration (height scales automatically). */
  width?: number;
  className?: string;
}

/**
 * Shared ZeroBus motif: a side-view coach in brand indigo/amber.
 * Pure SVG, no effects — safe for SSR/static renders. Motion (wheel spin,
 * gentle idle bob) lives in `index.css` and collapses entirely under
 * `prefers-reduced-motion`. Decorative, so hidden from assistive tech;
 * never carries information alone.
 */
export function BusArt({ width = 180, className = "" }: BusArtProps) {
  return (
    <svg
      className={`zb-busart ${className}`.trim()}
      width={width}
      height={width * 0.46}
      viewBox="0 0 140 64"
      aria-hidden="true"
      focusable="false"
    >
      <ellipse cx="70" cy="58" rx="54" ry="4" className="zb-shadow" />
      <g className="zb-body">
        <rect x="6" y="12" width="120" height="32" rx="8" className="zb-bus-body" />
        <rect x="6" y="12" width="120" height="7" rx="3.5" className="zb-bus-roof" />
        <rect x="14" y="21" width="17" height="10" rx="2" className="zb-bus-glass" />
        <rect x="35" y="21" width="17" height="10" rx="2" className="zb-bus-glass" />
        <rect x="56" y="21" width="17" height="10" rx="2" className="zb-bus-glass" />
        <rect x="77" y="21" width="17" height="10" rx="2" className="zb-bus-glass" />
        <rect x="99" y="20" width="9" height="24" rx="1.5" className="zb-bus-door" />
        <rect x="101" y="22" width="5" height="8" rx="1" className="zb-bus-glass" />
        <rect x="111" y="20" width="13" height="11" rx="2" className="zb-bus-glass" />
        <rect x="110" y="12.5" width="15" height="5" rx="1.5" className="zb-bus-board" />
        <rect x="6" y="37" width="120" height="3.5" className="zb-bus-stripe" />
        <circle cx="127.5" cy="36" r="2.4" className="zb-bus-lamp" />
        <circle cx="5" cy="36" r="2" className="zb-bus-tail" />
        <rect x="2" y="41" width="7" height="4" rx="2" className="zb-bus-bumper" />
        <rect x="123" y="41" width="7" height="4" rx="2" className="zb-bus-bumper" />
      </g>
      <g className="zb-wheel">
        <circle cx="34" cy="48" r="10" className="zb-tyre" />
        <circle cx="34" cy="48" r="5" className="zb-rim" />
        <g className="zb-spokes">
          <line x1="34" y1="43.5" x2="34" y2="52.5" className="zb-spoke" />
          <line x1="29.5" y1="48" x2="38.5" y2="48" className="zb-spoke" />
        </g>
        <circle cx="34" cy="48" r="1.8" className="zb-hub" />
      </g>
      <g className="zb-wheel">
        <circle cx="106" cy="48" r="10" className="zb-tyre" />
        <circle cx="106" cy="48" r="5" className="zb-rim" />
        <g className="zb-spokes">
          <line x1="106" y1="43.5" x2="106" y2="52.5" className="zb-spoke" />
          <line x1="101.5" y1="48" x2="110.5" y2="48" className="zb-spoke" />
        </g>
        <circle cx="106" cy="48" r="1.8" className="zb-hub" />
      </g>
    </svg>
  );
}
