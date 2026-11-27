"use client";
/* Original vector jewellery illustrations (no third-party images).
   <JewelleryImage> uses a real photo listed in /assets/jewellery/manifest.json, otherwise the art. */
import { useEffect, useId, useState } from "react";

let photoCache: Record<string, string> | null = null;
let photoPromise: Promise<Record<string, string>> | null = null;
function loadManifest() {
  photoPromise ??= fetch("/assets/jewellery/manifest.json").then((r) => (r.ok ? r.json() : {})).catch(() => ({})).then((m) => (photoCache = m));
  return photoPromise;
}

export type Kind = "ring" | "necklace" | "earrings" | "bangle" | "chain" | "pendant" | "mangalsutra" | "coin" | "diamond" | "gem" | "pearl";

export function kindFor(name = "", category = ""): Kind {
  const s = `${name} ${category}`.toLowerCase();
  if (/mangalsutra/.test(s)) return "mangalsutra";
  if (/coin|bar\b/.test(s)) return "coin";
  if (/pendant/.test(s)) return "pendant";
  if (/chain/.test(s)) return "chain";
  if (/earring|jhumk|stud|chandbali/.test(s)) return "earrings";
  if (/bangle|kada|kangan|bracelet|payal/.test(s)) return "bangle";
  if (/necklace|haar|set\b|thali/.test(s)) return "necklace";
  if (/ring|band/.test(s)) return "ring";
  if (/pearl/.test(s)) return "pearl";
  if (/diamond/.test(s)) return "diamond";
  if (/ruby|emerald|sapphire|gem|stone/.test(s)) return "gem";
  return "ring";
}

type Metal = "gold" | "silver" | "rose";
export function metalFor(metal = "", name = ""): Metal {
  if (/silver/i.test(metal) || /silver|payal/i.test(name)) return "silver";
  if (/rose/i.test(name)) return "rose";
  return "gold";
}

const STOPS: Record<Metal, [string, string, string]> = {
  gold: ["#F6E7B8", "#C9A45C", "#8E6D2B"],
  silver: ["#F4F6FA", "#B7BECB", "#7C8596"],
  rose: ["#F7DCCB", "#D9A184", "#9C6249"],
};

