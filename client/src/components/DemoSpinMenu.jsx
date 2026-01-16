import { useState, useRef, useEffect } from 'react';
import './DemoSpinMenu.css';

// Ensure the CSS is imported or inline styles used (doing inline/file mix).
// Reusing standard modal-ish styles but bottom sheet.

function DemoSpinMenu({
    isOpen,
    onClose,
    isDemo,
    onToggleDemo,
    selectedGiftName,
    onSelectGift,
    availableGifts
}) {
    const [closing, setClosing] = useState(false);
    const contentRef = useRef(null);

    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => { document.body.style.overflow = ''; };
    }, [isOpen]);

    const handleClose = () => {
        setClosing(true);
        setTimeout(() => {
            setClosing(false);
            onClose();
        }, 300); // match animation duration
    };

    if (!isOpen && !closing) return null;

    return (
        <div className={`demo-menu-overlay ${closing ? 'closing' : ''}`} onClick={handleClose}>
            <div
                className={`demo-menu-content ${closing ? 'closing' : ''}`}
                onClick={(e) => e.stopPropagation()}
                ref={contentRef}
            >
                <div className="demo-menu-handle-bar" onClick={handleClose} />

                <div className="demo-menu-header">
                    <h3>Developer Tools</h3>
                    <div className="demo-toggle-container">
                        <span>Demo Mode</span>
                        <label className="toggle-switch">
                            <input
                                type="checkbox"
                                checked={isDemo}
                                onChange={(e) => onToggleDemo(e.target.checked)}
                            />
                            <span className="slider round"></span>
                        </label>
                    </div>
                </div>

                {isDemo && (
                    <div className="demo-gifts-grid">
                        <p>Select outcome for next spin:</p>
                        <div className="gifts-list">
                            {availableGifts.map((gift) => (
                                <div
                                    key={gift.name || gift}
                                    className={`demo-gift-item ${selectedGiftName === (gift.name || gift) ? 'selected' : ''}`}
                                    onClick={() => onSelectGift(gift.name || gift)}
                                >
                                    {/* Show icon if available (e.g. Secret), else name */}
                                    {(gift.icon) ? (
                                        <img src={gift.icon} alt={gift.name} style={{ width: '32px', height: '32px' }} />
                                    ) : (
                                        <span>{(gift.name || gift).toUpperCase()}</span>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default DemoSpinMenu;
