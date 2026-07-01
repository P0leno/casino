export const haptic = (style) => {
  try {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(style || 'light')
  } catch {}
}
