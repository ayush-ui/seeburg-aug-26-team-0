/**
 * Inline SVG icons - never emoji, and never the only carrier of meaning.
 * Paths are Material Symbols outlines, drawn on a 24x24 grid.
 */

const PATHS = {
  check: 'M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z',
  close: 'M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z',
  error:
    'M12 2 1 21h22zm0 4.3 7.5 12.9h-15zM11 10v4h2v-4zm0 5.5V17h2v-1.5z',
  warning:
    'M12 5.99 19.53 19H4.47zM12 2 1 21h22zm-1 8v4h2v-4zm0 5.5V17h2v-1.5z',
  info: 'M11 7h2v2h-2zm0 4h2v6h-2zm1-9a10 10 0 1 0 0 20 10 10 0 0 0 0-20m0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16',
  skip: 'M6 18V6h2v12zm3.5-6 8.5 6V6z',
  doc: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zm-1 7V3.5L18.5 9zM8 13h8v2H8zm0 4h8v2H8z',
  inbox:
    'M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2m0 12h-4a3 3 0 0 1-6 0H5V5h14z',
  flag: 'M14.4 6 14 4H5v17h2v-7h5.6l.4 2h7V6z',
  chart: 'M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z',
  chat: 'M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2m0 14H5.2L4 17.2V4h16z',
  send: 'M2 21 23 12 2 3v7l15 2-15 2z',
  sun: 'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10m0 8a3 3 0 1 1 0-6 3 3 0 0 1 0 6M11 1h2v3h-2zm0 19h2v3h-2zM1 11h3v2H1zm19 0h3v2h-3zM4.2 5.6 5.6 4.2 7.8 6.4 6.4 7.8zM16.2 17.6l1.4-1.4 2.2 2.2-1.4 1.4zM17.6 6.4l2.2-2.2 1.4 1.4-2.2 2.2zM4.2 18.4l2.2-2.2 1.4 1.4-2.2 2.2z',
  moon: 'M12 3a9 9 0 1 0 9 9c0-.5 0-.9-.1-1.4a6 6 0 1 1-7.5-7.5c-.5-.1-.9-.1-1.4-.1',
  logout: 'M17 7l-1.4 1.4L18.2 11H8v2h10.2l-2.6 2.6L17 17l5-5zM4 5h8V3H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8v-2H4z',
  refresh:
    'M17.6 6.4A8 8 0 1 0 19.7 14h-2.1A6 6 0 1 1 12 6c1.7 0 3.1.7 4.2 1.8L13 11h7V4z',
  lock: 'M18 8h-1V6a5 5 0 0 0-10 0v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2M9 6a3 3 0 0 1 6 0v2H9zm9 14H6V10h12zm-6-3a2 2 0 1 0 0-4 2 2 0 0 0 0 4',
  person: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8m0 2c-2.7 0-8 1.3-8 4v2h16v-2c0-2.7-5.3-4-8-4',
  chevron: 'M8.6 16.6 13.2 12 8.6 7.4 10 6l6 6-6 6z',
  expand: 'M7.4 8.6 12 13.2l4.6-4.6L18 10l-6 6-6-6z',
  download: 'M5 20h14v-2H5zm7-16v9.2L8.4 9.6 7 11l5 5 5-5-1.4-1.4L13 13.2V4z',
  search: 'M15.5 14h-.8l-.3-.3a6.5 6.5 0 1 0-.7.7l.3.3v.8l5 5 1.5-1.5zm-6 0a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9',
  shield: 'M12 1 3 5v6c0 5.5 3.8 10.7 9 12 5.2-1.3 9-6.5 9-12V5zm0 10.9h7c-.5 4.1-3.3 7.8-7 8.9V12H5V6.3l7-3.1z',
};

export default function Icon({ name, size = 18, className = '', title }) {
  const d = PATHS[name];
  if (!d) return null;
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={className}
      fill="currentColor"
      aria-hidden={title ? undefined : 'true'}
      role={title ? 'img' : undefined}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      <path d={d} />
    </svg>
  );
}
