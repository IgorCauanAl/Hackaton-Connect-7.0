export default function BrandMark({ className }) {
  return (
    <span className={className} aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none">
        <path d="m3.5 10 2-6h13l2 6" />
        <path d="M3 10h18v10.5H3zM8 20.5v-6h5v6" />
        <path d="M3 10c0 2 3 2.5 4.5.6 1.5 1.9 4.5 1.9 6 0 1.5 1.9 4.5 1.9 6 0C21 12.5 23 12 23 10" />
      </svg>
    </span>
  );
}
