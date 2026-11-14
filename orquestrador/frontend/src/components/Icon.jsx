const paths = {
  home: (
    <>
      <path d="m3 10 9-7 9 7" />
      <path d="M5 9v12h14V9M9 21v-7h6v7" />
    </>
  ),
  document: (
    <>
      <path d="M7 3h7l5 5v13H7z" />
      <path d="M14 3v5h5M10 13h6M10 17h6" />
    </>
  ),
  radar: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 3v9l6 6M5.6 5.6l2.1 2.1M3 12h3" />
    </>
  ),
  chart: (
    <>
      <path d="M4 20V4M4 20h17" />
      <path d="M8 16v-4m5 4V8m5 8v-7" />
    </>
  ),
  search: (
    <>
      <circle cx="10.8" cy="10.8" r="6.8" />
      <path d="m16 16 4.5 4.5" />
    </>
  ),
  storefront: (
    <>
      <path d="m4 10 2-6h12l2 6" />
      <path d="M3 10h18v10H3zM8 20v-6h5v6" />
      <path d="M3 10c0 2 3 2.5 4.5.6 1.5 1.9 4.5 1.9 6 0 1.5 1.9 4.5 1.9 6 0C21 12.5 24 12 24 10" />
    </>
  ),
  people: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20v-1a6 6 0 0 1 12 0v1zM16 5.5a3 3 0 0 1 0 5.8M18 14a5 5 0 0 1 3 4.6v1h-3" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  arrowRight: (
    <>
      <path d="M4 12h16M13 5l7 7-7 7" />
    </>
  ),
};

export default function Icon({ name, size = 18, className }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {paths[name]}
    </svg>
  );
}
