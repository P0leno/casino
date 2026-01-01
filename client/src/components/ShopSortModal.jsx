import React from 'react'

function ShopSortModal({ currentSort, onClose, onApplySort }) {
    const sortOptions = [
        { id: 'default', label: 'По умолчанию' },
        { id: 'price_asc', label: 'Сначала дешевые' },
        { id: 'price_desc', label: 'Сначала дорогие' }
    ]

    return (
        <>
            <div
                className="sort-dropdown-backdrop"
                onClick={onClose}
                style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 99,
                    background: 'transparent'
                }}
            />
            <div
                className="sort-dropdown-menu"
                style={{
                    position: 'absolute',
                    top: '100%',
                    right: '0',
                    marginTop: '8px',
                    background: '#1a1a1a',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '16px',
                    zIndex: 100,
                    minWidth: '200px',
                    overflow: 'hidden',
                    backdropFilter: 'blur(12px)',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
                }}
            >
                {sortOptions.map((option) => (
                    <div
                        key={option.id}
                        onClick={() => {
                            onApplySort(option.id)
                        }}
                        style={{
                            padding: '12px 16px',
                            cursor: 'pointer',
                            color: currentSort === option.id ? '#0FBCE0' : 'rgba(255, 255, 255, 0.8)',
                            backgroundColor: currentSort === option.id ? 'rgba(15, 188, 224, 0.1)' : 'transparent',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            fontSize: '14px',
                            transition: 'background 0.2s',
                            borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
                        }}
                    >
                        <span>{option.label}</span>
                        {currentSort === option.id && <span>✓</span>}
                    </div>
                ))}
            </div>
        </>
    )
}

export default ShopSortModal
