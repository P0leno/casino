// Динамическая загрузка анимаций для оптимизации размера бандла
const giftAnimations = {
  bear: () => import('../assets/bear.json'),
  cake: () => import('../assets/cake.json'),
  cup: () => import('../assets/cup.json'),
  diamond: () => import('../assets/diamond.json'),
  flowers: () => import('../assets/flowers.json'),
  gift: () => import('../assets/gift.json'),
  heart: () => import('../assets/heart.json'),
  ring: () => import('../assets/ring.json'),
  rocket: () => import('../assets/rocket.json'),
  rose: () => import('../assets/rose.json')
}

const cache = {}

export async function loadGiftAnimation(giftName) {
  if (cache[giftName]) {
    return cache[giftName]
  }

  if (giftAnimations[giftName]) {
    const module = await giftAnimations[giftName]()
    cache[giftName] = module.default
    return module.default
  }

  return null
}

export async function preloadGiftAnimations(giftNames) {
  const promises = giftNames.map(name => loadGiftAnimation(name))
  return Promise.all(promises)
}
