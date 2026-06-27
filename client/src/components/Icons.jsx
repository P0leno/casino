const icons = {
  star: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z',
  gift: 'M20 12v6a2 2 0 01-2 2H6a2 2 0 01-2-2v-6m4-6a2 2 0 100-4 2 2 0 000 4zm8 0a2 2 0 100-4 2 2 0 000 4zm-8 0h8M4 12h16',
  paw: 'M12 2C9 2 7 4 7 7c0 2.5 2 4 5 6 3-2 5-3.5 5-6 0-3-2-5-5-5zM6 10c-2 0-3 2-3 4s1 4 3 4 3-2 3-4-1-4-3-4zm12 0c-2 0-3 2-3 4s1 4 3 4 3-2 3-4-1-4-3-4zM4 16c-1.5 0-3 1-3 3s1.5 3 3 3 3-1 3-3-1.5-3-3-3zm16 0c-1.5 0-3 1-3 3s1.5 3 3 3 3-1 3-3-1.5-3-3-3z',
  home: 'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z',
  shop: 'M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4zM3 6h18M16 10a4 4 0 01-8 0',
  inventory: 'M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm0 4v8m4-8v8m4-8v8m4-8v8',
  profile: 'M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2m8-10a4 4 0 100-8 4 4 0 000 8z',
  tasks: 'M9 11l3 3L22 4m-1 11v4a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11',
  topup: 'M12 1v22m-7-7l7 7 7-7',
  crash: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
  back: 'M19 12H5m7-7l-7 7 7 7',
  close: 'M18 6L6 18M6 6l12 12',
  settings: 'M12 15a3 3 0 100-6 3 3 0 000 6zm-8-3a8 8 0 1116 0 8 8 0 01-16 0z',
  search: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  admin: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
  ban: 'M12 2a10 10 0 100 20 10 10 0 000-20zm0 18a8 8 0 110-16 8 8 0 010 16zm-5-8h10',
  coin: 'M12 1a8 8 0 100 16 8 8 0 000-16zm0 12a4 4 0 110-8 4 4 0 010 8z',
  fire: 'M12 2C8 6 6 10 6 14a6 6 0 0012 0c0-4-2-8-6-12zm0 10a2 2 0 00-2 2c0 1.1.9 2 2 2v4',
  bomb: 'M11 2a1 1 0 012 0v2a1 1 0 01-2 0V2zM6 7a6 6 0 1112 0v4a6 6 0 01-12 0V7zm2 0v4a4 4 0 108 0V7a4 4 0 00-8 0zm2 8h4v2h-4v-2z',
  link: 'M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71',
  info: 'M12 2a10 10 0 100 20 10 10 0 000-20zm0 18a8 8 0 110-16 8 8 0 010 16zm1-13h-2v2h2V7zm0 4h-2v6h2v-6z',
  warning: 'M12 2L1 21h22L12 2zm0 4l7.53 13H4.47L12 6zm-1 5h2v4h-2v-4zm0 6h2v2h-2v-2z',
  check: 'M20 6L9 17l-5-5',
  bolt: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
  refresh: 'M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15',
  chart: 'M18 20V10M12 20V4M6 20v-6M3 20h18',
  palette: 'M12 2a8 8 0 00-8 8c0 3.3 2 6 5 7v1a2 2 0 002 2h2a2 2 0 002-2v-1c3-1 5-3.7 5-7a8 8 0 00-8-8zM8 10a1 1 0 110-2 1 1 0 010 2zm8 0a1 1 0 110-2 1 1 0 010 2zm-4-4a1 1 0 110-2 1 1 0 010 2z',
  support: 'M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.66 0 3-4.03 3-9s-1.34-9-3-9m0 18c-1.66 0-3-4.03-3-9s1.34-9 3-9M3 12a9 9 0 019-9',
  gamepad: 'M6 12h4M8 10v4M15 13h.01M18 11h.01M17.32 5H6.68a4 4 0 00-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 003 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 019.828 16h4.344a2 2 0 011.414.586L17 18c.5.5 1 1 2 1a3 3 0 003-3c0-1.545-.604-6.584-.685-7.258-.007-.05-.011-.1-.017-.151A4 4 0 0017.32 5z',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zm-8 8c0-2.7 5.3-4 8-4s8 1.3 8 4',
}

const sizes = {
  sm: 16,
  md: 20,
  lg: 24,
  xl: 32,
  '2xl': 40,
}

function Icon({ name, size = 'md', className = '', style = {}, fill, glow, bold }) {
  const path = icons[name]
  if (!path) return null

  const px = sizes[size] || 20
  const strokeW = bold ? 2.5 : 1.5

  const combinedStyle = { flexShrink: 0, ...style }
  if (fill) {
    combinedStyle.fill = 'currentColor'
  }
  if (glow) {
    combinedStyle.filter = 'drop-shadow(0 0 4px currentColor) drop-shadow(0 0 8px currentColor)'
  }

  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 24 24"
      fill={fill ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth={strokeW}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={combinedStyle}
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  )
}

export { icons }
export default Icon
