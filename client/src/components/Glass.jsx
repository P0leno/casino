const VARIANT_CLASSES = {
  default: 'glass',
  sm: 'glass-sm',
  strong: 'glass-strong',
  gradient: 'glass-gradient',
  liquid: 'glass-liquid',
}

function Glass({
  as: Tag = 'div',
  variant = 'default',
  hover = false,
  className = '',
  style = {},
  children,
  ...props
}) {
  const cls = [
    VARIANT_CLASSES[variant] || 'glass',
    hover ? 'glass-hover' : '',
    className,
  ].filter(Boolean).join(' ')

  return (
    <Tag className={cls} style={style} {...props}>
      {children}
    </Tag>
  )
}

export default Glass
