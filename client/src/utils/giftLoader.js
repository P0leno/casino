// Подарки теперь загружаются из public/gifts/ через Lottie path
// Этот модуль оставлен для обратной совместимости

const cache = {}

export async function loadGiftAnimation(giftName) {
  // Возвращаем путь к файлу вместо импорта
  const path = `/gifts/${giftName}.json`
  if (!cache[giftName]) {
    cache[giftName] = path
  }
  return path
}

export async function preloadGiftAnimations(giftNames) {
  // Ничего не делаем - Lottie загрузит файлы по требованию
  return Promise.resolve()
}