export function JewelleryArt({ kind, metal = "gold", className = "" }: { kind: Kind; metal?: Metal; className?: string }) {
  const id = useId().replace(/:/g, "");
  const [a, b, c] = STOPS[metal];
  const g = `url(#g${id})`, d = `url(#d${id})`;
  const gem = (cx: number, cy: number, s = 1) => (
    <g transform={`translate(${cx} ${cy}) scale(${s})`}>
      <polygon points="-12,-9 12,-9 18,-1 0,20 -18,-1" fill={d} stroke="#9fb4d6" strokeWidth="0.6" />
      <path d="M-18 -1 H18 M-6 -9 L-9 -1 L0 20 L9 -1 L6 -9" fill="none" stroke="#fff" strokeOpacity="0.8" strokeWidth="0.6" />
    </g>
  );
  let art: React.ReactNode;
  switch (kind) {
    case "ring":
      art = (<><circle cx="50" cy="62" r="25" fill="none" stroke={g} strokeWidth="8" /><circle cx="50" cy="62" r="21" fill="none" stroke="#fff" strokeOpacity="0.25" strokeWidth="1" />{gem(50, 26, 0.9)}</>);
      break;
    case "diamond":
      art = gem(50, 42, 2.2);
      break;
    case "necklace":
      art = (<><path d="M14 18 C 16 70, 84 70, 86 18" fill="none" stroke={g} strokeWidth="5" strokeLinecap="round" strokeDasharray="0.1 6.5" /><path d="M20 18 C 24 60, 76 60, 80 18" fill="none" stroke={g} strokeWidth="2.2" />{gem(50, 66, 0.75)}</>);
      break;
    case "earrings":
      art = ([32, 68].map((x) => (<g key={x}><path d={`M${x} 14 q6 0 6 7 v6`} fill="none" stroke={g} strokeWidth="2.4" strokeLinecap="round" /><path d={`M${x} 30 c-12 4 -14 24 0 34 c14 -10 12 -30 0 -34z`} fill={g} stroke={c} strokeWidth="0.8" /><circle cx={x} cy="46" r="5" fill={d} stroke="#9fb4d6" strokeWidth="0.6" /><circle cx={x} cy="70" r="4" fill={d} stroke="#9fb4d6" strokeWidth="0.6" /></g>)));
      break;
    case "bangle":
      art = (<><ellipse cx="50" cy="52" rx="34" ry="28" fill="none" stroke={g} strokeWidth="9" /><ellipse cx="50" cy="52" rx="34" ry="28" fill="none" stroke="#fff" strokeOpacity="0.3" strokeWidth="1.5" strokeDasharray="2 5" /><ellipse cx="60" cy="58" rx="30" ry="25" fill="none" stroke={g} strokeWidth="6" opacity="0.85" /></>);
      break;
    case "chain":
      art = (<><ellipse cx="50" cy="52" rx="30" ry="36" fill="none" stroke={g} strokeWidth="6" strokeDasharray="9 4" strokeLinecap="round" /><ellipse cx="50" cy="52" rx="30" ry="36" fill="none" stroke={c} strokeOpacity="0.5" strokeWidth="1" strokeDasharray="9 4" /></>);
      break;
    case "pendant":
      art = (<><circle cx="50" cy="16" r="6" fill="none" stroke={g} strokeWidth="2.6" /><circle cx="50" cy="56" r="26" fill={g} stroke={c} strokeWidth="1" /><circle cx="50" cy="56" r="20" fill="none" stroke="#fff" strokeOpacity="0.5" strokeWidth="1" />{gem(50, 52, 0.8)}</>);
      break;
    case "mangalsutra":
      art = (<><path d="M16 14 L50 66 L84 14" fill="none" stroke="#1d2540" strokeWidth="4.5" strokeLinecap="round" strokeDasharray="0.1 6" /><path d="M22 14 L50 58 L78 14" fill="none" stroke={g} strokeWidth="1.8" /><circle cx="50" cy="74" r="9" fill={g} stroke={c} /><circle cx="50" cy="74" r="4" fill="#1d2540" /></>);
      break;
    case "coin":
      art = (<><circle cx="50" cy="50" r="32" fill={g} stroke={c} strokeWidth="1.5" /><circle cx="50" cy="50" r="26" fill="none" stroke="#fff" strokeOpacity="0.5" strokeWidth="1.2" strokeDasharray="1.5 3" /><text x="50" y="56" textAnchor="middle" fontSize="16" fontWeight="700" fill={c} fontFamily="Georgia, serif">999</text></>);
      break;
    case "pearl":
      art = (<><circle cx="50" cy="50" r="26" fill="url(#pearl)" stroke="#d9d5cc" /><ellipse cx="42" cy="40" rx="8" ry="5" fill="#fff" opacity="0.7" /></>);
      break;
    default:
      art = (<polygon points="30,34 70,34 80,50 70,66 30,66 20,50" fill="url(#ruby)" stroke="#8e2a3a" strokeWidth="1.2" />);
  }
  return (
    <svg viewBox="0 0 100 100" className={className} role="img" aria-label={kind}>
      <defs>
        <linearGradient id={`g${id}`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={a} /><stop offset="0.5" stopColor={b} /><stop offset="1" stopColor={c} /></linearGradient>
        <linearGradient id={`d${id}`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ffffff" /><stop offset="0.6" stopColor="#dfe9f8" /><stop offset="1" stopColor="#b9cbe8" /></linearGradient>
        <radialGradient id="pearl" cx="0.35" cy="0.35"><stop offset="0" stopColor="#fff" /><stop offset="1" stopColor="#e6e1d6" /></radialGradient>
        <linearGradient id="ruby" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ff7b8f" /><stop offset="1" stopColor="#b3203a" /></linearGradient>
      </defs>
      {art}
    </svg>
  );
}

/** Photo-or-art tile. Add real photos to /public/assets/jewellery and list them in manifest.json. */
export function JewelleryImage({ name = "", category = "", metal = "", src, className = "" }: { name?: string; category?: string; metal?: string; src?: string | null; className?: string }) {
  const kind = kindFor(name, category);
  const [manifest, setManifest] = useState<Record<string, string> | null>(photoCache);
  useEffect(() => { if (!manifest) loadManifest().then(setManifest); }, [manifest]);
  const photo = manifest?.[kind];
  const [stage, setStage] = useState(0); // 0 = product photo / library photo, 1 = vector art
  const url = src || (photo ? `/assets/jewellery/${photo}` : "");
  return (
    <div className={`relative overflow-hidden grid place-items-center bg-gradient-to-br from-[#fbf8f0] to-[#f1ecde] dark:from-[#1a2547] dark:to-[#121b36] ${className}`}>
      {url && stage < 1 ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt={name || kind} loading="lazy" className="w-full h-full object-cover" onError={() => setStage(1)} />
      ) : (
        <JewelleryArt kind={kind} metal={metalFor(metal, name)} className="w-3/4 h-3/4 drop-shadow-sm" />
      )}
    </div>
  );
}

export function Logo({ size = 28, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" className={className} aria-hidden>
      <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#F6E7B8" /><stop offset="0.5" stopColor="#C9A45C" /><stop offset="1" stopColor="#8E6D2B" /></linearGradient></defs>
      <polygon points="9,5 31,5 38,15 20,36 2,15" fill="none" stroke="url(#lg)" strokeWidth="2" strokeLinejoin="round" />
      <path d="M2 15 H38 M14 5 L11 15 L20 36 L29 15 L26 5" fill="none" stroke="url(#lg)" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

/** Dark hero artwork: velvet bust with a gold collar necklace (used on dashboard + login). */
export function HeroArt({ className = "", bare = false }: { className?: string; bare?: boolean }) {
  const arcs = [0, 1, 2].map((i) => `M330 ${86 + i * 10} C 360 ${150 + i * 14}, 440 ${150 + i * 14}, 470 ${86 + i * 10}`);
  return (
    <svg viewBox="0 0 560 200" className={className} preserveAspectRatio={bare ? "xMidYMid meet" : "xMaxYMid slice"} aria-hidden>
      <defs>
        <radialGradient id="hv" cx="0.72" cy="0.5" r="0.75"><stop offset="0" stopColor="#2a4278" /><stop offset="1" stopColor="#0a1226" /></radialGradient>
        <linearGradient id="hg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#F6E7B8" /><stop offset="0.5" stopColor="#C9A45C" /><stop offset="1" stopColor="#8E6D2B" /></linearGradient>
        <linearGradient id="hb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1a2850" /><stop offset="1" stopColor="#0b1430" /></linearGradient>
      </defs>
      {!bare && <rect width="560" height="200" fill="url(#hv)" />}
      <path d="M300 200 C 305 140, 345 112, 400 108 C 455 112, 495 140, 500 200z" fill="url(#hb)" />
      <path d="M375 108 C 378 80, 392 62, 400 60 C 408 62, 422 80, 425 108 C 412 118, 388 118, 375 108z" fill="#10193a" />
      {arcs.map((d, i) => <path key={i} d={d} fill="none" stroke="url(#hg)" strokeWidth={5.5 - i * 1.4} strokeLinecap="round" strokeDasharray={i === 1 ? "0.1 7" : "none"} />)}
      {[[352, 124], [376, 134], [400, 138], [424, 134], [448, 124]].map(([x, y], i) => (
        <g key={i} transform={`translate(${x} ${y + 6})`}><polygon points="-7,-6 7,-6 11,0 0,13 -11,0" fill="#eaf1fd" stroke="#C9A45C" strokeWidth="1.2" /><path d="M-11 0 H11 M-4 -6 L-6 0 L0 13 L6 0 L4 -6" stroke="#9fb4d6" strokeWidth="0.6" fill="none" /></g>
      ))}
      <g fill="#C9A45C">{[[40, 36, 2.2], [120, 150, 1.6], [210, 50, 1.8], [270, 170, 1.4], [520, 30, 2], [250, 110, 1.2], [60, 120, 1.5]].map(([x, y, r], i) => <circle key={i} cx={x} cy={y} r={r} opacity="0.5" />)}</g>
    </svg>
  );
}
